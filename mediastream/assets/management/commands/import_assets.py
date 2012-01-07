from django.core.management.base import BaseCommand, CommandError
from mediastream.assets.models import Track

class Command(BaseCommand):
    args = '<filename filename ...>'
    help = 'Imports the provided assets.'

    def handle(self, *args, **options):
        for newfile in args:
            newtracks = Track.objects.create_from_file(newfile)
            for newtrack in newtracks:
                try:
                    self.stdout.write(u"Successfully imported from %s: pk %i, %s / %s / %s\n" % (newfile, newtrack.pk, newtrack.artist.name, newtrack.album.name, newtrack.name))
                except UnicodeError:
                    self.stdout.write(u"Successfully imported a track pk %i\n" % (newtrack.pk))
