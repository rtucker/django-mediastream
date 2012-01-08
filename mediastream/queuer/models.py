from django.db import models
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes import generic
from mediastream.assets.models import Asset, Album, Track

try:
    aqi_default_ct = ContentType.objects.get_for_model(Track)
except:
    aqi_default_ct = 1

class AssetQueue(models.Model):
    "Stores an ordered play list of assets."
    user = models.ForeignKey(User)
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    def __unicode__(self):
        return u"Queue {0} for {1}".format(self.pk, self.user)

class AssetQueueItem(models.Model):
    STATE_CHOICES = (
                     ('waiting', 'Waiting in queue'),
                     ('offered', 'Offered to client'),
                     ('playing', 'Playing on client'),
                     ('played', 'Has been played'),
                     ('skipped', 'Skipped by the user'),
                     ('fileerror', 'File error encountered by client'),
                    )

    queue = models.ForeignKey(AssetQueue, related_name='item_set')
    content_type = models.ForeignKey(ContentType,
        default=aqi_default_ct,
        limit_choices_to = {"model__in": ('track', 'album')},
        verbose_name = "Media type",
    )
    object_id = models.PositiveIntegerField(
        verbose_name = "Asset",
    )
    asset_object = generic.GenericForeignKey('content_type', 'object_id')
    state = models.CharField(max_length=10, choices=STATE_CHOICES, default='waiting')
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    class Meta:
        # TODO: order_with_respect_to = 'queue', then actually make sure it
        # all goes in the right order...
        ordering = ['id']

    def __unicode__(self):
        return u"Item {0} in {1} ({2})".format(self.pk, self.queue,
                                            self.get_state_display())

    @property
    def asset(self):
        return self.asset_object

    def save(self, *args, **kwargs):
        if self.content_type.model == 'album':
            # Explode the album.
            for track in self.asset_object.track_set.order_by('disc_number', 'track_number'):
                AssetQueueItem.objects.create(
                    queue = self.queue,
                    asset_object = track,
                    state = 'waiting',
                )
            return
        super(AssetQueueItem, self).save(*args, **kwargs)
