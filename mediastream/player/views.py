from django.contrib.auth.decorators import login_required
from django.db.models import Count
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render_to_response, redirect
from django.template import RequestContext
from django.utils import simplejson

from mediastream.assets.models import Asset, AssetFile, Play, Rating, Track
from mediastream.queuer.models import AssetQueue, AssetQueueItem

from datetime import datetime, timedelta
import urllib
import urlparse

RECENT_DAYS=7
TRACKS_OUT=3

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

        d = {'response':    ('Hello, {0}!').format(
                                request.user.first_name or request.user.username,
                                ),
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
            play_pointer = Play.objects.create(
                asset = current_track.asset,
                context = Play.CONTEXT_QUEUE,
                queue = queue,
                played = False,
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
            d['response'] += u"  Error {0} occurred: {1}".format(
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
    shortage = False
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
            key = next_track.asset.track.get_streaming_exten()
            url = next_track.asset.track.get_streaming_url()
            poster = next_track.asset.track.get_artwork_url()
            d['tracks'].append({
                key: url,
                'pk': next_track.pk,
                'artist': unicode(next_track.asset.track.artist),
                'title': unicode(next_track.asset.track),
                'free': request.user.has_perm('asset.can_download_asset', next_track.asset),
                'poster': poster or '',
            })
            next_track.state = 'offered'
            next_track.save()

        except AssetFile.DoesNotExist:
            # no way to stream this!
            next_track.state = 'fileerror'
            next_track.save()

        except AssetQueueItem.DoesNotExist:
            # queue is empty!
            shortage = True
            randtrack = None
            while not randtrack:
                randtrack = Track.objects.get_random()
                if Play.objects.filter(modified__gt=datetime.now()-timedelta(days=RECENT_DAYS), asset=randtrack).exists():
                    randtrack = None
                else:
                    aqi = AssetQueueItem.objects.create(
                        queue = queue,
                        asset_object = randtrack,
                    )

    if shortage:
        d['response'] = u"I'm picking random tracks for you, {0}.".format(request.user.first_name or request.user.username)

    # God save the state
    request.session['active_queue'] = queue.pk
    request.session['first_refresh'] = False
    request.session['offer_pointer'] = offer_pointer.pk
    request.session['play_pointer'] = play_pointer_pk
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

    # Get our asset by AssetQueueItem
    asset_pk = request.POST.get('asset', None)
    try:
        asset = AssetQueueItem.objects.get(pk=asset_pk).asset
    except Asset.DoesNotExist:
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
            resp.append("I've recorded your {0}-star ({1}) review.".format(
                 rating_obj.rating, rating_obj.get_rating_display()))
        else:
            rating_obj.delete()
            d['rating'] = 0
            resp.append("Old rating removed.")

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

    return HttpResponse(simplejson.dumps(d), mimetype="application/json")
