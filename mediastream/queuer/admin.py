from django.core import urlresolvers
from django.conf import settings
from django.core.cache import cache
from django.contrib import admin
from django.contrib.contenttypes import generic
from models import AssetQueue, AssetQueueItem
from forms import AdminAssetQueueItemForm
from collections import defaultdict

#class AssetQueueItemInline(generic.GenericTabularInline):
class AssetQueueItemInline(admin.TabularInline):
    model = AssetQueueItem
    form = AdminAssetQueueItemForm
    extra = 0
    fields = ['content_type', 'object_id', 'name', 'artist', 'album', 'state', 'modified']
    readonly_fields = ['state', 'artist', 'album', 'modified', 'name']

    _datacache = defaultdict(lambda: None)

    def _fetch_missing_data(self, obj=None):
        if obj is not None:
            cache_key = __name__ + '.AQII_datacache3.' + str(obj.pk)

            if self._datacache[obj.pk] is None:
                self._datacache[obj.pk] = cache.get(cache_key)
            if self._datacache[obj.pk] is None:
                self._datacache[obj.pk] = {
                    'ctname': obj.content_type.name,
                    'artist': obj.asset_object.track.artist.name,
                    'artistpk': obj.asset_object.track.artist.pk,
                    'album': obj.asset_object.track.album.name,
                    'albumpk': obj.asset_object.track.album.pk,
                    'track': obj.asset_object.track.name,
                    'trackpk': obj.asset_object.track.pk,
                }
                cache.set(cache_key, self._datacache[obj.pk])

    def _getdata(self, key, obj=None):
        self._fetch_missing_data(obj)
        return self._datacache[obj.pk][key]

    def _content_type_name(self, obj=None):
        if not obj:
            return None
        return self._getdata('ctname', obj)

    def artist(self, obj=None):
        if not obj:
            return u''
        if self._content_type_name(obj) == 'track':
            return u'<strong><a href="{0}">{1}</a></strong>'.format(urlresolvers.reverse('admin:assets_artist_change', args=(self._getdata('artistpk', obj),)), self._getdata('artist', obj))
        return u''
    artist.allow_tags = True

    def album(self, obj=None):
        if not obj:
            return u''
        if self._content_type_name(obj) == 'track':
            return u'<strong><a href="{0}">{1}</a></strong>'.format(urlresolvers.reverse('admin:assets_album_change', args=(self._getdata('albumpk', obj),)), self._getdata('album', obj))
        return u''
    album.allow_tags = True

    def name(self, obj=None):
        if not obj:
            return u''
        if self._content_type_name(obj) == 'track':
            return u'<strong><a href="{0}">{1}</a></strong>'.format(urlresolvers.reverse('admin:assets_track_change', args=(self._getdata('trackpk', obj),)), self._getdata('track', obj))
        return u''
    name.allow_tags = True

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
