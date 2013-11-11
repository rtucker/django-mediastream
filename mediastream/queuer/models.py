from django.db import models
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes import generic
from django.core.cache import cache
from mediastream.assets.models import Asset, Album, Track

from datetime import datetime, timedelta

try:
    aqi_default_ct = ContentType.objects.get_for_model(Track)
except:
    aqi_default_ct = 1

class AssetQueue(models.Model):
    "Stores an ordered play list of assets."
    user = models.ForeignKey(User)
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)
    randomize = models.BooleanField(default=True, help_text="When running low on assets, choose random ones?")
    expire_old_items = models.BooleanField(default=True, help_text="Purge records of old played and skipped assets?")

    _unicode_cache = None

    def __unicode__(self):
        cache_key = __name__ + '.AssetQueue.__unicode__.' + str(self.pk)
        if self._unicode_cache is None:
            self._unicode_cache = cache.get(cache_key)
        if self._unicode_cache is None:
            self._unicode_cache = u"Queue {0} for {1}".format(self.pk, self.user.username)
            cache.set(cache_key, self._unicode_cache)
        return self._unicode_cache

    def do_expire_old_items(self):
        "Deletes queue items older than a day."
        if self.expire_old_items:
            too_old = datetime.now() - timedelta(days=1)
            qs = self.item_set.filter(
                    state__in=['played', 'skipped'],
                    modified__lt=too_old,
                 )
            return qs.delete()

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

    _unicode_cache = None

    class Meta:
        # TODO: order_with_respect_to = 'queue', then actually make sure it
        # all goes in the right order...
        ordering = ['id']

    def __unicode__(self):
        cache_key = __name__ + '.AssetQueueItem.__unicode__.' + str(self.pk)
        if self._unicode_cache is None:
            self._unicode_cache = cache.get(cache_key)
        if self._unicode_cache is None:
            self._unicode_cache = u"Item {0} in {1} ({2})".format(self.pk, self.queue,
                                            self.get_state_display())
            cache.set(cache_key, self._unicode_cache)
        return self._unicode_cache

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
