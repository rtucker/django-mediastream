from django.conf import settings
from django.contrib.auth.models import User
from django.core.cache import cache
from django.core.exceptions import ObjectDoesNotExist
from django.core.files import File
from django.core.files.base import ContentFile
from django.core.urlresolvers import reverse
from django.db import models
from django.db.models import Avg, Max, Count, Q
from django.utils import simplejson

from mediastream.assets import MIMETYPE_CHOICES, _get_upload_path
from mediastream.assets import mt as mimetypes
from mediastream.utilities.mediainspector import Inspector

from datetime import datetime, timedelta
import discogs_client as discogs
from gitrevision.utils import gitrevision
import os
import random
from tempfile import NamedTemporaryFile
from urlparse import urlparse
import zipfile

# Approximate window for repeating Tracks
RECENT_DAYS = 14

discogs.user_agent = settings.HTTP_USER_AGENT

def playtime(rating=None):
    minimum = RECENT_DAYS
    if rating:
        minimum *= rating**-1
    return timedelta(days=minimum)

class DiscogsManager(models.Manager):
    def get_for_object(self, obj):
        "Attempts to find a Discogs record for an album or artist."
        if type(obj) is Artist:
            obj_type    = Discogs.ARTIST
            obj_id      = obj.name
            obj_class   = discogs.Artist
        elif type(obj) is Album:
            obj_type    = Discogs.RELEASE
            obj_id      = None
            obj_class   = discogs.Release

            try:
                results = sorted(discogs.Search(obj.name).results())
            except discogs.DiscogsAPIError, e:
                results = []
            for result in results:
                if type(result) not in [discogs.Release, discogs.MasterRelease]:
                    continue

                # Check track list concurrence
                tracks_matched = 0
                my_tracks = obj.track_set.values_list('name', flat=True)
                for discogs_track in result.tracklist:
                    if discogs_track['title'] in my_tracks:
                        tracks_matched += 1
                if tracks_matched > (len(my_tracks)/2):
                    # We probably have a winner here
                    obj_id = result._id
                    if type(result) is discogs.MasterRelease:
                        obj_type = Discogs.MASTERRELEASE
                        obj_class = discogs.MasterRelease
                    break

        # Bail out on errors
        if not obj_id:
            raise Discogs.DoesNotExist("Could not find a Discogs object for {0}".format(obj.name))

        # Do we already have one of these?
        try:
            return self.get(object_type=obj_type, object_id=obj_id)
        except Discogs.DoesNotExist:
            pass
        
        # Try to pull some data from it
        try:
            data = obj_class(obj_id).data
        except discogs.DiscogsAPIError, e:
            raise Discogs.DoesNotExist(u"Could not retrieve Discogs object for {0} using {1}({2}): {3}".format(obj.name, repr(obj_class), repr(obj_id), e))

        # Save stuff!
        return self.create(object_type=obj_type,
                           object_id=obj_id,
                           data_cache=simplejson.dumps(data),
                           data_cache_dttm=datetime.now())

class Discogs(models.Model):
    "Holds a relationship with Discogs."
    ARTIST = 1
    RELEASE = 2
    MASTERRELEASE = 3
    LABEL = 4
    SEARCH = 5
    OBJECT_TYPE_CHOICES = (
        (ARTIST, 'Artist'),
        (RELEASE, 'Release'),
        (MASTERRELEASE, 'MasterRelease'),
        (LABEL, 'Label'),
        (SEARCH, 'Search'),
    )

    object_type = models.PositiveSmallIntegerField(
        choices=OBJECT_TYPE_CHOICES,
    )
    object_id = models.CharField(max_length=255)
    data_cache = models.TextField(blank=True, null=True)
    data_cache_dttm = models.DateTimeField(blank=True, null=True, verbose_name='Data cache timestamp')

    objects = DiscogsManager()

    class Meta:
        ordering = ('object_type', 'object_id',)
        unique_together = (('object_type', 'object_id',),)
        verbose_name = 'Discogs mapping'

    def __unicode__(self):
        return u"{0} {1}".format(
            self.get_object_type_display(),
            self.object_id,
        )

    @property
    def discogs_object(self):
        return getattr(discogs, self.get_object_type_display())(self.object_id)

    @property
    def data(self):
        if self.object_type == self.SEARCH:
            return None
        if (not self.data_cache_dttm) or (self.data_cache_dttm < datetime.now() - timedelta(days=30)):
            # nuke existing cache
            self.data_cache = None
            self.data_cache_dttm = None
            self.save()
            # read in new stuff from discogs
            self.data_cache = simplejson.dumps(self.discogs_object.data)
            self.data_cache_dttm = datetime.now()
            self.save()
        return simplejson.loads(self.data_cache)

    def get_asset(self):
        qs = list(self.artist_set.all()) + list(self.album_set.all())
        return qs[0] if qs else None
    get_asset.short_description = 'Asset'

