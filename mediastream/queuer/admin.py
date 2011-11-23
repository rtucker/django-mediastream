from django.contrib import admin
from mediastream.queuer.models import AssetQueue, AssetQueueItem

class AssetQueueItemInline(admin.TabularInline):
    model = AssetQueueItem

class AssetQueueAdmin(admin.ModelAdmin):
    inlines = [
        AssetQueueItemInline,
    ]
admin.site.register(AssetQueue, AssetQueueAdmin)

