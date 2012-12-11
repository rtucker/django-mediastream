from django.core.management.base import BaseCommand, CommandError
from mediastream.assets.models import Album
from optparse import make_option
from utilities.mediainspector import mt as mimetypes
from django.utils.encoding import smart_str

class Command(BaseCommand):
    help = 'Deduplicates the tracks on a given album'

    def handle(self, *args, **options):
        for album_pk in args:
            a = Album.objects.get(pk=album_pk)

            for discnum, tracknum in a.track_set.values_list('disc_number', 'track_number'):
                trx = a.track_set.filter(disc_number=discnum, track_number=tracknum).order_by('pk')
                if trx.count() > 1:
                    print("Merging: %d <- %s" % (trx[0].pk,
                        ', '.join([str(t.pk) for t in trx])))
                    target_track = trx[0]
                    for t in trx:
                        for otherset in [t.assetfile_set, t.play_set, t.rating_set]:
                            for other in otherset.all():
                                other.asset = target_track
                                other.save()
                        for artist in t.extra_artists.all():
                            trx.extra_artists.add(artist)
