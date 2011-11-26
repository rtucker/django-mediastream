from django.conf import settings
from django.core.files.base import ContentFile
from django.core.urlresolvers import reverse
from django.db import models
from django.db.models import Avg, Max, Min, Count

import mimetypes
from mutagen.mp3 import MPEGInfo

from mediastream.assets import MIMETYPE_CHOICES, _get_upload_path
from mediastream.utilities.mediainspector import ID3File

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
        if hasattr(self.asset, 'track'):
            return u"{0}{1}".format(self.asset.track.name,
                                  mimetypes.guess_extension(
                                    self.mimetype, False))
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

    def _inspect_mp3(self):
        "Cracks open the mp3 file and determines what is inside."
        self.contents.seek(0)
        infoobj = MPEGInfo(self.contents)
        ad, created = self.assetdescriptor_set.get_or_create(bitstream=0)
        if not infoobj.sketchy:
            self.mimetype = ad.mimetype = 'audio/mpeg'
        self.length = infoobj.length
        ad.bit_rate = infoobj.bitrate
        ad.sample_rate = infoobj.sample_rate
        ad.lossy = True

        self.contents.seek(0)
        id3obj = ID3File(self.contents)
        # This is actually a remarkably grody object.
        # See http://code.google.com/p/mutagen/source/browse/trunk/mutagen/easyid3.py
        if 'TIT2' in id3obj:
            self.asset.name = id3obj.get('TIT2').text[0]

        apic = id3obj.getall('APIC')
        if apic:
            # hot dang, we have an artist pic
            apic_obj, apic_created = AssetFile.objects.get_or_create(
                asset = self.asset,
                mimetype = apic[0].mime,
                name = apic[0].pprint(),
            )
            apic_obj_fn = u'APIC-{0}-{1}{2}'.format(
                apic[0].type or 'X',
                self.name.replace('.','_'),
                mimetypes.guess_extension(apic[0].mime, strict=False),
            )
            apic_obj.contents.save(apic_obj_fn, ContentFile(apic[0].data))
            apic_obj.save()

        if 'TDRC' in id3obj:
            # special case: date
            try:
                self.asset.track.year = int(id3obj['TDRC'].text[0].year)
            except:
                pass

        if 'TRCK' in id3obj:
            # Track number
            self.asset.track.track_number = +id3obj.get('TRCK')

        if 'TPOS' in id3obj:
            # Part of set
            self.asset.track.disc_number = +id3obj.get('TPOS')

        ad.save()
        self.save()

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

    def get_streaming_url(self, **kwargs):
        "Returns the best URL for this object."
        return self.assetfile_set.all()[0].contents.url

    def get_streaming_exten(self, **kwargs):
        return self.assetfile_set.all()[0].contents.name[-3:]
