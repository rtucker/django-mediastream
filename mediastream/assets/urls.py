from django.conf.urls.defaults import patterns, include, url
from django.views.generic import DetailView, ListView
from assets.models import Track

urlpatterns = patterns('',
    (r'^upload/$', 'mediastream.assets.views.upload_file', {}, 'asset-upload'),
    url(r'^tracks/$',
        ListView.as_view(
            model=Track,
            template_name="assets/track_list.html")),
    url(r'^tracks/(?P<pk>\d+)/$',
        DetailView.as_view(
            model=Track,
            template_name="assets/track_play.html")),
)
