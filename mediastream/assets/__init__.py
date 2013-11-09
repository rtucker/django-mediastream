from django.conf import settings

from mediastream.utilities.mediainspector import mt

import os
import time

basepath = getattr(settings, 'ASSETS_UPLOAD_TO', '/assets')

def _get_upload_path(instance, filename):
    "Determine the location for uploaded files."
    if not instance.mimetype:
        instance.mimetype = mt.guess_type(filename)[0]
        instance.save()

    # Make filename slightly more unique
    inst_base, inst_ext = os.path.splitext(instance.filename)
    inst_base += '_%x' % (time.time()*100)
    inst_fn = inst_base + inst_ext

    if hasattr(instance.asset, 'track'):
        if instance.asset.track.album.is_compilation:
            return os.path.join(basepath,
                    'V',
                    'Various Artists',
                    instance.asset.track.album.name, inst_fn)
        else:
            return os.path.join(basepath,
                    instance.asset.track.artist.name.upper()[0],
                    instance.asset.track.artist.name,
                    instance.asset.track.album.name, inst_fn)
    else:
        return os.path.join(basepath, inst_fn)
