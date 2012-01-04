# Django settings for mediastream project.

DEBUG = False
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    # ('Your Name', 'your_email@example.com'),
)

MANAGERS = ADMINS

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3', # Add 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3' or 'oracle'.
        'NAME': '/home/rtucker/dev/django-mediastream/db.sqlite3',                      # Or path to database file if using sqlite3.
        'USER': '',                      # Not used with sqlite3.
        'PASSWORD': '',                  # Not used with sqlite3.
        'HOST': '',                      # Set to empty string for localhost. Not used with sqlite3.
        'PORT': '',                      # Set to empty string for default. Not used with sqlite3.
    }
}

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# On Unix systems, a value of None will cause Django to use the same
# timezone as the operating system.
# If running in a Windows environment this must be set to the same as your
# system time zone.
TIME_ZONE = 'America/New_York'

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'en-us'

SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

# If you set this to False, Django will not format dates, numbers and
# calendars according to the current locale
USE_L10N = True

# Absolute filesystem path to the directory that will hold user-uploaded files.
# Example: "/home/media/media.lawrence.com/media/"
MEDIA_ROOT = ''

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash.
# Examples: "http://media.lawrence.com/media/", "http://example.com/media/"
MEDIA_URL = ''

# Absolute path to the directory static files should be collected to.
# Don't put anything in this directory yourself; store your static files
# in apps' "static/" subdirectories and in STATICFILES_DIRS.
# Example: "/home/media/media.lawrence.com/static/"
STATIC_ROOT = ''

# URL prefix for static files.
# Example: "http://media.lawrence.com/static/"
STATIC_URL = '/static/'     # note: gets reset by local_settings

# URL prefix for admin static files -- CSS, JavaScript and images.
# Make sure to use a trailing slash.
# Examples: "http://foo.com/static/admin/", "/static/admin/".
ADMIN_MEDIA_PREFIX = '/static/admin/'   # note: gets reset by local_settings

# Additional locations of static files
STATICFILES_DIRS = (
    # Put strings here, like "/home/html/static" or "C:/www/django/static".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
)

# List of finder classes that know how to find static files in
# various locations.
STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
#    'django.contrib.staticfiles.finders.DefaultStorageFinder',
)

# Make this unique, and don't share it with anybody.
SECRET_KEY = 'g^t&cld^&y1ljs-*4gv1k@^u))^_j)))2061mg-m$pw5c_%y!$'

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
#     'django.template.loaders.eggs.Loader',
)

MIDDLEWARE_CLASSES = (
    'django.middleware.cache.UpdateCacheMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    #'gitrevision.middleware.GitRevision',
    'django.contrib.flatpages.middleware.FlatpageFallbackMiddleware',
    'django.middleware.cache.FetchFromCacheMiddleware',
    'debug_toolbar.middleware.DebugToolbarMiddleware',
)

ROOT_URLCONF = 'mediastream.urls'

TEMPLATE_DIRS = (
    # Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
)

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    'django.contrib.flatpages',
    'django.contrib.staticfiles',
    'django.contrib.admin',
    'django.contrib.admindocs',
    # third-party stuff
    'debug_toolbar',
    'gitrevision',
    'gunicorn',
    'south',
    # our applications
    'mediastream.assets',
    'mediastream.player',
    'mediastream.queuer',
    'mediastream.tags',
    'mediastream.utilities',
)

# A sample logging configuration. The only tangible logging
# performed by this configuration is to send an email to
# the site admins on every HTTP 500 error.
# See http://docs.djangoproject.com/en/dev/topics/logging for
# more details on how to customize your logging configuration.
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'mail_admins': {
            'level': 'ERROR',
            'class': 'django.utils.log.AdminEmailHandler'
        }
    },
    'loggers': {
        'django.request': {
            'handlers': ['mail_admins'],
            'level': 'ERROR',
            'propagate': True,
        },
    }
}

# Debuggery
INTERNAL_IPS = ('127.0.0.1',)

# File storage
# See AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_STORAGE_BUCKET_NAME
# in local_settings.py
DEFAULT_FILE_STORAGE = 'storages.backends.s3boto.S3BotoStorage'
ASSETS_UPLOAD_TO = '/'
AWS_DEFAULT_ACL = 'private'
AWS_AUTO_CREATE_BUCKET=True
AWS_REDUCED_REDUNDANCY=False
AWS_HEADERS = {
    'Cache-Control': 'private, max-age=604800',
}

# Static file storage
# See AWS_STATIC_STORAGE_BUCKET_NAME in local_settings.py
STATICFILES_STORAGE = 'mediastream.utilities.s3static.S3StaticStorage'
AWS_STATIC_DEFAULT_ACL='public-read'
AWS_STATIC_REDUCED_REDUNDANCY=True
AWS_STATIC_IS_GZIPPED=True
AWS_STATIC_HEADERS = {
    'Cache-Control': 'public, max-age=604800',
} 

# User agent
from django import VERSION as djversion
from git import Repo, InvalidGitRepositoryError
from platform import python_version
try:
    gitrev = Repo().head.commit.hexsha
except InvalidGitRepositoryError:
    gitrev = 'unknown'
HTTP_USER_AGENT = 'django-mediastream/{0} Django/{1} Python/{2} +{3}'.format(
    gitrev[0:10],
    '.'.join([str(f) for f in djversion]),
    python_version(),
    'https://github.com/rtucker/django-mediastream',
)

# Local settings
try:
    from local_settings import *
    STATIC_URL = '//{0}.s3.amazonaws.com/'.format(AWS_STATIC_STORAGE_BUCKET_NAME)
    ADMIN_MEDIA_PREFIX = STATIC_URL + 'admin/'
except ImportError, NameError:
    pass