class Thing(models.Model):
    "Abstract base class for things with names."
    name        = models.CharField(max_length=255)
    created     = models.DateTimeField(auto_now_add=True)
    modified    = models.DateTimeField(auto_now=True)

    name.alphabetic_filter = True

    class Meta:
        abstract = True
        ordering = ['name']

    def __unicode__(self):
        return self.name

class AssetManager(models.Manager):
    def get_query_set(self):
        qs = super(AssetManager, self).get_query_set()
        return qs.annotate(
                    assetfile_count=Count('assetfile', distinct=True),
                    play_count=Count('play', distinct=True),
                    average_rating=Avg('rating__rating'),
                    last_play=Max('play__modified'),)

class Asset(Thing):
    "Inherited class that owns the actual files."
    owner = models.ForeignKey(User, blank=True, null=True,
                              on_delete=models.SET_NULL,
                              help_text="Owner of this asset",
                              related_name='owned_assets',)
    shared_with = models.ManyToManyField(User, blank=True, null=True,
                              help_text="Users who may access this asset",
                              related_name='shared_assets',)
    shared_with_all = models.BooleanField(default=False,
                              help_text="May any user access this asset?")

    class Meta:
        permissions = (
                       ("can_download_asset", "Can download asset"),
                       ("can_stream_asset", "Can stream asset"),
                      )

    objects = AssetManager()

class AssetFile(Thing):
    "Describes an underlying file for an Asset."
    asset       = models.ForeignKey(Asset)
    contents    = models.FileField(upload_to=_get_upload_path, max_length=255)
    mimetype    = models.CharField(max_length=255, choices=MIMETYPE_CHOICES,
                                   blank=True, verbose_name="MIME type")
    length      = models.FloatField(blank=True, null=True,)

    class Meta:
        order_with_respect_to = 'asset'

    @property
    def filename(self):
        if hasattr(self.asset, 'track') and self.mimetype.startswith('audio'):
            if self.mimetype == 'audio/mpeg': exten = '.mp3'
            elif self.mimetype == 'audio/mp4': exten = '.m4a'
            elif self.mimetype == 'audio/x-flac': exten = '.flac'
            elif self.mimetype == 'audio/ogg': exten = '.ogg'
            else: exten = mimetypes.guess_extension(self.mimetype, False)
            return u"{0}{1}".format(self.asset.track.name, exten)
        else:
            return u"{0}{1}".format(self.name,
                                  mimetypes.guess_extension(
                                    self.mimetype, False))

    def get_descriptor_admin_links(self):
        out = u'<ul>'
        for descriptor in self.assetdescriptor_set.all():
            out += (u'<li><a href="{url}">{text}</a>: '
                    u'{bit_rate} b/s, {sample_rate} Hz'
                   ).format(
                        url=reverse('admin:assets_assetdescriptor_change',
                            args=(descriptor.id,)),
                        text=unicode(descriptor), **descriptor.__dict__
                        )
            if descriptor.is_vbr: out += (u', VBR')
            if descriptor.lossy is False: out += (u', lossless')
            out += u'</li>'
        out += u'</ul>'
        if self.pk: out += u'<a href="{url}">Add new</a> (advanced)'.format(
                        url=reverse('admin:assets_assetdescriptor_add'),
                    )
        return out
    get_descriptor_admin_links.allow_tags = True
    get_descriptor_admin_links.short_description = 'Stream descriptors'

