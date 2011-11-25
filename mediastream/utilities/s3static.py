from storages.backends.s3boto import *

#STATIC_ACCESS_KEY_NAME     = getattr(settings, 'AWS_STATIC_ACCESS_KEY_ID', ACCESS_KEY_NAME)
#STATIC_SECRET_KEY_NAME     = getattr(settings, 'AWS_STATIC_SECRET_ACCESS_KEY', SECRET_KEY_NAME)
STATIC_HEADERS             = getattr(settings, 'AWS_STATIC_HEADERS', HEADERS)
STATIC_STORAGE_BUCKET_NAME = getattr(settings, 'AWS_STATIC_STORAGE_BUCKET_NAME', STORAGE_BUCKET_NAME)
#STATIC_AUTO_CREATE_BUCKET  = getattr(settings, 'AWS_STATIC_AUTO_CREATE_BUCKET', AUTO_CREATE_BUCKET)
STATIC_DEFAULT_ACL         = getattr(settings, 'AWS_STATIC_DEFAULT_ACL', DEFAULT_ACL)
STATIC_BUCKET_ACL          = getattr(settings, 'AWS_STATIC_BUCKET_ACL', STATIC_DEFAULT_ACL)
STATIC_QUERYSTRING_AUTH    = getattr(settings, 'AWS_STATIC_QUERYSTRING_AUTH', QUERYSTRING_AUTH)
STATIC_QUERYSTRING_EXPIRE  = getattr(settings, 'AWS_STATIC_QUERYSTRING_EXPIRE', QUERYSTRING_EXPIRE)
STATIC_REDUCED_REDUNDANCY  = getattr(settings, 'AWS_STATIC_REDUCED_REDUNDANCY', REDUCED_REDUNDANCY)
STATIC_LOCATION            = getattr(settings, 'AWS_STATIC_LOCATION', LOCATION)
STATIC_CUSTOM_DOMAIN       = getattr(settings, 'AWS_STATIC_S3_CUSTOM_DOMAIN', CUSTOM_DOMAIN)
STATIC_CALLING_FORMAT      = getattr(settings, 'AWS_STATIC_S3_CALLING_FORMAT', CALLING_FORMAT)
STATIC_SECURE_URLS         = getattr(settings, 'AWS_STATIC_S3_SECURE_URLS', SECURE_URLS)
STATIC_FILE_NAME_CHARSET   = getattr(settings, 'AWS_STATIC_S3_FILE_NAME_CHARSET', FILE_NAME_CHARSET)
#STATIC_FILE_OVERWRITE      = getattr(settings, 'AWS_STATIC_S3_FILE_OVERWRITE', FILE_OVERWRITE)
STATIC_IS_GZIPPED          = getattr(settings, 'AWS_STATIC_IS_GZIPPED', IS_GZIPPED)
STATIC_PRELOAD_METADATA    = getattr(settings, 'AWS_STATIC_PRELOAD_METADATA', PRELOAD_METADATA)
STATIC_GZIP_CONTENT_TYPES  = getattr(settings, 'GZIP_CONTENT_TYPES', GZIP_CONTENT_TYPES)

if STATIC_IS_GZIPPED:
    from gzip import GzipFile

class S3StaticStorage(S3BotoStorage):
    "Subclasses S3BotoStorage to use its own config."
    def __init__(self,
                 bucket=STATIC_STORAGE_BUCKET_NAME,
                 access_key=None,
                 secret_key=None,
                 bucket_acl=STATIC_BUCKET_ACL,
                 acl=STATIC_DEFAULT_ACL,
                 headers=STATIC_HEADERS,
                 gzip=STATIC_IS_GZIPPED,
                 gzip_content_types=STATIC_GZIP_CONTENT_TYPES,
                 querystring_auth=STATIC_QUERYSTRING_AUTH,
                 querystring_expire=STATIC_QUERYSTRING_EXPIRE,
                 reduced_redundancy=STATIC_REDUCED_REDUNDANCY,
                 custom_domain=STATIC_CUSTOM_DOMAIN,
                 secure_urls=STATIC_SECURE_URLS,
                 location=STATIC_LOCATION,
                 file_name_charset=STATIC_FILE_NAME_CHARSET,
                 preload_metadata=STATIC_PRELOAD_METADATA,
                 calling_format=STATIC_CALLING_FORMAT):

        return super(S3StaticStorage, self).__init__(bucket, access_key,
            secret_key, bucket_acl, acl, headers, gzip, gzip_content_types,
            querystring_auth, querystring_expire, reduced_redundancy,
            custom_domain, secure_urls, location, file_name_charset,
            preload_metadata, calling_format)

    def _compress_content(self, content):
        """Gzip a given string."""
        zbuf = StringIO()
        zfile = GzipFile(mode='wb', compresslevel=6, fileobj=zbuf)
        zfile.write(content.read())
        zfile.close()
        content.file = zbuf
        return content
