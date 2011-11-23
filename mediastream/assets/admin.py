from django.contrib import admin
from mediastream.assets.models import Artist, Album, Track, AssetFile

admin.site.register(Artist)
admin.site.register(Album)

class AssetFileInline(admin.StackedInline):
    model = AssetFile

class TrackAdmin(admin.ModelAdmin):
    inlines = [
        AssetFileInline,
    ]
admin.site.register(Track, TrackAdmin)