class AssetDescriptor(models.Model):
    "Describes a bitstream in a possibly-multiplexed file."
    assetfile   = models.ForeignKey(AssetFile)
    bitstream   = models.IntegerField(default=0)
    mimetype    = models.CharField(max_length=255, choices=MIMETYPE_CHOICES,
                                   default='application/octet-stream',
                                   verbose_name="MIME type")

    bit_rate    = models.FloatField(blank=True, null=True)
    is_vbr      = models.NullBooleanField(blank=True, null=True,
                                          verbose_name="Variable bit rate")
    lossy       = models.NullBooleanField(blank=True, null=True)
    sample_rate = models.FloatField(blank=True, null=True)

    class Meta:
        ordering        = ['bitstream']
        unique_together = ('assetfile', 'bitstream')

    def __unicode__(self):
        return u"Stream {bitstream} ({mimetype})".format(**self.__dict__)

# Music-specific concepts.
class ArtistManager(models.Manager):
    def get_query_set(self):
        qs = super(ArtistManager, self).get_query_set()
        return qs.annotate(
                    album_count=Count('track__album', distinct=True),
                    track_count=Count('track', distinct=True),
                    play_count=Count('track__play', distinct=True),)

class Artist(Thing):
    "A performing artist."
    is_prince   = models.BooleanField(default=False,
                    help_text=("If true, Unicode representation will be "
                               "O(+> between 1993 and 2000."),
                    verbose_name="Occasionally known as Prince")
    discogs     = models.ForeignKey(Discogs, null=True, blank=True, on_delete=models.SET_NULL)

    objects     = ArtistManager()

    def __unicode__(self):
        return u"O(+>" if self.is_prince else self.name

    def get_track_admin_links(self):
        def __album_print(album, tracks=None):
            out = u'<h4><a href="{url}">{album}</a>{wholealbum}</h4>'.format(
                    url=reverse('admin:assets_album_change', args=(album.id,)),
                    album=album.name,
                    wholealbum='' if tracks else ' (entire album)',
                )
            if tracks:
                for track in tracks:
                    out += u'<li>{0}</li>'.format(__track_print(track))
            return out

        def __track_print(track, album=False):
            return (
                u'<a href="{url}">Track {tn}</a>: {artist} / {name}'.format(
                    url=reverse('admin:assets_track_change',
                        args=(track.id,)),
                    tn=track.get_pretty_track_number(),
                    artist=track.artist.name,
                    name=track.name,
                ))

        out = [u'<ul>']

        direct = self.track_set.values('album').order_by('album').distinct()
        if len(direct) > 0:
            out.append(u'<h3>As primary artist</h3>')
            for album in direct:
                album = Album.objects.get(pk=album['album'])
                out.append(__album_print(album, tracks=self.track_set.filter(album=album).order_by('disc_number', 'track_number')))

        extra_albums = self.album_credits.values('pk').order_by('name').distinct()
        extra_tracks = self.track_credits.values('pk', 'album__name', 'album__pk').order_by('album__name', 'track_number').distinct()
        seen_albums = []

        if len(extra_tracks) > 0 or len(extra_albums) > 0:
            out.append(u'<h3>As credited artist</h3>')

            for extra_track in extra_tracks:
                if extra_track['album__pk'] in seen_albums:
                    continue
                album = Album.objects.get(pk=extra_track['album__pk'])
                seen_albums.append(album.pk)
                out.append(__album_print(album, tracks=self.track_credits.filter(album=album).order_by('disc_number', 'track_number')))

            for extra_album in extra_albums:
                if extra_album['pk'] in seen_albums:
                    continue
                album = Album.objects.get(pk=extra_album['pk'])
                out.append(__album_print(album, tracks=self.track_credits.filter(album=album).order_by('disc_number', 'track_number')))

        out.append(u'</ul>')

        return ''.join(out)
    get_track_admin_links.allow_tags = True
    get_track_admin_links.short_description = 'Tracks'

class AlbumManager(models.Manager):
    def get_query_set(self):
        qs = super(AlbumManager, self).get_query_set()
        return qs.annotate(
                    artist_count=Count('track__artist', distinct=True),
                    track_count=Count('track', distinct=True),
                    play_count=Count('track__play', distinct=True),)

