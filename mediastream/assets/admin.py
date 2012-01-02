# -*- coding: utf-8 -*-
from django.conf import settings
from django.contrib import admin
from django.contrib.contenttypes.generic import GenericTabularInline
from django.contrib.humanize.templatetags.humanize import naturalday
from django.core.urlresolvers import reverse
from django.db.models import Avg, Max, Min, Count
from assets.models import *
from tags.models import TaggedItem

class TaggedItemInline(GenericTabularInline):
    model = TaggedItem

class AlbumAdmin(admin.ModelAdmin):
    def queryset(self, request):
        qs = super(AlbumAdmin, self).queryset(request)
        return qs.annotate(
                    artist_count=Count('track__artist', distinct=True),
                    track_count=Count('track', distinct=True),)

    inlines         = [TaggedItemInline,]
    list_display    = ['__unicode__', 'get_artist_name', 'is_compilation',
                       'discs', 'get_artist_count', 'get_track_count',]
    list_filter     = ['is_compilation', 'discs', 'name', 'created',]
    search_fields   = ['name', 'track__name',]
    readonly_fields = ['get_track_admin_links', 'get_discogs_resource_url', 'get_discogs_data_quality', 'get_discogs_artists', 'get_discogs_credits', 'get_discogs_notes',]

    fieldsets = (
        ('', {
            'fields': (
                ('name', 'is_compilation',),
                'discs',
            ),
        }),
        ('Discogs', {
            'fields': (
                'get_discogs_resource_url',
                'get_discogs_data_quality',
                'get_discogs_artists',
                'get_discogs_credits',
                'get_discogs_notes',
            ),
        }),
        ('Track listing', {
            'fields': (
                'get_track_admin_links',
            ),
        }),
    )

    def get_artist_name(self, obj):
        artists = obj.track_set.values_list('artist__name', flat=True).annotate(Count('id')).order_by('-id__count')
        if len(artists) > 3:
            artists = list(artists[0:3]) + ['...']
        return ', '.join(artists)
    get_artist_name.admin_order_field = 'track__artist'
    get_artist_name.short_description = 'Artists'

    def get_artist_count(self, obj): return obj.artist_count
    get_artist_count.admin_order_field = 'artist_count'
    get_artist_count.short_description = 'Artist count'

    def get_track_count(self, obj): return obj.track_count
    get_track_count.admin_order_field = 'track_count'
    get_track_count.short_description = 'Tracks'

    def get_discogs_notes(self, obj):
        if obj.discogs:
            return obj.discogs.data['notes']
    get_discogs_notes.short_description='Notes'

    def get_discogs_artists(self, obj):
        if obj.discogs:
            return ', '.join([f['name'] for f in obj.discogs.data['artists']])
    get_discogs_artists.short_description='Artists'

    def get_discogs_credits(self, obj):
        if obj.discogs:
            return u'<br/>'.join([u'{role}{tl}{tracks} – <a href="{resource_url}" target="_blank">{name}</a>'.format(tl=', tracks ' if f['tracks'] else '', **f) for f in obj.discogs.data['extraartists']])
    get_discogs_credits.short_description='Credits'
    get_discogs_credits.allow_tags = True

    def get_discogs_data_quality(self, obj):
        if obj.discogs:
            return '{0} (retrieved {1})'.format(
                obj.discogs.data['data_quality'],
                naturalday(obj.discogs.data_cache_dttm),
            )
    get_discogs_data_quality.short_description='Data quality'

    def get_discogs_resource_url(self, obj):
        if obj.discogs:
            return '<a href="{resource_url}" target="_blank">Discogs ID {id}</a>'.format(**obj.discogs.data)
    get_discogs_resource_url.allow_tags=True
    get_discogs_resource_url.short_description='Resource'


admin.site.register(Album, AlbumAdmin)

