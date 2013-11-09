from django.conf import settings
from storages.backends.s3boto import *

STATIC_SETTINGS = {
    "headers":              getattr(settings, 'AWS_STATIC_HEADERS', None),
    "bucket_name":          getattr(settings, 'AWS_STATIC_STORAGE_BUCKET_NAME', None),
    "default_acl":          getattr(settings, 'AWS_STATIC_DEFAULT_ACL', None),
    "bucket_acl":           getattr(settings, 'AWS_STATIC_BUCKET_ACL', None),
    "querystring_auth":     getattr(settings, 'AWS_STATIC_QUERYSTRING_AUTH', None),
    "querystring_expire":   getattr(settings, 'AWS_STATIC_QUERYSTRING_EXPIRE', None),
    "reduced_redundancy":   getattr(settings, 'AWS_STATIC_REDUCED_REDUNDANCY', None),
    "location":             getattr(settings, 'AWS_STATIC_LOCATION', None),
    "custom_domain":        getattr(settings, 'AWS_STATIC_S3_CUSTOM_DOMAIN', None),
    "calling_format":       getattr(settings, 'AWS_STATIC_S3_CALLING_FORMAT', None),
    "secure_urls":          getattr(settings, 'AWS_STATIC_S3_SECURE_URLS', None),
    "file_name_charset":    getattr(settings, 'AWS_STATIC_S3_FILE_NAME_CHARSET', None),
    "file_overwrite":       getattr(settings, 'AWS_STATIC_S3_FILE_OVERWRITE', None),
    "gzip":                 getattr(settings, 'AWS_STATIC_IS_GZIPPED', None),
    "preload_metadata":     getattr(settings, 'AWS_STATIC_PRELOAD_METADATA', None),
    "gzip_content_types":   getattr(settings, 'GZIP_CONTENT_TYPES', None),
}

class S3StaticStorage(S3BotoStorage):
    "Subclasses S3BotoStorage to use its own config."
    def __init__(self, acl=None, bucket=None, **settings):
        for name, value in STATIC_SETTINGS.items():
            if hasattr(self, name) and value is not None:
                setattr(self, name, value)

        return super(S3StaticStorage, self).__init__(acl, bucket, **settings)