class Album(Thing):
    """
    One album of tracks.

    This corresponds approximately to the unit of sale for a group of
    tracks.  It may consist of multiple discs, or none at all.
    """

    is_compilation  = models.BooleanField(default=False,
                        help_text="Contains the work of distinct artists.")
    discs           = models.IntegerField(default=1,
                        help_text="Quantity of discs in the set.")
    discogs         = models.ForeignKey(Discogs, null=True, blank=True, on_delete=models.SET_NULL)
    extra_artists   = models.ManyToManyField(Artist, null=True, blank=True,
                        related_name="album_credits",
                        help_text="Additional credited artists for this album, such as remixer, producer, etc.")

    objects = AlbumManager()

    def get_track_admin_links(self):
        out = u'<ul>'
        for track in self.track_set.all().order_by('disc_number', 'track_number'):
            out += (u'<li><a href="{url}">Track {tn}</a>: '
                    u'{artist} / {name}</li>'
                   ).format(
                        url=reverse('admin:assets_track_change',
                            args=(track.id,)),
                        tn=track.get_pretty_track_number(),
                        artist=track.artist.name,
                        name=track.name,
                    )
        if self.pk: out += u'<li><a href="{url}">Add new...</a></li>'.format(
                        url=reverse('admin:assets_track_add'),
                    )
        out += u'</ul>'
        return out
    get_track_admin_links.allow_tags = True
    get_track_admin_links.short_description = 'Tracks'

