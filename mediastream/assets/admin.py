from django.conf import settings
from django.contrib import admin
from django.db.models import Avg, Max, Min, Count
from mediastream.assets.models import *

class AlbumAdmin(admin.ModelAdmin):
    def queryset(self, request):
        qs = super(AlbumAdmin, self).queryset(request)
        return qs.annotate(
                    artist_count=Count('track__artist', distinct=True),
                    track_count=Count('track', distinct=True),)

    list_display    = ['__unicode__', 'is_compilation', 'discs',
                       'get_artist_count', 'get_track_count',]
    list_filter     = ['is_compilation', 'discs', 'name',]
    search_fields   = ['name', 'track__name',]
    readonly_fields = ['get_track_admin_links',]

    def get_artist_count(self, obj): return obj.artist_count
    get_artist_count.admin_order_field = 'artist_count'
    get_artist_count.short_description = 'Artists'

    def get_track_count(self, obj): return obj.track_count
    get_track_count.admin_order_field = 'track_count'
    get_track_count.short_description = 'Tracks'

admin.site.register(Album, AlbumAdmin)

class ArtistAdmin(admin.ModelAdmin):
    def queryset(self, request):
        qs = super(ArtistAdmin, self).queryset(request)
        return qs.annotate(
                    album_count=Count('track__album', distinct=True),
                    track_count=Count('track', distinct=True),)

    list_display    = ['__unicode__', 'is_prince',
                       'get_album_count', 'get_track_count',]
    list_filter     = ['is_prince', 'name',]
    search_fields   = ['name', 'track__name',]
    readonly_fields = ['get_track_admin_links',]

    def get_album_count(self, obj): return obj.album_count
    get_album_count.admin_order_field = 'album_count'
    get_album_count.short_description = 'Albums'

    def get_track_count(self, obj): return obj.track_count
    get_track_count.admin_order_field = 'track_count'
    get_track_count.short_description = 'Tracks'

admin.site.register(Artist, ArtistAdmin)

class AssetDescriptorAdmin(admin.ModelAdmin):
    pass
admin.site.register(AssetDescriptor, AssetDescriptorAdmin)

class AssetFileInline(admin.StackedInline):
    model           = AssetFile
    extra           = 1
    readonly_fields = ['get_descriptor_admin_links',]

    fieldsets       = (
        ('', {
              'classes': ('asidecol', 'float-right',),
              'fields': ('get_descriptor_admin_links',),
        }),
        ('', {
              'classes': ('maincol',),
              'fields': ('name', 'mimetype', 'contents',),
        }),
    )

class TrackAdmin(admin.ModelAdmin):
    inlines         = [AssetFileInline,]

    list_display    = ['__unicode__', 'artist', 'album',
                       'get_pretty_track_number', 'get_pretty_length',
                       'get_assetfile_count',]
    list_filter     = ['artist__name', 'album__name', 'name']
    search_fields   = ['artist__name', 'album__name', 'name']
    ordering        = ['artist']

    class Media:
        js = ('%s/collapse_filter.js' % (settings.STATIC_URL),)

    def get_pretty_length(self, obj):
        if obj.length:
            return u"{0}:{1:02d}".format(obj.length / 60, obj.length % 60)
    get_pretty_length.short_description = 'length'
    get_pretty_length.admin_order_field = 'length'

admin.site.register(Track, TrackAdmin)

class PlayAdmin(admin.ModelAdmin):
    readonly_fields = ['asset', 'previous_play', 'context', 'played', 'queue']
admin.site.register(Play, PlayAdmin)
