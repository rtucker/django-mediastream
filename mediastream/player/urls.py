from django.conf.urls.defaults import patterns, include, url

urlpatterns = patterns('player.views',
    url(r'^$', 'music_player', name='player_ui'),
    url(r'^event/$', 'player_event_handler', name='player_event'),
    url(r'^rating/$', 'collect_rating', name='player_rating'),
)