class TrackManager(models.Manager):
    def get_query_set(self):
        qs = super(TrackManager, self).get_query_set()
        return qs.annotate(
                    assetfile_count=Count('assetfile', distinct=True),
                    play_count=Count('play', distinct=True),
                    average_rating=Avg('rating__rating'),
                    last_play=Max('play__modified'),)


    def create_from_file(self, stash):
        if not isinstance(stash, file):
            filename = stash
            stash = open(stash)
        else:
            filename = getattr(stash, 'name', 'input_file')

        inspfp = NamedTemporaryFile(suffix=os.path.splitext(filename)[1])
        inspfp.write(stash.read())
        stash.seek(0)
        inspfp.seek(0)
        inspobj = Inspector(fileobj=inspfp)

        files = []

        if inspobj.mimetype == 'application/zip':
            myzip = zipfile.ZipFile(stash)
            count = 0
            for member in myzip.namelist():
                # We could just use ZipFile.open, but we need to
                # be able to seek.
                if member.endswith('/'):
                    continue
                mytarget = NamedTemporaryFile()
                mytarget.write(myzip.read(member))
                mytarget.seek(0)
                myinspfp = NamedTemporaryFile()
                myinspfp.write(mytarget.read())
                myinspobj = Inspector(fileobj=myinspfp)
                mytarget.seek(0)
                files.append((mytarget, myinspobj))
                count += 1
        elif inspobj.mimetype.startswith('audio/'):
            stash.seek(0)
            files.append((stash, inspobj))
        else:
            raise Exception('Could not figure out what to do with {0} of type {1}.'.format(filename, inspobj.mimetype))

        results = []

        for f, i in files:
            mandatory = ['artist', 'album', 'name']
            proceed = True
            for attrib in mandatory:
                if not getattr(i, attrib, None):
                    proceed = False

            if not proceed:
                results.append(None)
                continue

            art, cre = Artist.objects.get_or_create(
                name__iexact=i.artist,
                defaults={
                    'name': i.artist,
                },
            )
            alb, cre = Album.objects.get_or_create(
                name__iexact=i.album,
                defaults={
                    'name': i.album,
                    'is_compilation': getattr(i, 'is_compilation', False),
                },
            )
            t, cre = self.get_or_create(
                name__iexact=i.name,
                album=alb,
                artist=art,
                defaults={
                    'name': i.name,
                    'track_number': getattr(i, 'track', None),
                    'disc_number': getattr(i, 'disc', None),
                    'length': getattr(i, 'length', None),
                },
            )
            af = AssetFile.objects.create(
                name=i.name,
                asset=t,
                contents=File(f),
                mimetype=i.mimetype,
            )

            t._inspect_files(qs=t.assetfile_set.filter(pk=af.pk))
            results.append(t)

        return results

    def _get_shuffle_sample(self, user):
        "Returns a sampling of a QuerySet."
        qssample = cache.get('get_shuffle__sample__%i' % user.pk)
        if not qssample:
            qs = self.get_query_set().filter(skip_random=False)
            qs = qs.filter(
                    Q(owner=user) | Q(shared_with=user) |
                    Q(shared_with_all=True))   # assets we may enjoy
            qs = qs.annotate(anno_rate=Avg('rating__rating'))
            qs = qs.annotate(anno_last=Max('play__modified'))
            qs = qs.filter(
                Q(anno_last=None) |
                Q(anno_rate=None,   anno_last__lt=datetime.now() - playtime(None)) |
                Q(anno_rate__lte=1, anno_last__lt=datetime.now() - playtime(1)) |
                Q(anno_rate__gt=1,  anno_last__lt=datetime.now() - playtime(2)) |
                Q(anno_rate__gt=2,  anno_last__lt=datetime.now() - playtime(3)) |
                Q(anno_rate__gt=3,  anno_last__lt=datetime.now() - playtime(4)) |
                Q(anno_rate__gt=4,  anno_last__lt=datetime.now() - playtime(5))
            )

            # Filter the sample somewhat to avoid over-representation
            seen_albums = {}
            seen_artists = {}
            qssample = []
            for t in qs.order_by('?').iterator():
                seen_albums[t.album_id] = seen_albums.get(t.album_id, 0) + 1
                seen_artists[t.artist_id] = seen_artists.get(t.artist_id, 0) + 1
                if seen_albums[t.album_id] < 5 and seen_artists[t.artist_id] < 5:
                    qssample.append(t)
                if len(qssample) > 199: break
            cache.set('get_shuffle__sample__%i' % user.pk, qssample, 3600)
        return qssample

    def get_shuffle(self, user, previous=None, debug=False):
        """Returns a shuffle-mode track, with some smarts.

        We set relative probabilities for the following possibilities:
            - Grooves: if they exist, go for them most of the time.
            - Ratings: highest-rated tracks first, much of the time
            - Unrated/unplayed tracks: sometimes, go completely random
        """
        randstats = {}
        if type(previous) is int:
            previous = self.get(pk=previous)

        # Interrogate previous track for good and bad grooves.
        if previous:
            randstats['previous'] = previous.pk
            grooves = cache.get('get_shuffle__grooves__%i__%i' % (user.pk, previous.pk))
            if not grooves:
                grooves = list(self.get_query_set().filter(
                    skip_random=False,
                    play__in_groove=True,
                    play__previous_play__asset=previous,
                    play__user=user,
                ))
                cache.set('get_shuffle__grooves__%i__%i' % (user.pk, previous.pk), grooves, 7200)
            antigrooves = cache.get('get_shuffle__antigrooves__%i__%i' % (user.pk, previous.pk))
            if not antigrooves:
                antigrooves = list(self.get_query_set().filter(
                    skip_random=False,
                    play__in_groove=False,
                    play__previous_play__asset=previous,
                    play__user=user,
                ))
                cache.set('get_shuffle__antigrooves__%i__%i' % (user.pk, previous.pk), antigrooves, 7200)
        else:
            antigrooves = []
            grooves = []

        qssample = self._get_shuffle_sample(user)
        qssample.sort(key=lambda k: k.anno_rate)

        # Mix this bad boy up.
        val = random.randint(0, 99)
        if val < 25:
            # 25% of the time, be completely random.
            random.shuffle(qssample)
            randstats['mode'] = 'shuffle'
        elif val < 80:
            # 55% of the time, if there's grooves, put 'em first
            qssample.extend(grooves)
            randstats['mode'] = 'grooves'
        else:
            randstats['mode'] = 'rating'

        result = None
        iterations = 0
        while not result:
            # Randomly pick a sequence.
            iterations += 1
            randstats = {
                'user_pk': user.pk,
                'iterations': iterations,
                'antigrooves_len': len(antigrooves),
                'grooves_len': len(grooves),
                'qssample_len': len(qssample),
            }

            if qssample:
                result = qssample.pop()
                if (cache.get('get_shuffle__offered__%i__%i' % (user.pk, result.pk)) or
                    result.recently_played or
                    result in antigrooves
                   ): result=None
            else:
                cache.delete('get_shuffle__sample__%i' % user.pk)
                qssample = self._get_shuffle_sample(user)
                randstats['mode'] = 'failsafe'

        cache.set('get_shuffle__offered__%i__%i' % (user.pk, result.pk), True, 7200)
        result._randstats = randstats
        return result

