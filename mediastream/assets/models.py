from django.conf import settings
from django.core.files.base import ContentFile
from django.core.urlresolvers import reverse
from django.db import models
from django.db.models import Avg, Max, Min, Count

from mutagen.m4a import M4ACover
from mutagen.mp3 import MPEGInfo

from mediastream.assets import MIMETYPE_CHOICES, _get_upload_path
from mediastream.assets import mt as mimetypes
from mediastream.utilities.mediainspector import Inspector

class Thing(models.Model):
    "Abstract base class for things with names."
    name        = models.CharField(max_length=255)
    created     = models.DateTimeField(auto_now_add=True)
    modified    = models.DateTimeField(auto_now=True)

    name.alphabetic_filter = True

    class Meta:
        abstract = True
        ordering = ['name']

    def __unicode__(self):
        return self.name

class Asset(Thing):
    "Inherited class that owns the actual files."
    class Meta:
        permissions = (
                       ("can_download_asset", "Can download asset"),
                       ("can_stream_asset", "Can stream asset"),
                      )

    def get_assetfile_count(self):
        return self.assetfile_set.count()
    get_assetfile_count.short_description = 'files'

class AssetFile(Thing):
    "Describes an underlying file for an Asset."
    asset       = models.ForeignKey(Asset)
    contents    = models.FileField(upload_to=_get_upload_path, max_length=255)
    mimetype    = models.CharField(max_length=255, choices=MIMETYPE_CHOICES,
                                   blank=True, verbose_name="MIME type")
    length      = models.FloatField(blank=True, null=True,
                    help_text="Length of file, in seconds")

    class Meta:
        order_with_respect_to = 'asset'

    @property
    def filename(self):
        if hasattr(self.asset, 'track') and self.mimetype.startswith('audio'):
            if self.mimetype == 'audio/mpeg': exten = '.mp3'
            elif self.mimetype == 'audio/mp4': exten = '.m4a'
            else: exten = mimetypes.guess_extension(self.mimetype, False)
            return u"{0}{1}".format(self.asset.track.name, exten)
        else:
            return u"{0}{1}".format(self.name,
                                  mimetypes.guess_extension(
                                    self.mimetype, False))

    def get_descriptor_admin_links(self):
        out = u'<ul>'
        for descriptor in self.assetdescriptor_set.all():
            out += (u'<li><a href="{url}">{text}</a>: '
                    u'{bit_rate} b/s, {sample_rate} Hz'
                   ).format(
                        url=reverse('admin:assets_assetdescriptor_change',
                            args=(descriptor.id,)),
                        text=unicode(descriptor), **descriptor.__dict__
                        )
            if descriptor.is_vbr: out += (u', VBR')
            if descriptor.lossy is False: out += (u', lossless')
            out += u'</li>'
        out += u'</ul>'
        if self.pk: out += u'<a href="{url}">Add new</a> (advanced)'.format(
                        url=reverse('admin:assets_assetdescriptor_add'),
                    )
        return out
    get_descriptor_admin_links.allow_tags = True
    get_descriptor_admin_links.short_description = 'Stream descriptors'

class AssetDescriptor(models.Model):
    "Describes a bitstream in a possibly-multiplexed file."
    assetfile   = models.ForeignKey(AssetFile)
    bitstream   = models.IntegerField(default=0)
    mimetype    = models.CharField(max_length=255, choices=MIMETYPE_CHOICES,
                                   default='application/octet-stream',
                                   verbose_name="MIME type")

    bit_rate    = models.FloatField(blank=True, null=True)
    is_vbr      = models.NullBooleanField(blank=True, null=True,
                                          verbose_name="Variable bit rate")
    lossy       = models.NullBooleanField(blank=True, null=True)
    sample_rate = models.FloatField(blank=True, null=True)

    class Meta:
        ordering        = ['bitstream']
        unique_together = ('assetfile', 'bitstream')

    def __unicode__(self):
        return u"Stream {bitstream} ({mimetype})".format(**self.__dict__)

# Music-specific concepts.
class Artist(Thing):
    "A performing artist."
    is_prince   = models.BooleanField(default=False,
                    help_text=("If true, Unicode representation will be "
                               "O(+> between 1993 and 2000."),
                    verbose_name="Occasionally known as Prince")

    def __unicode__(self):
        return u"O(+>" if self.is_prince else self.name

    def get_track_admin_links(self):
        out = u'<ul>'
        for album in self.track_set.all().values('album').order_by('album').distinct():
            album = Album.objects.get(pk=album['album'])
            out += u'<li><a href="{url}">{album}</a>:</li>'.format(url=reverse('admin:assets_album_change', args=(album.id,)), album=album.name,)
            out += u'<ul>'
            for track in self.track_set.filter(album=album).order_by('disc_number', 'track_number'):
                out += (u'<li><a href="{url}">Track {tn}</a>: '
                        u'{artist} / {name}</li>'
                       ).format(
                        url=reverse('admin:assets_track_change',
                            args=(track.id,)),
                        tn=track.get_pretty_track_number(),
                        artist=track.artist.name,
                        name=track.name,
                       )
            out += u'</ul>'
        out += u'</ul>'
        return out
    get_track_admin_links.allow_tags = True
    get_track_admin_links.short_description = 'Tracks'

