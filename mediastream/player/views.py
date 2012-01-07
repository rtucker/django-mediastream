from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib.humanize.templatetags.humanize import naturalday
from django.db import connection
from django.db.models import Count
from django.views.decorators.cache import never_cache, cache_page
from django.http import HttpResponse, Http404
from django.shortcuts import get_object_or_404, render_to_response, redirect
from django.template import RequestContext
from django.utils import simplejson

from mediastream.assets.models import Asset, AssetFile, Play, Rating, Track, Artist, Album, Discogs
from mediastream.queuer.models import AssetQueue, AssetQueueItem

from datetime import datetime, timedelta
import discogs_client as discogs
from gitrevision.utils import gitrevision
import pycurl
from StringIO import StringIO
import urlparse

RECENT_DAYS=7
TRACKS_OUT=3

@never_cache
@login_required
def music_player(request):
    "Returns a jPlayer music player for the user, with some stuff in the queue."
    # Find queues with unplayed stuff
    all_queues = AssetQueue.objects.filter(user=request.user)
    queues = all_queues.filter(item_set__state__in=['waiting', 'offered']
                            ).annotate(Count('item_set__state'))
    if not queues.exists():
        #return redirect('player-set-queue')
        return HttpResponse('utoh')

    # TODO: Make selection easier
    queue = queues[0]

    # Clear any offered tracks
    queue.item_set.filter(state='offered').update(state='waiting')
    queue.item_set.filter(state='playing').update(state='waiting')

    request.session['active_queue'] = queue.pk
    request.session['first_refresh'] = True
    request.session['offer_pointer'] = None
    request.session['play_pointer'] = None

    return render_to_response('player/queue_play.html', {}, context_instance=RequestContext(request))

