from mutagen.id3 import ID3, ID3NoHeaderError, ID3UnsupportedVersionError
from mutagen.id3 import ParseID3v1, Frames, Frames_2_2, Frame

# Subclass various mutagen stuff to use file-like objects
# instead of filenames, since it doesn't really know what
# to do with our filenames...

class ID3File(ID3):
    def load(self, fp, known_frames=None, translate=True):
        self.filename = fp.name
        self.__known_frames = known_frames
        self.__fileobj = fp
        self.__filesize = fp.size

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