class Track(Asset):
    """
    One track from an album.

    When multiple recordings of a song exist, each one should be its own
    track.  However, a recording may be stored as multiple files, perhaps
    MP3 and FLAC, or multiple bitrates, or, ...
    """
    artist      = models.ForeignKey("Artist")
    album       = models.ForeignKey("Album")
    year        = models.IntegerField(blank=True, null=True)

    disc_number = models.IntegerField(blank=True, null=True)
    track_number = models.IntegerField(blank=True, null=True)

    length      = models.IntegerField(blank=True, null=True,
                    verbose_name="Duration (seconds)")
    bpm         = models.FloatField(blank=True, null=True,
                    verbose_name="Beats per minute")
    skip_random = models.BooleanField(default=False,
                    help_text="Don't play during random mode")

    extra_artists   = models.ManyToManyField(Artist, null=True, blank=True,
                        related_name="track_credits",
                        help_text="Additional credited artists for this track, such as producer, special guest, etc.")


    class Meta:
        order_with_respect_to   = 'album'
        ordering                = ['disc_number', 'track_number']

    objects = TrackManager()

    def get_display_name(self):
        return u'{0} - {1}'.format(self.artist, self.name)

    def get_pretty_track_number(self):
        # TODO: ID3 spec specifies X/Y = Track X of Y
        # This is probably quite confusing.
        dn = self.disc_number if (self.disc_number and
                                self.disc_number > 0) else None
        tn = self.track_number if (self.track_number and
                                self.track_number > 0) else None
        if dn and tn: return u"{0}/{1}".format(dn, tn)
        elif tn:      return u"{0}".format(tn)
        else:         return u""
    get_pretty_track_number.short_description = 'track number'
    get_pretty_track_number.admin_order_field = 'track_number'

    def get_artwork_url(self, **kwargs):
        qs = self.assetfile_set.filter(mimetype__startswith='image/').order_by('?')
        if qs.exists():
            return qs[0].contents.url
        pickings = []
        for discogs in [self.album.discogs, self.artist.discogs]:
            if discogs and 'images' in discogs.data:
                for img in discogs.data['images']:
                    localpath = reverse('discogs_image',
                        args=(urlparse(img['resource_url']).path,),)
                    if img['type'] == 'primary':
                        return localpath
                    else:
                        pickings.append(localpath)
        if len(pickings) > 0:
            return random.choice(pickings)
        return None

    def get_streamable_assetfile(self, **kwargs):
        for candidate in self.assetfile_set.all():
            fn = candidate.contents.name.lower()
            if os.path.splitext(fn)[1] in ['.mp3', '.m4a', '.spx', '.ogg']:
                return candidate
        raise AssetFile.DoesNotExist("No suitable content found")
    get_streamable_assetfile.short_description = "Best asset for streaming"

    def get_streaming_url(self, **kwargs):
        "Returns the best URL for this object."
        return self.get_streamable_assetfile().contents.url

    def get_streaming_exten(self, **kwargs):
        ext = self.get_streamable_assetfile().contents.name.split('.')[-1:][0]
        if ext in ['spx', 'ogg']: ext = 'oga'
        return ext

    def get_recently_played(self):
        "Based on Rating and Play, returns True if track played recently"
        if not self.last_play:
            return False
        return self.last_play > (datetime.now() + playtime(self.average_rating))
    recently_played = property(get_recently_played)

    def _inspect_files(self, qs=None, update_artist=False, update_album=False):
        if not qs:
            qs = self.assetfile_set.all()
        for assetfile in qs:
            inspobj = Inspector(assetfile.contents, assetfile.mimetype)

            if not inspobj.mimetype.startswith('audio/'):
                continue

            if (not self.artist or update_artist) and hasattr(inspobj, 'artist') and inspobj.artist:
                self.artist, created = Artist.objects.get_or_create(
                    name__iexact=inspobj.artist.strip(),
                )
            if (not self.album or update_album) and hasattr(inspobj, 'album') and inspobj.album:
                self.album, created = Album.objects.get_or_create(
                    name__iexact=inspobj.album.strip(),
                )

            if hasattr(inspobj, 'is_compilation') and inspobj.is_compilation is not None:
                self.album.is_compilation = inspobj.is_compilation
                self.album.save()

            self.name = getattr(inspobj, 'name', None) or self.name
            self.year = getattr(inspobj, 'year', None) or self.year
            self.disc_number = getattr(inspobj, 'disc', None) or self.disc_number
            self.track_number = getattr(inspobj, 'track', None) or self.track_number

            self.length = getattr(inspobj, 'length', None) or self.length
            assetfile.length = getattr(inspobj, 'length', None) or assetfile.length
            assetfile.mimetype = getattr(inspobj, 'mimetype', assetfile.mimetype)

            descriptor, created = assetfile.assetdescriptor_set.get_or_create(bitstream=0, defaults={
                'mimetype': assetfile.mimetype,
                'bit_rate': getattr(inspobj, 'bitrate', None),
                'is_vbr': getattr(inspobj, 'is_vbr', None),
                'lossy': getattr(inspobj, 'lossy', None),
                'sample_rate': getattr(inspobj, 'samplerate', None),
            })

            for apic in getattr(inspobj, 'artwork', []):
                # We have a picture!  Extract it onto its own AssetFile.
                apic_obj_fn = u'APIC-{0}-{1}'.format(
                    self.pk,
                    assetfile.pk,
                )
                apic_obj, apic_created = AssetFile.objects.get_or_create(
                    asset = self,
                    mimetype = apic['mimetype'],
                    name = apic_obj_fn,
                )
                apic_obj.contents.save(apic_obj_fn, ContentFile(apic['data']))
                apic_obj.save()