@login_required
def player_event_handler(request):
    "Handles AJAX events from the client."
    if not request.is_ajax() or request.method != 'POST':
        return HttpResponse('oh no')

    post = request.POST.copy()
    d = {}

    # The queue we're currently playing from.
    queue_pk = request.session.get('active_queue', None)

    # Is this the first load of stuff?
    first_refresh = request.session.get('first_refresh', False)

    # Currently playing track
    current_track_pk = post.get('mediaPk', None)

    # The last track offered
    offer_pointer_pk = request.session.get('offer_pointer', None)

    # The current Play
    play_pointer_pk = request.session.get('play_pointer', None)

    # Remaining tracks
    remaining = int(post.get('playlistLength', 0))

    # Start building response
    if not queue_pk:
        d['response'] = ("I'm sorry, but please reload this page when "
                         "you get a chance.  I've had an accident.")
        return HttpResponse(simplejson.dumps(d), mimetype="application/json")

    # Determine client state
    player_state = post.get('eventType', 'jPlayer_unknown')
    queue = AssetQueue.objects.get(pk=queue_pk)

    if current_track_pk:
        current_track = AssetQueueItem.objects.get(pk=current_track_pk)

        current_name = current_track.asset.track.name
        current_artist = current_track.asset.track.artist

        d = {
             'artistName':  current_track.asset.track.artist.name,
             'artistPk':    current_track.asset.track.artist.pk,
             'trackName':   current_track.asset.track.name,
             'trackPk':     current_track.asset.track.pk,
             'albumName':   current_track.asset.track.album.name,
             'albumPk':     current_track.asset.track.album.pk,
             'queuePk':     queue.pk,
            }

        # Handle client states
        if player_state == 'jPlayer_play':
            # Player is currently playing.
            AssetQueueItem.objects.filter(pk__lt=current_track.pk, state='playing').update(state='skipped')
            current_track.state = 'playing'
            current_track.save()

            last_play = current_track.asset.last_play

            if last_play:
                d['response'] = u"{0}, the last time you listened to {1} was {2}.".format(
                    request.user.first_name or request.user.username,
                    current_track.asset.name,
                    naturalday(last_play),
                )

            play_pointer = Play.objects.create(
                asset = current_track.asset,
                context = Play.CONTEXT_QUEUE,
                queue = queue,
                played = False,
                user = request.user,
            )

            if play_pointer_pk:
                try:
                    old_play = Play.objects.get(pk=play_pointer_pk)
                    play_pointer.previous_play = old_play
                    play_pointer.save()
                except:
                    pass

            play_pointer_pk = play_pointer.pk

        elif player_state == 'jPlayer_ended':
            current_track.state = 'played'
            current_track.save()
            remaining -= 1
            if play_pointer_pk:
                try:
                    play_pointer = Play.objects.get(pk=play_pointer_pk)
                    play_pointer.played = True
                    play_pointer.save()
                    play_pointer_pk = play_pointer.pk
                except:
                    pass

        elif player_state == 'jPlayer_error':
            # oh no!
            d['response'] = u"  Error {0} occurred: {1}".format(
                        post.get('errorType', 'unknown'),
                        post.get('errorMsg', 'no msg'))
            current_track.state = 'fileerror'
            current_track.save()

    if offer_pointer_pk:
        offer_pointer = AssetQueueItem.objects.get(pk=offer_pointer_pk)
    else:
        offer_pointer = None
        remaining = 0

    # Top off the user's playlist
    d['tracks'] = []
    while (len(d['tracks']) + remaining) < TRACKS_OUT:
        try:
            if not offer_pointer:
                next_track = queue.item_set.all()[0]
            else:
                next_track = offer_pointer.get_next_by_created()
            offer_pointer = next_track
            if next_track.state != 'waiting':
                continue
            if not request.user.has_perm('asset.can_stream_asset', next_track.asset):
                continue

            # Try to build out discogs data slowly but surely
            try:
                artist = next_track.asset.track.artist
                #album  = next_track.asset.track.album
                artist.discogs = Discogs.objects.get_for_object(artist)
                artist.save()
                #album.discogs = Discogs.objects.get_for_object(album)
                #album.save()
            except Discogs.DoesNotExist:
                pass

            key = next_track.asset.track.get_streaming_exten()
            url = next_track.asset.track.get_streaming_url()
            poster = next_track.asset.track.get_artwork_url()
            last_play = next_track.asset.last_play
            d['tracks'].append({
                key: url,
                'pk': next_track.pk,
                'assetPk': next_track.asset.pk,
                'album': next_track.asset.track.album.name,
                'artist': next_track.asset.track.artist.name,
                'title': next_track.asset.track.name,
                'free': request.user.has_perm('asset.can_download_asset', next_track.asset),
                'poster': poster or '',
                'averageRating': next_track.asset.average_rating or 0,
                'lastPlayAt': last_play.isoformat() if last_play else '',
            })
            next_track.state = 'offered'
            next_track.save()

        except AssetFile.DoesNotExist:
            # no way to stream this!
            next_track.state = 'fileerror'
            next_track.save()

        except AssetQueueItem.DoesNotExist:
            # queue is empty!
            randtrack = Track.objects.get_shuffle(request.user, offer_pointer)
            if not AssetQueueItem.objects.filter(
                object_id=randtrack.pk,
                state__in=['offered', 'playing'],
            ).exists():
                aqi = AssetQueueItem.objects.create(
                    asset_object = randtrack,
                    queue = queue,
                )
                d['randstats'] = randtrack._randstats

    if request.session.get('first_refresh', False):
        request.session['first_refresh'] = False
        d['response'] = u"Hello, {0}.  I am django-mediastream.  This is {1}.  I know {2} tracks, {3} albums and {4} artists.  I have played {5} tracks and recorded {6} ratings.".format(
            request.user.first_name or request.user.username,
            unicode(queue),
            Track.objects.count(),
            Album.objects.count(),
            Artist.objects.count(),
            Play.objects.count(),
            Rating.objects.count(),
        )

    # God save the state
    request.session['active_queue'] = queue.pk
    request.session['offer_pointer'] = offer_pointer.pk
    request.session['play_pointer'] = play_pointer_pk

    d['_queries'] = len(connection.queries)
    d['_querytime'] = sum([float(f['time']) for f in connection.queries])
    d['_revision'] = gitrevision()[0:10]

    return HttpResponse(simplejson.dumps(d), mimetype="application/json")

