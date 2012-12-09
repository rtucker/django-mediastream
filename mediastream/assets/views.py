from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ObjectDoesNotExist
from django.core.files import File
from django.core.urlresolvers import reverse
from django.http import HttpRequest, HttpResponseRedirect, Http404
from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext
from django.views.decorators.cache import never_cache
from django.views.generic import ListView, DetailView, RedirectView

from mediastream.assets.forms import UploadFileForm, ImportFileForm
from mediastream.assets.models import Album, Artist, Track, AssetFile
from mediastream.utilities.mediainspector import Inspector
from mediastream.utilities.recursion import long_substr

import os
from tempfile import NamedTemporaryFile
import zipfile

@login_required
@never_cache
def upload_file(request):
    # TODO: Much of this can be eliminated, thanks to Track.objects.create_from_file
    if request.method == 'POST':
        upform = UploadFileForm(request.POST, request.FILES)
        imform = ImportFileForm(request.POST)
        stashes = []
        if upform.is_valid():
            for upload in request.FILES.getlist('file'):
                stash = NamedTemporaryFile()
                for chunk in upload.chunks():
                    stash.write(chunk)
                stash.seek(0)
                stashes.append((stash, upload.name,))

        if imform.is_valid() and 'path' in request.POST:
            stashes.append((open(request.POST.get('path')), request.POST.get('path'),))

        for stash, filename in stashes:
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
                messages.info(request, 'Found {0} file{1} in zip file {2}.'.format(count, '' if count == 1 else 's', filename))
            elif inspobj.mimetype.startswith('audio/'):
                stash.seek(0)
                files.append((stash, inspobj))
                messages.info(request, 'Found {0} to be a Track of type {1}.'.format(filename, inspobj.mimetype))
            else:
                messages.error(request, 'Could not figure out what to do with {0} of type {1}.'.format(filename, inspobj.mimetype))

            for f, i in files:
                count = 0
                mandatory = ['artist', 'album', 'name']
                proceed = True
                for attrib in mandatory:
                    if not getattr(i, attrib, None):
                        messages.error(request, 'Could not import sequence {0} - no {1} tag!'.format(count, attrib))
                        proceed = False

                if not proceed:
                    continue

                art, cre = Artist.objects.get_or_create(
                    name__iexact=i.artist,
                    defaults={
                        'name': i.artist,
                    },
                )
                if cre: messages.warning(request, 'Creating artist {0}'.format(art.name))
                alb, cre = Album.objects.get_or_create(
                    name__iexact=i.album,
                    defaults={
                        'name': i.album,
                        'is_compilation': getattr(i, 'is_compilation', False),
                    },
                )
                if cre: messages.warning(request, 'Creating album {0}'.format(art.name))
                t, cre = Track.objects.get_or_create(
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

                messages.success(request, 'Imported {0} by {1}.'.format(t.name, art.name))
                count += 1
            return HttpResponseRedirect('/assets/upload/')
    else:
        upform = UploadFileForm()
        imform = ImportFileForm()
    return render_to_response('assets/upload.html', {'upform': upform, 'imform': imform}, context_instance=RequestContext(request))

@login_required
@never_cache
def merge_assets_view(request, **kwargs):
    ct = kwargs['ct']
    ids = kwargs['ids'].split(',')
    content_type = ContentType.objects.get(pk=ct)

    if content_type.model_class() is Album:
        child = 'track_set'
        attribute = 'album'
    elif content_type.model_class() is Artist:
        child = 'track_set'
        attribute = 'artist'
    elif content_type.model_class() is Track:
        child = 'assetfile_set'
        attribute = 'asset'
    else:
        raise Http404

    context = {
        'content_type': content_type,
    }

    if request.method == 'POST':
        asset_order_raw = request.POST.get('asset_order')
        if asset_order_raw:
            # 'asset[]=123&asset[]=456'
            asset_order_raw = asset_order_raw.split('&')
            # ['asset[]=123', 'asset[]=456']
            asset_order = [int(f.split('=',1)[1]) for f in asset_order_raw] # [123, 456]
        else:
            asset_order = [int(f) for f in ids]

        assets = [content_type.get_object_for_this_type(pk=pk) for pk in asset_order]
        common_name = request.POST.get('common_name').strip()
        if common_name:
            messages.info(request, 'Preparing to merge %i assets into "%s"' % (len(assets), common_name))

            target = assets[0]

            # Renumber discs
            disc_counter = 0
            update_tracks = {}
            for asset in assets:
                # How many distinct discs do we have here?
                discs = list(asset.track_set.values_list('disc_number', flat=True).order_by().distinct())
                discs.sort()
                for disc in discs:
                    disc_counter += 1
                    update_tracks[disc_counter] = list(asset.track_set.filter(disc_number=disc))

            messages.info(request, 'New album will have %i discs' % disc_counter)
            target.discs = disc_counter
            target.name = common_name
            target.save()

            for disc_number, tracks in update_tracks.items():
                for track in tracks:
                    track.album = target
                    track.disc_number = disc_number
                    track.save()

            messages.info(request, "Merge process complete.  Please delete old albums when you have a chance.")

            return HttpResponseRedirect(reverse('admin:assets_album_change', args=(target.pk,)))

        else:
            messages.error(request, "No name specified.")

    else:
        assets = [content_type.get_object_for_this_type(pk=pk) for pk in ids]
        common_name = long_substr([a.name for a in assets])
        messages.info(request, "Drag the list around until they are in the proper order.")
        messages.info(request, "All albums will be merged into the first album, with the disc number set in this order.  The first album will be renamed to the value in the box at the bottom.")

    context['assets'] = [(a, getattr(a, child).all().order_by('disc_number', 'track_number')) for a in assets]
    context['common_name'] = common_name

    return render_to_response('assets/merge_assets.html', context, context_instance=RequestContext(request))

class TrackListView(ListView):
    context_object_name = 'tracks'
    template_name = 'assets/track_list.html'

    def get_queryset(self):
        qs = Track.objects.all()

        if 'artist_pk' in self.kwargs:
            self.artist = get_object_or_404(Artist, pk=self.kwargs['artist_pk'])
            qs = qs.filter(artist=self.artist).order_by('album')
        else:
            self.artist = None

        if 'album_pk' in self.kwargs:
            self.album = get_object_or_404(Album, pk=self.kwargs['album_pk'])
            qs = qs.filter(album=self.album).order_by('artist')
        else:
            self.album = None

        return qs.distinct()

    def get_context_data(self, **kwargs):
        context = super(TrackListView, self).get_context_data(**kwargs)
        context['artist'] = self.artist
        context['album'] = self.album
        return context

class TrackRedirector(RedirectView):
    permanent = False

    def get_redirect_url(self, **kwargs):
        track = get_object_or_404(Track, pk=kwargs['pk'])
        try:
            return track.get_streaming_url()
        except ObjectDoesNotExist:
            return None

class M3UDetailView(DetailView):
    def render_to_response(self, context, **response_kwargs):
        """
        Returns a response with a template rendered with the given context.
        """
        scheme = 'https' if self.request.is_secure() else 'http'
        host = self.request.get_host()
        context['baseurl'] = scheme + '://' + host
        return self.response_class(
            request = self.request,
            template = self.get_template_names(),
            context = context,
            mimetype = 'audio/x-mpegurl',
            **response_kwargs
        )

class PLSDetailView(DetailView):
    def render_to_response(self, context, **response_kwargs):
        """
        Returns a response with a template rendered with the given context.
        """
        scheme = 'https' if self.request.is_secure() else 'http'
        host = self.request.get_host()
        context['baseurl'] = scheme + '://' + host
        return self.response_class(
            request = self.request,
            template = self.get_template_names(),
            context = context,
            mimetype = 'audio/x-scpls',
            **response_kwargs
        )