class Album(Thing):
    """
    One album of tracks.

    This corresponds approximately to the unit of sale for a group of
    tracks.  It may consist of multiple discs, or none at all.

    Notice that there is no Artist here.  This can happen with
    compilations, etc.
    """
    is_compilation  = models.BooleanField(default=False,
                        help_text="Contains the work of distinct artists.")
    discs           = models.IntegerField(default=1,
                        help_text="Quantity of discs in the set.")

    def get_track_admin_links(self):
        out = u'<ul>'
        for track in self.track_set.all().order_by('track_number'):
            out += (u'<li><a href="{url}">Track {tn}</a>: '
                    u'{artist} / {name}</li>'
                   ).format(
                        url=reverse('admin:assets_track_change',
                            args=(track.id,)),
                        tn=track.get_pretty_track_number(),
                        artist=track.artist.name,
                        name=track.name,
                    )
        if self.pk: out += u'<li><a href="{url}">Add new...</a></li>'.format(
                        url=reverse('admin:assets_track_add'),
                    )
        out += u'</ul>'
        return out
    get_track_admin_links.allow_tags = True
    get_track_admin_links.short_description = 'Tracks'

class Track(Asset):
    """
    One track from an album.

    When multiple recordings of a song exist, each one should be its own
    track.  However, a recording may be stored as multiple files, perhaps
    MP3 and FLAC, or multiple bitrates, or, ...
    """
    artist      = models.ForeignKey("Artist")
    album       = models.ForeignKey("Album")
    year        = models.IntegerField(blank=True, null=True)

    disc_number = models.IntegerField(blank=True, null=True)
    track_number = models.IntegerField(blank=True, null=True)

    length      = models.IntegerField(blank=True, null=True,
                    help_text="Duration of track, in seconds.")
    bpm         = models.FloatField(blank=True, null=True,
                    help_text="unce unce unce unce unce",
                    verbose_name="BPM")

    class Meta:
        order_with_respect_to   = 'album'
        ordering                = ['disc_number', 'track_number']

    def get_display_name(self):
        return u'{0} - {1}'.format(self.artist, self.name)

    def get_pretty_track_number(self):
        # TODO: ID3 spec specifies X/Y = Track X of Y
        # This is probably quite confusing.
        dn = self.disc_number if (self.disc_number and
                                self.disc_number > 0) else None
        tn = self.track_number if (self.track_number and
                                self.track_number > 0) else None
        if dn and tn: return u"{0}/{1}".format(dn, tn)
        elif tn:      return u"{0}".format(tn)
        else:         return u""
    get_pretty_track_number.short_description = 'track number'
    get_pretty_track_number.admin_order_field = 'track_number'

    def get_artwork_url(self, **kwargs):
        qs = self.assetfile_set.filter(mimetype__startswith='image/').order_by('?')
        if qs.exists():
            return qs[0].contents.url
        return None

    def get_streaming_url(self, **kwargs):
        "Returns the best URL for this object."
        return self.assetfile_set.all()[0].contents.url

    def get_streaming_exten(self, **kwargs):
        return self.assetfile_set.all()[0].contents.name[-3:]

    def _inspect_files(self, qs=None, update_artist=False, update_album=False):
        if not qs:
            qs = self.assetfile_set.all()
        for assetfile in qs:
            inspobj = Inspector(assetfile.contents, assetfile.mimetype)

            if not inspobj.mimetype.startswith('audio/'):
                continue

            if (not self.artist or update_artist) and hasattr(inspobj, 'artist') and inspobj.artist:
                self.artist, created = Artist.objects.get_or_create(
                    name__iexact=inspobj.artist.strip(),
                )
            if (not self.album or update_album) and hasattr(inspobj, 'album') and inspobj.album:
                self.album, created = Album.objects.get_or_create(
                    name__iexact=inspobj.album.strip(),
                )

            if hasattr(inspobj, 'is_compilation') and inspobj.is_compilation is not None:
                self.album.is_compilation = inspobj.is_compilation
                self.album.save()

            self.name = getattr(inspobj, 'name', None) or self.name
            self.year = getattr(inspobj, 'year', None) or self.year
            self.disc_number = getattr(inspobj, 'disc', None) or self.disc_number
            self.track_number = getattr(inspobj, 'track', None) or self.track_number

            self.length = getattr(inspobj, 'length', None) or self.length
            assetfile.length = getattr(inspobj, 'length', None) or assetfile.length
            assetfile.mimetype = getattr(inspobj, 'mimetype', assetfile.mimetype)

            descriptor, created = assetfile.assetdescriptor_set.get_or_create(bitstream=0, defaults={
                'mimetype': assetfile.mimetype,
                'bit_rate': getattr(inspobj, 'bitrate', None),
                'is_vbr': getattr(inspobj, 'is_vbr', None),
                'lossy': getattr(inspobj, 'lossy', None),
                'sample_rate': getattr(inspobj, 'samplerate', None),
            })

            for apic in getattr(inspobj, 'artwork', []):
                # We have a picture!  Extract it onto its own AssetFile.
                apic_obj_fn = u'APIC-{0}-{1}'.format(
                    self.pk,
                    assetfile.pk,
                )
                apic_obj, apic_created = AssetFile.objects.get_or_create(
                    asset = self,
                    mimetype = apic['mimetype'],
                    name = apic_obj_fn,
                )
                apic_obj.contents.save(apic_obj_fn, ContentFile(apic['data']))
                apic_obj.save()