class PlayManager(models.Manager):
    def get_last_play(self, asset):
        qs = self.filter(asset=asset, played=True).order_by('-modified')
        try:
            return qs[0]
        except IndexError:
            return None

class Play(models.Model):
    "Logs when an asset has been played."
    CONTEXT_STANDALONE = 0
    CONTEXT_QUEUE = 1
    CONTEXT_CHOICES = (
                        (CONTEXT_STANDALONE, 'standalone player'),
                        (CONTEXT_QUEUE, 'queue player'),
                      )

    created         = models.DateTimeField(auto_now_add=True)
    modified        = models.DateTimeField(auto_now=True)

    asset           = models.ForeignKey(Asset)
    user            = models.ForeignKey(User, blank=True, null=True,
                            on_delete=models.SET_NULL)

    played          = models.BooleanField(default=True)

    context         = models.SmallIntegerField(
                            choices=CONTEXT_CHOICES,
                            default=CONTEXT_STANDALONE)
    previous_play   = models.ForeignKey('self',
                            blank=True, null=True,
                            on_delete=models.SET_NULL)
    queue           = models.ForeignKey('queuer.AssetQueue',
                            blank=True, null=True,
                            on_delete=models.SET_NULL)
    in_groove       = models.NullBooleanField(blank=True, null=True,
                            default=None,
                            verbose_name="Is this set grooving?")

    objects = PlayManager()

    def __unicode__(self):
        return u"Play {0} ({1}, {2}, {3})".format(
            self.pk,
            self.asset.name,
            'played' if self.played else 'not played',
            self.get_context_display(),
        )

class RatingManager(models.Manager):
    def get_average_rating(self, asset, history=None):
        qs = self.filter(asset=asset)
        if history:
            qs = qs.filter(modified__gte=datetime.now()-history)
        qs = qs.aggregate(Avg('rating'))
        return qs['rating__avg']

class Rating(models.Model):
    "A user's rating of an asset"
    RATING_NONE = 0
    RATING_1    = 1
    RATING_2    = 2
    RATING_3    = 3
    RATING_4    = 4
    RATING_5    = 5
    RATING_CHOICES = (
                        (RATING_NONE, 'none'),
                        (RATING_1, 'blows major goats'),
                        (RATING_2, 'not my thing right now'),
                        (RATING_3, 'not bad'),
                        (RATING_4, 'pretty good'),
                        (RATING_5, 'great'),
                     )

    created     = models.DateTimeField(auto_now_add=True)
    modified    = models.DateTimeField(auto_now=True)

    asset       = models.ForeignKey(Asset)
    user        = models.ForeignKey(User)
    play        = models.ForeignKey(Play, blank=True, null=True, on_delete=models.SET_NULL)
    rating      = models.SmallIntegerField(choices=RATING_CHOICES, default=RATING_NONE)

    objects = RatingManager()

    def __unicode__(self):
        return u"Rating {0}: {1}, {2}-star ({3})".format(
            self.pk,
            self.asset.name,
            self.rating,
            self.get_rating_display(),
        )
