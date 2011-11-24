from django.contrib import admin
from django.contrib.contenttypes import generic
from mediastream.queuer.models import AssetQueue, AssetQueueItem
from forms import AdminAssetQueueItemForm

#class AssetQueueItemInline(generic.GenericTabularInline):
class AssetQueueItemInline(admin.TabularInline):
    model = AssetQueueItem
    form = AdminAssetQueueItemForm
    extra = 0

class AssetQueueAdmin(admin.ModelAdmin):
    inlines = [
        AssetQueueItemInline,
    ]
admin.site.register(AssetQueue, AssetQueueAdmin)
