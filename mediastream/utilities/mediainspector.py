from mutagen.id3 import ID3, ID3NoHeaderError, ID3UnsupportedVersionError
from mutagen.id3 import ParseID3v1, Frames, Frames_2_2, Frame

from mutagen.mp3 import MPEGInfo

from mutagen.mp4 import MP4, Atoms, MP4Info, MP4StreamInfoError, MP4Tags
from mutagen.mp4 import MP4MetadataError, MP4Cover

from mutagen.flac import FLAC, FLACNoHeaderError

from mutagen.ogg import error as OggError
from mutagen.ogg import OggPage
from mutagen.oggvorbis import OggVorbis, OggVorbisInfo, OggVCommentDict, OggVorbisHeaderError

import magic
import mimetypes

# Add previously-unknown mimetypes
mt = mimetypes.MimeTypes()
mt.add_type('audio/mp4', '.m4a')

# Group and sort the mimetypes, for ease of display
mimetypes_grouped = {}
mtmap = mt.types_map_inv[1] # strict
for mtkey, mtvalue in mtmap.items():
    mt0, mt1 = mtkey.split('/',1)
    if mt0 not in mimetypes_grouped:
        mimetypes_grouped[mt0] = []
    if (mt, mt1) not in mimetypes_grouped[mt0]:
        mimetypes_grouped[mt0].append((mtkey, mt1))
    mimetypes_grouped[mt0].sort()

MIMETYPE_CHOICES = sorted(mimetypes_grouped.items())

# Subclass various mutagen stuff to use file-like objects
# instead of filenames, since it doesn't really know what
# to do with our filenames...

class ID3File(ID3):
    def load(self, fp, known_frames=None, translate=True):
        self.filename = fp.name
        self.__known_frames = known_frames
        self.__fileobj = fp
        try:
            self.__filesize = fp.size
        except AttributeError:
            self.__filesize = len(fp.read())
            fp.seek(0)

        # grumble grumble
        self.__load_header = self._ID3__load_header
        self.__fullread = self._ID3__fullread
        self.__read_frames = self._ID3__read_frames
        self._ID3__known_frames = self.__known_frames
        self._ID3__fileobj = self.__fileobj
        self._ID3__filesize = self.__filesize

        try:
            try:
                self.__load_header()
            except EOFError:
                self.size = 0
                raise ID3NoHeaderError("%s: too small (%d bytes)" %(
                    filename, self.__filesize))
            except (ID3NoHeaderError, ID3UnsupportedVersionError), err:
                self.size = 0
                import sys
                stack = sys.exc_info()[2]
                try: self.__fileobj.seek(-128, 2)
                except EnvironmentError: raise err, None, stack
                else:
                    frames = ParseID3v1(self.__fileobj.read(128))
                    if frames is not None:
                        self.version = (1, 1)
                        map(self.add, frames.values())
                    else: raise err, None, stack
            else:
                frames = self.__known_frames
                if frames is None:
                    if (2,3,0) <= self.version: frames = Frames
                    elif (2,2,0) <= self.version: frames = Frames_2_2
                data = self.__fullread(self.size - 10)
                for frame in self.__read_frames(data, frames=frames):
                    if isinstance(frame, Frame): self.add(frame)
                    else: self.unknown_frames.append(frame)
        finally:
            self.__fileobj.close()
            del self.__fileobj
            del self.__filesize
            if translate:
                self.update_to_v24()

    def save(self, filename=None):
        raise NotImplementedError

class MP4File(MP4):
    def load(self, fp):
        self.filename = fp.name
        fileobj = fp
        try:
            atoms = Atoms(fileobj)
            try: self.info = MP4Info(atoms, fileobj)
            except StandardError, err:
                raise MP4StreamInfoError, err, sys.exc_info()[2]
            try: self.tags = MP4Tags(atoms, fileobj)
            except MP4MetadataError:
                self.tags = None
            except StandardError, err:
                raise MP4MetadataError, err, sys.exc_info()[2]
        finally:
            fileobj.close() 

    def save(self, filename=None):
        raise NotImplementedError

class FLACFile(FLAC):
    def load(self, fp):
        self.__check_header = self._FLAC__check_header
        self.__read_metadata_block = self._FLAC__read_metadata_block
        self.metadata_blocks = []
        self.tags = None
        self.cuesheet = None
        self.seektable = None
        self.filename = fp.name
        fileobj = fp
        try:
            self.__check_header(fileobj)
            while self.__read_metadata_block(fileobj):
                pass
        finally:
            fileobj.close()

        try:
            self.metadata_blocks[0].length
        except (AttributeError, IndexError):
            raise FLACNoHeaderError("Stream info block not found")

    def save(self, filename=None):
        raise NotImplementedError

class OggVorbisFile(OggVorbis):
    def load(self, fp):
        self.filename = fp.name
        fileobj = fp
        try:
            try:
                self.info = self._Info(fileobj)
                self.tags = self._Tags(fileobj, self.info)
                if self.info.length:
                    return
                last_page = OggPage.find_last(fileobj, self.info.serial)
                samples = last_page.position
                try:
                    denom = self.info.sample_rate
                except AttributeError:
                    denom = self.info.fps
                self.info.length = samples / float(denom)
            except OggError, e:
                raise self._Error, e, sys.exc_info()[2]
            except EOFError:
                raise self._Error, "no appropriate stream found"
        finally:
            fileobj.close()

    def save(self, filename=None):
        raise NotImplementedError
    def delete(self, filename=None):
        raise NotImplementedError

