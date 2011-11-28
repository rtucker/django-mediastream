from django.contrib.auth.decorators import login_required
from django.db.models import Count
from django.http import HttpResponse
from django.shortcuts import render_to_response, redirect
from django.template import RequestContext
from django.utils import simplejson

from mediastream.assets.models import AssetFile
from mediastream.queuer.models import AssetQueue, AssetQueueItem

import urllib
import urlparse

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

    request.session['active_queue'] = queue
    request.session['first_refresh'] = True
    context = {'offer': []}

    next_track = queue.item_set.filter(state__in=['waiting', 'offered'])[0]
    request.session['last_known_playing'] = next_track

    while len(context['offer']) < 1:
        try:
            if next_track.state not in ['waiting', 'offered']:
                next_track = next_track.get_next_by_created()
                continue
            if not request.user.has_perm('asset.can_stream_asset', next_track.asset):
                next_track = next_track.get_next_by_created()
                continue
            url = next_track.asset.track.get_streaming_url()
            key = next_track.asset.track.get_streaming_exten()
            context['offer'].append(next_track)
            next_track.state = 'offered'
            next_track.save()
            request.session['last_track_offered'] = next_track
            next_track = next_track.get_next_by_created()

        except AssetQueueItem.DoesNotExist:
            break

    return render_to_response('player/queue_play.html', context, context_instance=RequestContext(request))

@login_required
def player_event_handler(request):
    "Handles AJAX events from the client."
    post = request.POST.copy()

    # Handle session love
    queue = request.session.get('active_queue', None)
    offer_pointer = request.session.get('last_track_offered', None)
    last_known_playing_pk = request.session.get('last_known_playing', None).pk
    last_known_playing = AssetQueueItem.objects.get(pk=last_known_playing_pk)

    # Determine client state
    player_state = post.get('eventType', 'jPlayer_unknown')

    if 'mediaPk' in post:
        # First item on the playlist
        current_track = AssetQueueItem.objects.get(pk=post['mediaPk'])
    else:
        current_track = last_known_playing

    if 'caboosePk' in post:
        # Last item on the playlist
        offer_pointer = AssetQueueItem.objects.get(pk=post['caboosePk'])

    current_name = current_track.asset.track.name
    current_artist = current_track.asset.track.artist
    remaining = int(post.get('playlistLength', 0))

    # Start building response
    d = {}

    if not queue or not offer_pointer or not last_known_playing:
        d['response'] = ("I'm sorry, but please reload this page when "
                         "you get a chance.  I've had an accident.")
        return HttpResponse(simplejson.dumps(d), mimetype="application/json")

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
         'tracks':      [],
        }

    # Handle client states
    if player_state == 'jPlayer_play':
        # Player is currently playing.
        if request.session.get('first_refresh', False):
            last_known_playing.state = 'playing'
            last_known_playing.save()
            request.session['first_refresh'] = False
        if current_track.asset != last_known_playing.asset:
            if last_known_playing.state == 'playing':
                # We should have received an ended notification
                last_known_playing.state = 'skipped'
                last_known_playing.save()
            elif last_known_playing.state != 'played':
                last_known_playing.state = 'played'
                last_known_playing.save()
            last_known_playing = current_track
            last_known_playing.state = 'playing'
            last_known_playing.save()

    if player_state == 'jPlayer_ended':
        current_track.state = 'played'
        current_track.save()

    if player_state == 'jPlayer_error':
        # oh no!
        d['response'] += u"  Error {0} occurred: {1}".format(
                    post.get('errorType', 'unknown'),
                    post.get('errorMsg', 'no msg'))
        current_track.state = 'fileerror'
        current_track.save()

    # Top off the user's playlist
    shortage = False
    while len(d['tracks']) + remaining < 3:
        try:
            next_track = offer_pointer.get_next_by_created()
            offer_pointer = next_track
            if next_track.state != 'waiting':
                continue
            if not request.user.has_perm('asset.can_stream_asset', next_track.asset):
                continue
            poster_af = next_track.asset.track.assetfile_set.filter(mimetype__startswith='image/').order_by('?')
            if poster_af.exists():
                poster = poster_af[0].contents.url
            else:
                poster = None
            url = next_track.asset.track.get_streaming_url()
            key = next_track.asset.track.get_streaming_exten()
            d['tracks'].append({
                'pk': next_track.pk,
                'artist': unicode(next_track.asset.track.artist),
                'title': unicode(next_track.asset.track),
                'free': request.user.has_perm('asset.can_download_asset', next_track.asset),
                key: url,
                'poster': poster or '',
            })
            next_track.state = 'offered'
            next_track.save()

        except AssetQueueItem.DoesNotExist:
            # queue is empty!
            shortage = True
            break

    if shortage:
        d['response'] = u"You're almost out of music, {0}.".filter(request.user.first_name or request.user.username)

    d['title'] = '{0}{1} - {2} - mediastream'.format(
            '* ' if shortage else '',
            current_name,
            current_artist,
        )

    # God save the state
    request.session['last_known_playing'] = last_known_playing
    request.session['offer_pointer'] = offer_pointer
    return HttpResponse(simplejson.dumps(d), mimetype="application/json")
