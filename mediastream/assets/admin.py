# -*- coding: utf-8 -*-
from django.conf import settings
from django.contrib import admin
from django.contrib.contenttypes.generic import GenericTabularInline
from django.contrib.contenttypes.models import ContentType
from django.contrib.humanize.templatetags.humanize import naturalday
from django.core.urlresolvers import reverse
from django.db.models import Avg, Max, Min, Count
from django.http import HttpResponseRedirect
from django.template.defaultfilters import slugify
from django.utils import simplejson
from assets.models import *
from tags.models import Tag, TaggedItem
from utilities.recursion import html_tree

def link_to_discogs(modeladmin, request, queryset):
    rows_updated = 0
    rows_failed = 0
    tags_applied = 0
    for obj in queryset:
        try:
            d = Discogs.objects.get_for_object(obj)
            obj.discogs = d
            obj.save()
            rows_updated += 1
            for key in ['genres', 'styles']:
                for thing in d.data.get(key, []):
                    tag, c = Tag.objects.get_or_create(
                        label=slugify(thing),
                        parent=Tag.objects.get(label=key, parent=None),
                    )
                    TaggedItem.objects.get_or_create(
                        tag=tag,
                        content_type=ContentType.objects.get_for_model(obj),
                        object_id=obj.id,
                    )
        except Discogs.DoesNotExist:
            rows_failed += 1
    out = []
    if rows_updated > 0:
        out.append("Successfully updated %i row%s" % (
            rows_updated, '' if rows_updated == 1 else 's',))
    if rows_failed > 0:
        out.append("Failed to update %i row%s" % (
            rows_failed, '' if rows_failed == 1 else 's',))
    modeladmin.message_user(request, ', and '.join(out).capitalize())
link_to_discogs.short_description = 'Create Discogs records'

def merge_assets(modeladmin, request, queryset):
    selected = request.POST.getlist(admin.ACTION_CHECKBOX_NAME)
    ct = ContentType.objects.get_for_model(queryset.model)
    return HttpResponseRedirect(reverse('asset-merge', kwargs={'ct': ct.pk, 'ids': ','.join(selected)}))

def set_shared_with_all_off(modeladmin, request, queryset):
    rows_updated = 0
    if queryset.model is Track:
        rows_updated = queryset.update(shared_with_all=False)
    elif queryset.model is Album:
        for album in queryset:
            rows_updated += album.track_set.update(shared_with_all=False)
    modeladmin.message_user(request, "%i asset%s successfully unshared with all." %
        (rows_updated, '' if rows_updated == 1 else 's'))
set_shared_with_all_off.short_description = "Unshare assets with all users"

def set_shared_with_all_on(modeladmin, request, queryset):
    rows_updated = 0
    if queryset.model is Track:
        rows_updated = queryset.update(shared_with_all=True)
    elif queryset.model is Album:
        for album in queryset:
            rows_updated += album.track_set.update(shared_with_all=True)
    modeladmin.message_user(request, "%i asset%s successfully shared with all." %
        (rows_updated, '' if rows_updated == 1 else 's'))
set_shared_with_all_on.short_description = "Share assets with all users"

def take_ownership(modeladmin, request, queryset):
    rows_updated = 0
    if queryset.model is Track:
        rows_updated = queryset.update(owner=request.user)
    elif queryset.model is Album:
        for album in queryset:
            rows_updated += album.track_set.update(owner=request.user)
    modeladmin.message_user(request, "%i asset%s successfully taken by %s." %
        (rows_updated, '' if rows_updated == 1 else 's', request.user.username))
take_ownership.short_description = "Take ownership of assets"

class TaggedItemInline(GenericTabularInline):
    model = TaggedItem

