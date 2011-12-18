from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.files import File
from django.http import HttpResponseRedirect
from django.shortcuts import render_to_response
from django.template import RequestContext

from mediastream.assets.forms import UploadFileForm, ImportFileForm
from mediastream.assets.models import Album, Artist, Track, AssetFile
from mediastream.utilities.mediainspector import Inspector

import os
from tempfile import NamedTemporaryFile
import zipfile

@login_required
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
