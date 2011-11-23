from django.conf import settings
from django.db import models

import mimetypes
import os

basepath = getattr(settings, 'ASSETS_UPLOAD_TO', '/assets')

# Cook the mimetypes a bit, so they make good choices
mimetypes_grouped = {}
for mt in mimetypes.types_map.values():
    mt0, mt1 = mt.split('/',1)
    if mt0 not in mimetypes_grouped:
        mimetypes_grouped[mt0] = []
    if (mt, mt1) not in mimetypes_grouped[mt0]:
        mimetypes_grouped[mt0].append((mt, mt1))
    mimetypes_grouped[mt0].sort()

MIMETYPE_CHOICES = sorted(mimetypes_grouped.items())

def _get_upload_path(instance, filename):
    if not instance.mimetype:
        instance.mimetype = mimetypes.guess_type(filename)[0]

    if hasattr(instance.asset, 'track'):
        if instance.asset.track.album.is_compilation:
            return os.path.join(basepath, 'V', 'Various Artists', instance.asset.track.album.name, instance.filename)
        else:
            return os.path.join(basepath, instance.asset.track.artist.name.upper()[0], instance.asset.track.artist.name, instance.asset.track.album.name, instance.filename)
    else:
        return os.path.join(basepath, instance.filename)

# Broad, generic things.
class Thing(models.Model):
    "Abstract base class for things with names."
    name = models.CharField(max_length=255)
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

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

class AssetFile(Thing):
    "Describes an underlying file for an Asset."
    asset = models.ForeignKey(Asset)
    contents = models.FileField(upload_to=_get_upload_path)
    mimetype = models.CharField(max_length=255, choices=MIMETYPE_CHOICES, blank=True)

    class Meta:
        order_with_respect_to = 'asset'

    @property
    def filename(self):
        if hasattr(self.asset, 'track'):
            return u"{}{}".format(self.asset.track.name, mimetypes.guess_extension(self.mimetype, False))
        else:
            return u"{}{}".format(self.name, mimetypes.guess_extension(self.mimetype, False))

class AssetDescriptor(models.Model):
    "Describes a bitstream in a possibly-multiplexed file."
    assetfile = models.ForeignKey(AssetFile)
    bitstream = models.IntegerField(default=0)
    mimetype = models.CharField(max_length=255, choices=MIMETYPE_CHOICES, default='application/octet-stream')

    bit_rate = models.FloatField(blank=True, null=True)
    is_vbr = models.NullBooleanField(blank=True, null=True)
    lossy = models.NullBooleanField(blank=True, null=True)
    sample_rate = models.FloatField(blank=True, null=True)

    class Meta:
        ordering = ['bitstream']
        unique_together = ('assetfile', 'bitstream')

    def __unicode__(self):
        return u"Stream {bitstream} ({mimetype})".format(**self.__dict__)

# Music-specific concepts.
class Artist(Thing):
    "A performing artist."
    is_prince = models.BooleanField(default=False, help_text="If true, Unicode representation will be O(+> between 1993 and 2000.", verbose_name="Is often known as Prince")

    def __unicode__(self):
        return u"O(+>" if self.is_prince else self.name

class Album(Thing):
    """
    One album of tracks.

    This corresponds approximately to the unit of sale for a group of
    tracks.  It may consist of multiple discs, or none at all.

    Notice that there is no Artist here.  This can happen with
    compilations, etc.
    """
    is_compilation = models.BooleanField(default=False, help_text="Contains the work of distinct artists.")
    discs = models.IntegerField(default=1, help_text="Quantity of discs in the set.")

class Track(Asset):
    """
    One track from an album.

    When multiple recordings of a song exist, each one should be its own
    track.  However, a recording may be stored as multiple files, perhaps
    MP3 and FLAC, or multiple bitrates, or, ...
    """

    # Pedigree
    artist = models.ForeignKey("Artist")
    album = models.ForeignKey("Album")
    year = models.IntegerField(blank=True, null=True)

    # Physical media reference
    disc_number = models.IntegerField(blank=True, null=True)
    track_number = models.IntegerField(blank=True, null=True)

    # Structural data independent of compression/archiving
    length = models.IntegerField(blank=True, null=True, help_text="Duration of track, in seconds.")
    bpm = models.FloatField(blank=True, null=True, help_text="unce unce unce unce unce")

    class Meta:
        order_with_respect_to = 'album'
        ordering = ['disc_number', 'track_number']

    def get_streaming_url(self, **kwargs):
        "Returns the best URL for this object."
        return self.assetfile_set.all()[0].contents.url