class AlbumAdmin(admin.ModelAdmin):
    actions         = [link_to_discogs, merge_assets, set_shared_with_all_on,
                       set_shared_with_all_off, take_ownership,]
    inlines         = [TaggedItemInline,]
    list_display    = ['__unicode__', 'get_artist_name', 'is_compilation',
                       'discs', 'get_artist_count', 'get_track_count', 'get_play_count', 'discogs']
    list_filter     = ['is_compilation', 'discs', 'name', 'created',]
    search_fields   = ['name',]
    readonly_fields = ['get_track_admin_links', 'get_discogs_resource_url', 'get_discogs_data_quality', 'get_discogs_artists', 'get_discogs_credits', 'get_discogs_notes', 'get_play_count',]

    filter_horizontal = ['extra_artists',]

    fieldsets = (
        ('', {
            'fields': (
                ('name', 'is_compilation',),
                'discs',
            ),
        }),
        ('Discogs', {
            'fields': (
                'discogs',
                'get_discogs_resource_url',
                'get_discogs_data_quality',
                'get_discogs_artists',
                'get_discogs_credits',
                'get_discogs_notes',
            ),
        }),
        ('Tracks and Performers', {
            'fields': (
                ('get_track_admin_links', 'extra_artists',),
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

    def get_play_count(self, obj):
        return obj.play_count
    get_play_count.short_description = 'Play count'
    get_play_count.admin_order_field = 'play_count'

    def get_track_count(self, obj): return obj.track_count
    get_track_count.admin_order_field = 'track_count'
    get_track_count.short_description = 'Tracks'

    def get_discogs_notes(self, obj):
        if obj.discogs:
            return obj.discogs.data.get('notes', None)
    get_discogs_notes.short_description='Notes'

    def get_discogs_artists(self, obj):
        if obj.discogs:
            return ', '.join([f['name'] for f in obj.discogs.data.get('artists', [])])
    get_discogs_artists.short_description='Artists'

    def get_discogs_credits(self, obj):
        if obj.discogs:
            return u'<br/>'.join([u'{role}{tl}{tracks} – <a href="{resource_url}" target="_blank">{name}</a>'.format(tl=', tracks ' if f['tracks'] else '', **f) for f in obj.discogs.data.get('extraartists', [])])
    get_discogs_credits.short_description='Credits'
    get_discogs_credits.allow_tags = True

    def get_discogs_data_quality(self, obj):
        if obj.discogs:
            return '{0} (retrieved {1})'.format(
                obj.discogs.data.get('data_quality', 'unknown'),
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
    actions         = [link_to_discogs]

    inlines         = [TaggedItemInline,]
    list_display    = ['__unicode__', 'is_prince',
                       'get_album_count', 'get_track_count', 'get_play_count', 'discogs']
    list_filter     = ['is_prince', 'name', 'created',]
    search_fields   = ['name',]
    readonly_fields = ['get_track_admin_links', 'get_discogs_resource_url', 'get_discogs_data_quality', 'get_discogs_members', 'get_discogs_profile', 'get_play_count',]

    fieldsets = (
        ('', {
            'fields': (
                ('name', 'is_prince',),
            ),
        }),
        ('Discogs', {
            'fields': (
                'discogs',
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

    def get_play_count(self, obj):
        return obj.play_count
    get_play_count.short_description = 'Play count'
    get_play_count.admin_order_field = 'play_count'

    def get_track_count(self, obj): return obj.track_count
    get_track_count.admin_order_field = 'track_count'
    get_track_count.short_description = 'Tracks'

    def get_discogs_profile(self, obj):
        if obj.discogs:
            return obj.discogs.data.get('profile', None)
    get_discogs_profile.short_description='Profile'

    def get_discogs_members(self, obj):
        if obj.discogs:
            return ', '.join(obj.discogs.data.get('members', []))
    get_discogs_members.short_description='Members'

    def get_discogs_data_quality(self, obj):
        if obj.discogs:
            return '{0} (retrieved {1})'.format(
                obj.discogs.data.get('data_quality', 'unknown'),
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

    actions         = [set_shared_with_all_off, set_shared_with_all_on,
                       take_ownership,]

    list_display    = ['__unicode__', 'artist', 'album',
                       'get_pretty_track_number', 'get_pretty_length',
                       'get_assetfile_count', 'get_play_count',
                       'get_average_rating', 'owner', 'shared_with_all',]
    list_filter     = ['artist__name', 'album__name', 'name', 'created',
                       'owner', 'shared_with', 'shared_with_all',]
    search_fields   = ['name',]
    ordering        = ['artist',]
    readonly_fields = ['get_average_rating', 'get_streamable_assetfile',
                       'get_play_count', 'artwork_preview',
                       'get_extra_artist_list',]

    filter_horizontal = ['extra_artists',]

    fieldsets       = (
        ('Media Summary', {
            'classes': ('collapse', 'float-right',),
            'fields': ('artwork_preview', 'get_streamable_assetfile',),
        }),
        ('Track Data', {
            'classes': (),
            'fields': ( 'name', 
                        'artist',
                        'get_extra_artist_list',
                        ('album', 'year',),
                        ('disc_number', 'track_number',),
                        ('length', 'bpm',),
                        ('get_play_count', 'get_average_rating',),
                        'skip_random',
                      ),
        }),
        ('Ownership Information', {
            'classes': (),
            'fields': (
                        'owner',
                        'shared_with',
                        'shared_with_all',
                      ),
        }),
        ('Extra Artists', {
            'classes': ('collapse',),
            'fields': (
                'extra_artists',
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

    def get_extra_artist_list(self, obj):
        return u', '.join([
                    u'<a href="{0}">{1}</a>'.format(
                        reverse('admin:{app_label}_{module_name}_change'.format(**f._meta.__dict__), args=(f.pk,)),
                        f.name,
                    ) for f in obj.extra_artists.all()
        ])
    get_extra_artist_list.allow_tags = True
    get_extra_artist_list.short_description = 'Extra artists'

    def get_pretty_length(self, obj):
        if obj.length:
            return u"{0}:{1:02d}".format(obj.length / 60, obj.length % 60)
    get_pretty_length.short_description = 'length'
    get_pretty_length.admin_order_field = 'length'

    def get_play_count(self, obj):
        return obj.play_count
    get_play_count.short_description = 'Play count'
    get_play_count.admin_order_field = 'play_count'

    def get_assetfile_count(self, obj):
        return obj.assetfile_count
    get_assetfile_count.short_description = 'Files'
    get_assetfile_count.admin_order_field = 'assetfile_count'

    def get_average_rating(self, obj):
        return obj.average_rating
    get_average_rating.short_description = 'Average rating'
    get_average_rating.admin_order_field = 'average_rating'

    def save_model(self, request, obj, form, change):
        if not obj.owner:
            obj.owner = request.user
            obj.save()

admin.site.register(Track, TrackAdmin)

class PlayAdmin(admin.ModelAdmin):
    list_display = ['created', 'user', 'get_asset_name', 'played']
    fields = ['user', 'get_asset_name', 'get_play_prev', 'get_play_next', 'context', 'played', 'queue', 'created', 'in_groove']
    readonly_fields = ['user', 'get_asset_name', 'get_play_prev', 'get_play_next', 'context', 'played', 'queue', 'created', 'in_groove']

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

    search_fields = ['object_id', 'artist__name', 'album__name']

    readonly_fields = ['get_asset_link', 'get_pretty_data_cache', 'data_cache_dttm',]

    fields = ['object_type', 'object_id', 'get_asset_link', 'data_cache_dttm', 'get_pretty_data_cache']

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

    def get_pretty_data_cache(self, obj):
        data = simplejson.loads(obj.data_cache)
        return u'<div class="aligned">{0}</div>'.format(html_tree(data))
    get_pretty_data_cache.short_description='Data cache'
    get_pretty_data_cache.allow_tags=True


admin.site.register(Discogs, DiscogsAdmin)
