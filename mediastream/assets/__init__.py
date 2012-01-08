from django.conf import settings

from utilities.mediainspector import mt

import os

basepath = getattr(settings, 'ASSETS_UPLOAD_TO', '/assets')

def _get_upload_path(instance, filename):
    "Determine the location for uploaded files."
    if not instance.mimetype:
        instance.mimetype = mt.guess_type(filename)[0]
    
    if hasattr(instance.asset, 'track'):
        if instance.asset.track.album.is_compilation:
            return os.path.join(basepath,
                    'V',
                    'Various Artists',
                    instance.asset.track.album.name, instance.filename)
        else:
            return os.path.join(basepath,
                    instance.asset.track.artist.name.upper()[0],
                    instance.asset.track.artist.name,
                    instance.asset.track.album.name, instance.filename)
    else:
        return os.path.join(basepath, instance.filename)