class ArtistAdmin(admin.ModelAdmin):
    def queryset(self, request):
        qs = super(ArtistAdmin, self).queryset(request)
        return qs.annotate(
                    album_count=Count('track__album', distinct=True),
                    track_count=Count('track', distinct=True),)

    inlines         = [TaggedItemInline,]
    list_display    = ['__unicode__', 'is_prince',
                       'get_album_count', 'get_track_count',]
    list_filter     = ['is_prince', 'name', 'created',]
    search_fields   = ['name', 'track__name',]
    readonly_fields = ['get_track_admin_links', 'get_discogs_resource_url', 'get_discogs_data_quality', 'get_discogs_members', 'get_discogs_profile',]

    fieldsets = (
        ('', {
            'fields': (
                ('name', 'is_prince',),
            ),
        }),
        ('Discogs', {
            'fields': (
                'get_discogs_resource_url',
                'get_discogs_data_quality',
                'get_discogs_members',
                'get_discogs_profile',
            ),
        }),
        ('Track listing', {
            'fields': (
                'get_track_admin_links',
            ),
        }),
    )

    def get_album_count(self, obj): return obj.album_count
    get_album_count.admin_order_field = 'album_count'
    get_album_count.short_description = 'Albums'

    def get_track_count(self, obj): return obj.track_count
    get_track_count.admin_order_field = 'track_count'
    get_track_count.short_description = 'Tracks'

    def get_discogs_profile(self, obj):
        if obj.discogs:
            return obj.discogs.data['profile']
    get_discogs_profile.short_description='Profile'

    def get_discogs_members(self, obj):
        if obj.discogs:
            return ', '.join(obj.discogs.data['members'])
    get_discogs_members.short_description='Members'

    def get_discogs_data_quality(self, obj):
        if obj.discogs:
            return '{0} (retrieved {1})'.format(
                obj.discogs.data['data_quality'],
                naturalday(obj.discogs.data_cache_dttm),
            )
    get_discogs_data_quality.short_description='Data quality'

    def get_discogs_resource_url(self, obj):
        if obj.discogs:
            return '<a href="{resource_url}" target="_blank">Discogs ID {id}</a>'.format(**obj.discogs.data)
    get_discogs_resource_url.allow_tags=True
    get_discogs_resource_url.short_description='Resource'

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
    inlines         = [TaggedItemInline, AssetFileInline,]

    list_display    = ['__unicode__', 'artist', 'album',
                       'get_pretty_track_number', 'get_pretty_length',
                       'get_assetfile_count', 'total_plays', 'average_rating']
    list_filter     = ['artist__name', 'album__name', 'name', 'created',]
    search_fields   = ['artist__name', 'album__name', 'name']
    ordering        = ['artist',]
    readonly_fields = ['average_rating', 'get_streamable_assetfile',
                       'artwork_preview', 'total_plays',]

    date_hierarchy  = 'created'

    fieldsets       = (
        ('Media Summary', {
            'classes': ('collapse', 'float-right',),
            'fields': ('artwork_preview', 'get_streamable_assetfile',),
        }),
        ('Track Data', {
            'classes': (),
            'fields': ('name', 'artist', 'album', 'year',
                        ('disc_number', 'track_number',),
                        ('length', 'bpm',),
                        ('total_plays', 'average_rating',),
                        'skip_random',
                      ),
        }),
    )

    class Media:
        js = ('%scollapse_filter.js' % (settings.STATIC_URL),)

    def artwork_preview(self, obj):
        candidate = obj.get_artwork_url()
        if candidate:
            return u'<img src="{0}" width="420px">'.format(candidate)
        return u''
    artwork_preview.allow_tags=True

    def get_pretty_length(self, obj):
        if obj.length:
            return u"{0}:{1:02d}".format(obj.length / 60, obj.length % 60)
    get_pretty_length.short_description = 'length'
    get_pretty_length.admin_order_field = 'length'

    def average_rating(self, obj):
        return Rating.objects.get_average_rating(obj) or ''

    def total_plays(self, obj):
        return Play.objects.filter(asset=obj).count() or ''

admin.site.register(Track, TrackAdmin)

class PlayAdmin(admin.ModelAdmin):
    list_display = ['created', 'get_asset_name', 'played']
    fields = ['get_asset_name', 'get_play_prev', 'get_play_next', 'context', 'played', 'queue', 'created', 'in_groove']
    readonly_fields = ['get_asset_name', 'get_play_prev', 'get_play_next', 'context', 'played', 'queue', 'created', 'in_groove']

    def get_asset_name(self, obj):
        if hasattr(obj.asset, 'track'):
            return u"{0} - {1} <i>({2})</i>".format(obj.asset.track.artist.name, obj.asset.track.name, obj.asset.track.album.name)
        else:
            return obj.asset.__unicode__()
    get_asset_name.short_description = "Asset"
    get_asset_name.allow_tags = True

    def get_play_next(self, obj):
        try:
            nextplay = Play.objects.get(previous_play=obj)
            return u'<a href="../{0}/">{1}</a>'.format(nextplay.pk, nextplay)
        except:
            return None
    get_play_next.short_description = "Next play"
    get_play_next.allow_tags = True

    def get_play_prev(self, obj):
        try:
            prevplay = obj.previous_play
            return u'<a href="../{0}/">{1}</a>'.format(prevplay.pk, prevplay)
        except:
            return None
    get_play_prev.short_description = "Previous play"
    get_play_prev.allow_tags = True
admin.site.register(Play, PlayAdmin)

class RatingAdmin(admin.ModelAdmin):
    list_display = ['play', 'modified', 'get_asset_name', 'user', 'get_rating_stars']
    fields = ['modified', 'get_asset_name', 'user', 'play', 'rating']
    readonly_fields = ['modified', 'get_asset_name', 'user', 'play', 'rating', 'get_rating_stars']

    def get_asset_name(self, obj):
        if hasattr(obj.asset, 'track'):
            return u"{0} - {1} <i>({2})</i>".format(obj.asset.track.artist.name, obj.asset.track.name, obj.asset.track.album.name)
        else:
            return obj.asset.__unicode__()
    get_asset_name.short_description = "Asset"
    get_asset_name.allow_tags = True

    def get_rating_stars(self, obj):
        return u'* ' * obj.rating
    get_rating_stars.short_description = "Rating"

admin.site.register(Rating, RatingAdmin)

class DiscogsAdmin(admin.ModelAdmin):
    list_display = ['__unicode__', 'get_asset', 'data_cache_dttm']
    date_hierarchy  = 'data_cache_dttm'

    readonly_fields = ['get_asset_link', 'data_cache', 'data_cache_dttm',]

    def get_asset_link(self, obj):
        asset = obj.get_asset()
        url = reverse('admin:{app_label}_{module_name}_change'.format(**asset._meta.__dict__), args=(asset.pk,))
        return u'{0} <a href="{1}">{2}</a>'.format(
            asset._meta.verbose_name,
            url,
            asset.name,
        ) 
    get_asset_link.short_description='Asset'
    get_asset_link.allow_tags=True

admin.site.register(Discogs, DiscogsAdmin)
