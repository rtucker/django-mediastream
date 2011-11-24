from django.contrib.auth.decorators import login_required
from django.db.models import Count
from django.http import HttpResponse
from django.shortcuts import render_to_response, redirect
from django.template import RequestContext
from django.utils import simplejson

from mediastream.assets.models import AssetFile
from mediastream.queuer.models import AssetQueue

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
    offer = queue.get_offer_set()
    for i in offer:
        i.state = 'offered'
        i.save()

    context = {
        'offer': offer,
    }

    return render_to_response('player/queue_play.html', context, context_instance=RequestContext(request))

@login_required
def player_event_handler(request):
    post = request.POST.copy()
    if 'src' in post:
        filepath = urlparse.urlparse(post['src']).path
        qs = AssetFile.objects.filter(contents__contains=urllib.unquote(filepath).strip('/'))
    else:
        qs = AssetFile.objects.none()

    if qs.exists():
        current_track = qs[0]
        current_name = current_track.asset.track.name
        current_artist = current_track.asset.track.artist
    else:
        current_track = None
        current_name = 'unknown'
        current_artist = 'unknown'

    player_state = post.get('eventType', 'jPlayer_unknown')

    remaining = int(post.get('playlistLength', 0))

    d = {'response': ('Hello, {}.  You are listening to {} by {}.').format(
            request.user,
            current_name,
            current_artist,
        )}

    # Handle session love
    queue = request.session.get('active_queue', None)
    if not queue:
        d['response'] = ("I'm sorry, but please reload this page when "
                         "you get a chance.")

    # Make sure our current song state is right
    all_offered = queue.item_set.filter(state__in=['offered', 'playing'])
    for i in all_offered:
        if not current_track:
            break
        if player_state == 'jPlayer_play':
            if i.state == 'playing' and i.asset != current_track.asset:
                # :-(
                i.state = 'skipped'
                i.save()
            elif i.asset == current_track.asset:
                i.state = 'playing'
                i.save()
                break
        elif player_state == 'jPlayer_ended':
            if i.asset == current_track.asset:
                i.state = 'played'
                i.save()
                break

    # Top off the user's playlist
    d['tracks'] = []
    while len(d['tracks']) + remaining < 3:
        candidates = queue.item_set.filter(state='waiting')
        if not candidates.exists():
            d['response'] += u"  You're almost out of music in this queue."
            break
        i = candidates[0]
        url = i.asset.track.get_streaming_url()
        key = i.asset.track.get_streaming_exten()
        d['tracks'].append({
            'title': unicode(i.asset.track),
            'free': request.user.has_perm('asset.can_download_asset'),
            key: url
        })
        i.state = 'offered'
        i.save()

    return HttpResponse(simplejson.dumps(d), mimetype="application/json")
