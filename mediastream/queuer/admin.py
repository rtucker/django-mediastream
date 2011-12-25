from django.conf import settings
from django.contrib import admin
from django.contrib.contenttypes import generic
from mediastream.queuer.models import AssetQueue, AssetQueueItem
from forms import AdminAssetQueueItemForm

#class AssetQueueItemInline(generic.GenericTabularInline):
class AssetQueueItemInline(admin.TabularInline):
    model = AssetQueueItem
    form = AdminAssetQueueItemForm
    extra = 0
    fields = ['content_type', 'object_id', 'artist', 'album', 'state']
    readonly_fields = ['state', 'artist', 'album']

    def artist(self, obj=None):
        if not obj:
            return u''
        if obj.content_type.name == 'track':
            return u'<strong>{0}</strong>'.format(obj.asset_object.track.artist.name)
        return u''
    artist.allow_tags = True

    def album(self, obj=None):
        if not obj:
            return u''
        if obj.content_type.name == 'track':
            return u'<strong>{0}</strong>'.format(obj.asset_object.track.album.name)
        return u''
    album.allow_tags = True

class AssetQueueAdmin(admin.ModelAdmin):
    inlines = [
        AssetQueueItemInline,
    ]

    list_display = ['id', 'user', 'created', 'modified', 'get_playing_state', 'get_waiting_count', 'get_item_count']
    list_filter = ['created', 'modified', 'user']

    readonly_fields = ['created', 'modified', 'get_playing_state', 'get_waiting_count', 'get_item_count', 'delete_old_tracks']

    fieldsets = (
        ('', 
            {
             'fields': (
                ('user', 'created', 'modified',),
                ('get_playing_state', 'get_waiting_count', 'get_item_count',
                 'delete_old_tracks',),
             ),
            },
        ),
    )

    class Media:
        js = ('%squeuer_select_old_deletes.js' % (settings.STATIC_URL),)

    def get_playing_state(self, obj=None):
        if not obj:
            return False
        return obj.item_set.filter(state='playing').exists()
    get_playing_state.boolean = True
    get_playing_state.short_description = 'Playing?'

    def get_waiting_count(self, obj=None):
        if not obj:
            return u''
        return obj.item_set.filter(state='waiting').count()
    get_waiting_count.short_description = 'Remaining'

    def get_item_count(self, obj=None):
        if not obj:
            return u''
        return obj.item_set.count()
    get_item_count.short_description = 'Total'

    def delete_old_tracks(self, obj=None):
        if not obj:
            return u''
        return u'<span id="select_old_deletes_trigger">Select all</span>'
    delete_old_tracks.short_description = 'Delete played tracks'
    delete_old_tracks.allow_tags = True

admin.site.register(AssetQueue, AssetQueueAdmin)
