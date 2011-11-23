from django.db import models
from django.contrib.auth.models import User
from mediastream.assets.models import Asset

class AssetQueue(models.Model):
    "Stores an ordered play list of assets."
    user = models.ForeignKey(User)
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    def __unicode__(self):
        return u"Queue {} created by {} at {}".format(self.pk, self.user, self.created)

    def get_offer_set(self, items=3):
        "Returns a QuerySet of items waiting in the queue."
        qs = self.item_set.filter(state='waiting')[:items]
        return qs

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
    asset = models.ForeignKey(Asset)
    state = models.CharField(max_length=10, choices=STATE_CHOICES, default='waiting')
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    class Meta:
        order_with_respect_to = 'queue'
        ordering = ['created']

    def __unicode__(self):
        return u"Item {} in {} ({})".format(self.pk, self.queue, self.get_state_display())