class Inspector(object):
    """
    Given a file-like object, this class provides attributes for accessing
    various metadata stored in media objects.
    """
    def __init__(self, fileobj, mimetype=None):
        self._fileobj = fileobj
        self.mimetype = mimetype
        if not self.mimetype:
            self._determine_type()
        if self.mimetype == 'audio/mpeg':
            self._inspect_mp3()
        elif self.mimetype == 'audio/mp4':
            self._inspect_mp4()
        elif self.mimetype == 'audio/x-flac' or self.mimetype == 'audio/flac':
            self._inspect_flac()
        elif self.mimetype == 'audio/ogg':
            self._inspect_oggvorbis()

    def _determine_type(self):
        "Determines the type of a file, if possible."
        self._fileobj.seek(0)
        self.mimetype = None
        if hasattr(self._fileobj, 'name'):
            self.mimetype = mt.guess_type(self._fileobj.name)[0]
        if not self.mimetype:
            self.mimetype = magic.from_buffer(self._fileobj.read(), mime=True)

    def _inspect_mp4(self):
        "Cracks open an MP4 file and determines what is inside."
        self._fileobj.seek(0)
        mp4obj = MP4File(self._fileobj)

        self.album = mp4obj.get('\xa9alb', None)
        self.artist = mp4obj.get('\xa9ART', None)
        self.bitrate = mp4obj.info.bitrate
        self.disc = mp4obj.get('disk', [None])[0]
        self.genre = mp4obj.get('\xa9gen', None)
        self.length = mp4obj.info.length
        self.lossy = True
        self.is_compilation = mp4obj.get('cpil', None)
        self.name = mp4obj.get('\xa9nam', None)
        self.track = mp4obj.get('trkn', [None])[0]
        self.year = int(mp4obj.get('\xa9day')[0]) if '\xa9day' in mp4obj else None

        self.artwork = []
        if 'covr' in mp4obj:
            # Cover artwork
            # Untested, so far!
            covr = mp4obj.get('covr')
            if covr.imageformat == MP4Cover.FORMAT_JPEG:
                covr_mime = 'image/jpeg'
            elif covr.imageformat == MP4Cover.FORMAT_PNG:
                covr_mime = 'image/png'
            else:
                covr_mime = 'application/octet-stream'
            self.artwork.append({'data': covr, 'mimetype': covr_mime})

    def _inspect_mp3(self):
        "Cracks open the mp3 file and determines what is inside."
        self._fileobj.seek(0)
        infoobj = MPEGInfo(self._fileobj)
        self._fileobj.seek(0)
        id3obj = ID3File(self._fileobj)

        self.album = id3obj.get('TALB').text[0] if 'TALB' in id3obj else None
        self.artist = id3obj.get('TPE1').text[0] if 'TPE1' in id3obj else None
        self.band = id3obj.get('TPE2').text[0] if 'TPE2' in id3obj else None
        self.bitrate = infoobj.bitrate
        try:
            self.disc = +id3obj.get('TPOS') if 'TPOS' in id3obj else None
        except:
            self.disc = None
        self.genre = id3obj.get('TCON').text[0] if 'TCON' in id3obj else None
        self.is_sketchy = infoobj.sketchy
        self.length = infoobj.length
        self.lossy = True
        self.name = id3obj.get('TIT2').text[0] if 'TIT2' in id3obj else None
        self.samplerate = infoobj.sample_rate
        try:
            self.track = +id3obj.get('TRCK') if 'TRCK' in id3obj else None
        except:
            self.track = None
        self.year = int(id3obj['TDRC'].text[0].year) if 'TDRC' in id3obj else None

        self.artwork = []
        for apic in id3obj.getall('APIC'):
            # We have a picture!  Extract it onto its own AssetFile.
            self.artwork.append({'data': apic.data, 'mimetype': apic.mime})

    def _inspect_flac(self):
        "Cracks open a FLAC file and determines what is inside."
        self._fileobj.seek(0)
        flacobj = FLACFile(self._fileobj)

        self.album          = flacobj.get('album', [None])[0]
        self.artist         = flacobj.get('artist', [None])[0]
        self.bitrate        = flacobj.info.total_samples*flacobj.info.bits_per_sample/flacobj.info.length
        self.disc           = flacobj.get('discnumber', [None])[0]
        self.genre          = flacobj.get('genre', [None])[0]
        self.length         = flacobj.info.length
        self.lossy          = False
        self.is_compilation = False  # TODO
        self.name           = flacobj.get('title', [None])[0]
        self.track          = flacobj.get('tracknumber', [None])[0]
        self.year           = int(flacobj['date'][0].split('-')[0]) if 'date' in flacobj else None

        self.artwork = []   # TODO

    def _inspect_oggvorbis(self):
        "Cracks open a FLAC file and determines what is inside."
        self._fileobj.seek(0)
        oggobj = OggVorbisFile(self._fileobj)

        self.album          = oggobj.get('album', [None])[0]
        self.artist         = oggobj.get('artist', [None])[0]
        self.bitrate        = oggobj.info.bitrate
        self.disc           = oggobj.get('discnumber', [None])[0]
        self.genre          = oggobj.get('genre', [None])[0]
        self.length         = oggobj.info.length
        self.lossy          = True
        self.is_compilation = False  # TODO
        self.name           = oggobj.get('title', [None])[0]
        self.track          = oggobj.get('tracknumber', [None])[0]
        self.year           = int(oggobj['date'][0].split('-')[0]) if 'date' in oggobj else None

        self.artwork = []   # TODO
