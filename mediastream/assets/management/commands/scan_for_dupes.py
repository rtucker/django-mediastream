from django.core.management.base import BaseCommand, CommandError
from mediastream.assets.models import Asset
from optparse import make_option
from django.utils.encoding import smart_str

class Command(BaseCommand):
    help = 'Scans for possibly-duplicate asset files that may be merged'

    def handle(self, *args, **options):
        for asset in Asset.objects.filter(assetfile_count__gte=2).order_by('pk'):
            etag_history = {}
            for af in asset.assetfile_set.all():
                try:
                    etag = af.contents.file.key.etag
                except IOError as e:
                    print smart_str(e)
                    if smart_str(e).startswith('File does not exist'):
                        af.delete()
                    continue

                if etag in etag_history:
                    print "DUPE!", etag, smart_str(af), af.pk, " -> ", etag_history[etag].pk
                    if len(etag) is 34:
                        if smart_str(etag_history[etag].contents.file.key.name) != smart_str(af.contents.file.key.name):
                            print "    Deleting from server:", smart_str(af.contents.file.key.name)
                            af.contents.file.key.delete()
                        af.delete()
                    else:
                        print "Etag is weird, not deleting..."
                else:
                    etag_history[etag] = af
