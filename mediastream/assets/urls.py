from django.conf.urls.defaults import patterns, include, url
from django.contrib.auth.decorators import login_required
from django.views.generic import DetailView, ListView, RedirectView
from assets.models import Album, Artist, Track
from assets.views import TrackListView

urlpatterns = patterns('',
    (r'^upload/$', 'mediastream.assets.views.upload_file', {}, 'asset-upload'),
    (r'^merge/(?P<ct>\d+)/(?P<ids>[\d,]+)/$', 'mediastream.assets.views.merge_assets_view', {}, 'asset-merge'),
    url(r'^album/$',
        ListView.as_view(
            model=Album,
            template_name="assets/album_list.html")),
    url(r'^album/(?P<album_pk>\d+)/$',
        TrackListView.as_view(),
        name='asset-album'),
    url(r'^album/(?P<pk>\d+)/play/$',
        login_required(DetailView.as_view(
            model=Album,
            template_name="assets/playlist.html")),
        name='play-album'),
    url(r'^artist/$',
        ListView.as_view(
            model=Artist,
            template_name="assets/artist_list.html"),
        name='artist-list'),
    url(r'^artist/(?P<artist_pk>\d+)/$',
        TrackListView.as_view(),
        name='asset-artist'),
    url(r'^track/$',
        ListView.as_view(
            model=Track,
            template_name="assets/track_list.html")),
    url(r'^track/(?P<pk>\d+)/$',
        login_required(DetailView.as_view(
            model=Track,
            template_name="assets/track_play.html")),
        name='play-track'),
    url(r'^tracks/$',
        RedirectView.as_view(
            url='/assets/track/')),
    url(r'^tracks/(?P<pk>\d+)/$',
        RedirectView.as_view(
            url='/assets/track/%(pk)s/')),
)
