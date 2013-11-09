from django.conf.urls import patterns, include, url

urlpatterns = patterns('mediastream.player.views',
    url(r'^$', 'music_player', name='player_ui'),
    url(r'^event/$', 'player_event_handler', name='player_event'),
    url(r'^rating/$', 'collect_rating', name='player_rating'),
    url(r'^discogsimage(?P<image>/.*)$', 'discogs_image_view', name='discogs_image'),
)