@login_required
def collect_rating(request):
    GROOVE_STATES = {
        'awyeah': True,
        'nope': False,
        'pokerface': None,
    }

    d = {}
    resp = []

    if not request.is_ajax() or request.method != 'POST':
        return HttpResponse('oh no')

    # We expect a rating and a groove.
    groove = request.POST.get('groove', None)
    rating = request.POST.get('rating', None)

    # Get our asset by assetpk
    asset_pk = request.POST.get('assetpk', None)
    try:
        asset = Asset.objects.get(pk=asset_pk)
    except Asset.DoesNotExist:
        asset = None

    # Fallback: legacy JS sends asset queue item pk, not asset pk
    if not asset:
        assetqueueitem_pk = request.POST.get('asset', None)
        try:
            aqi = AssetQueueItem.objects.get(pk=assetqueueitem_pk)
            asset = Asset.objects.get(pk=aqi.object_id)
        except AssetQueueItem.DoesNotExist, Asset.DoesNotExist:
            asset = None

    # We should have a play_pointer in the session.
    play_pointer_pk = request.session.get('play_pointer', None)
    try:
        play = Play.objects.get(pk=play_pointer_pk)
    except Play.DoesNotExist:
        play = None

    if play and asset and asset.pk != play.asset.pk:
        # We might have a stale session.
        play = None

    if play and not asset:
        asset = play.asset

    # Handle rating, 1-5 stars.
    if rating and asset:
        rating = int(rating)

        try:
            rating_obj = Rating.objects.get(play=play)
        except Rating.DoesNotExist:
            rating_obj = Rating()

        if rating == rating_obj.rating:
            rating = 0

        if rating > 0:
            rating_obj.asset = asset
            rating_obj.user = request.user
            rating_obj.play = play
            rating_obj.rating = rating
            rating_obj.save()
            rating_obj = Rating.objects.get(pk=rating_obj.pk)
            d['rating'] = rating_obj.rating
            resp.append(u"I've logged your opinion ({0}) for {1}.".format(rating_obj.get_rating_display(), asset.name))
        else:
            resp.append(u"I've removed the {0}-star rating for {1}.".format(rating_obj.rating, asset.name))
            rating_obj.delete()
            d['rating'] = 0

        asset = Asset.objects.get(pk=asset.pk)  # reload so that average_rating is right
        d['avg_rating'] = asset.average_rating or 0
        d['total_ratings'] = asset.rating_set.count()

    # Handle groove, which is related to how well this track fits
    # into a stream of plays.
    if groove and play:
        play.in_groove = GROOVE_STATES.get(groove, None)
        play.save()

        if play.in_groove is True:
            resp.append("Acknowledging ongoing groove.")
        elif play.in_groove is False:
            resp.append("Sorry about harshing the mellow.")
        else:
            resp.append("Okay.")

    d['response'] = ' '.join(resp)

    d['_queries'] = len(connection.queries)
    d['_querytime'] = sum([float(f['time']) for f in connection.queries])
    d['_revision'] = gitrevision()[0:10]

    return HttpResponse(simplejson.dumps(d), mimetype="application/json")

@login_required
@cache_page(604800)
def discogs_image_view(request, image):
    """Proxies an image view from Discogs.

    Expects image to be the path of a resource_url, i.e.

        In [69]: d.data['images'][0]['resource_url']
        Out[69]: u'http://api.discogs.com/image/A-67830-1080022087.jpg'

        In [70]: urlparse(d.data['images'][0]['resource_url'])
        Out[70]: ParseResult(scheme=u'http', netloc=u'api.discogs.com', path=u'/image/A-67830-1080022087.jpg', params='', query='', fragment='')

        In [71]: urlparse(d.data['images'][0]['resource_url']).path
        Out[71]: u'/image/A-67830-1080022087.jpg'
    """

    if not image.startswith('/image'):
        raise Http404

    urlbase = discogs.api_uri
    b = StringIO()
    h = StringIO()
    c = pycurl.Curl()
    c.setopt(pycurl.URL, str(urlbase + image))
    c.setopt(pycurl.USERAGENT, settings.HTTP_USER_AGENT)
    c.setopt(pycurl.FOLLOWLOCATION, 1)
    c.setopt(pycurl.HEADERFUNCTION, h.write)
    c.setopt(pycurl.WRITEFUNCTION, b.write)
    c.perform()
    b.seek(0)
    h.seek(0)

    if c.getinfo(pycurl.HTTP_CODE) > 399:
        raise Http404

    content_type = None
    for line in h:
        if line.startswith('Content-Type: '):
            hdr, content_type = line.strip().split(': ', 1)
            break

    resp = HttpResponse(content=b, content_type=content_type)
    resp['X-Retrieved'] = datetime.now().isoformat()
    return resp
