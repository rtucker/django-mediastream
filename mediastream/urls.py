from django.conf.urls.defaults import patterns, include, url
import mediastream.admin.filterspecs

# Uncomment the next two lines to enable the admin:
from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
    # Examples:
    # url(r'^$', 'mediastream.views.home', name='home'),
    # url(r'^mediastream/', include('mediastream.foo.urls')),

    url(r'^assets/', include('mediastream.assets.urls')),
    url(r'^player/', include('mediastream.player.urls')),
    (r'^accounts/login/$', 'django.contrib.auth.views.login', {'template_name': 'login.html'}),

    # Uncomment the admin/doc line below to enable admin documentation:
    url(r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    url(r'^admin/', include(admin.site.urls)),
)
