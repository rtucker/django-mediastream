from django.conf.urls.defaults import patterns, include, url

from player.views import music_player

urlpatterns = patterns('',
    url(r'^$', music_player),
)
