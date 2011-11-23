from django.contrib.auth.decorators import login_required
from django.shortcuts import render_to_response
from django.template import RequestContext
from mediastream.queuer.models import AssetQueue

@login_required
def music_player(request):
    "Returns a jPlayer music player for the user, with some stuff in the queue."
    for queue in AssetQueue.objects.filter(user=request.user):
        offer = queue.get_offer_set()
        if offer.exists():
            break

    context = {
        'offer': offer,
    }

    return render_to_response('player/queue_play.html', context, context_instance=RequestContext(request))
