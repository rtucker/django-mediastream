from django.core.management.base import BaseCommand, CommandError
from mediastream.assets.models import AssetFile
from optparse import make_option
from utilities.mediainspector import mt as mimetypes
from django.utils.encoding import smart_str

class Command(BaseCommand):
    help = 'If the S3 mimetype is wrong, fix it'

    def handle(self, *args, **options):
        for af in AssetFile.objects.all().order_by('pk'):
            local_mimetype = str(af.mimetype)
            if local_mimetype is None or local_mimetype == '':
                local_mimetype = mimetypes.guess_type(af.name)[0]
                if local_mimetype is None:
                    print "NO MIMETYPE GUESSED:", smart_str(af)
                    continue

                print "Local updated:", smart_str(af), local_mimetype
                af.mimetype = local_mimetype
                af.save()

            try:
                key = af.contents.file.key
            except IOError as e:
                if smart_str(e).startswith('File does not exist'):
                    print "FILE NOT FOUND:", smart_str(af)
                    af.delete()
                    continue
                else:
                    raise

            s3_mimetype = str(key.content_type)
            if local_mimetype != s3_mimetype:
                print "Remote updated:", smart_str(af), s3_mimetype, local_mimetype
                name = key.name
                bucket = key.bucket
                metadata = key.metadata
                metadata.update({'Content-Type': local_mimetype})
                key.copy(bucket, key, metadata=metadata, preserve_acl=True)
