from django.conf import settings

import mimetypes
import os

basepath = getattr(settings, 'ASSETS_UPLOAD_TO', '/assets')

# Group and sort the mimetypes, for ease of display
mimetypes_grouped = {}
for mt in mimetypes.types_map.values():
    mt0, mt1 = mt.split('/',1)
    if mt0 not in mimetypes_grouped:
        mimetypes_grouped[mt0] = []
    if (mt, mt1) not in mimetypes_grouped[mt0]:
        mimetypes_grouped[mt0].append((mt, mt1))
    mimetypes_grouped[mt0].sort()

MIMETYPE_CHOICES = sorted(mimetypes_grouped.items())

def _get_upload_path(instance, filename):
    "Determine the location for uploaded files."
    if not instance.mimetype:
        instance.mimetype = mimetypes.guess_type(filename)[0]
    
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
