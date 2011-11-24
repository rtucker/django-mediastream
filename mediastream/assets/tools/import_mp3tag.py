#!/usr/bin/python
# Imports a CSV from Mp3tag.  Lots of assumptions in this file.

import os, sys
from mediastream.assets.models import Artist, Album, Track, AssetFile


# From http://docs.python.org/library/csv.html
import csv, codecs, cStringIO

class UTF8Recoder:
    """
    Iterator that reads an encoded stream and reencodes the input to UTF-8
    """
    def __init__(self, f, encoding):
        self.reader = codecs.getreader(encoding)(f)

    def __iter__(self):
        return self

    def next(self):
        return self.reader.next().encode("utf-8")

class UnicodeReader:
    """
    A CSV reader which will iterate over lines in the CSV file "f",
    which is encoded in the given encoding.
    """

    def __init__(self, f, dialect=csv.excel, encoding="utf-8", **kwds):
        f = UTF8Recoder(f, encoding)
        self.reader = csv.reader(f, dialect=dialect, **kwds)

    def next(self):
        row = self.reader.next()
        return [unicode(s, "utf-8") for s in row]

    def __iter__(self):
        return self

class UnicodeWriter:
    """
    A CSV writer which will write rows to CSV file "f",
    which is encoded in the given encoding.
    """

    def __init__(self, f, dialect=csv.excel, encoding="utf-8", **kwds):
        # Redirect output to a queue
        self.queue = cStringIO.StringIO()
        self.writer = csv.writer(self.queue, dialect=dialect, **kwds)
        self.stream = f
        self.encoder = codecs.getincrementalencoder(encoding)()

    def writerow(self, row):
        self.writer.writerow([s.encode("utf-8") for s in row])
        # Fetch UTF-8 output from the queue ...
        data = self.queue.getvalue()
        data = data.decode("utf-8")
        # ... and reencode it into the target encoding
        data = self.encoder.encode(data)
        # write to the target stream
        self.stream.write(data)
        # empty queue
        self.queue.truncate(0)

    def writerows(self, rows):
        for row in rows:
            self.writerow(row)

d = csv.excel()
d.delimiter = ';'
d.doublequote = False
d.lineterminator = '\r\n'
d.quotechar = '"'
d.skipinitialspace = None
d.quoting = csv.QUOTE_MINIMAL
c = UnicodeReader(open(sys.argv[1]), dialect=d, encoding='utf-16')

header = c.next()
print header

for row in c:
    if len(row) != 11:
        print "ROW LEN %i: %s" % (len(row), row)
        # Congratulations, you get to edit the .csv by hand, find the field with a semicolon in it, and quote it.
        # Or find the dangling ^M.
        continue
    title, artist, album, track, year, length, size, lastmod, path, filename, moot = row
    if track:
        try:
            track = int(track)
            disc = 0
        except ValueError:
            disc, track = track.split('/')
            track = int(track)
            disc = int(disc)
    else:
        track = disc = 0
    if not title:
        if track:
            title = 'Disc %d Track %d' % (disc, track)
        else:
            title = filename
    if not artist:
        artist = 'Unknown Artist'
    if not album:
        album = 'Unknown Album'
    if year:
        try:
            year = int(year.split('-',1)[0])
        except ValueError:
            year = None
    if length:
        length = int(length)
    else:
        length = None

    # Convert path to a S3 relative path
    shit, shit, shit, fertilizer = path.split('\\',3)
    path = fertilizer.replace('\\', '/')
    filepath = os.path.join(path, filename)

    # Send it to the database
    artist_obj, shit = Artist.objects.get_or_create(name__iexact=artist.strip(), defaults={'name': artist.strip()})
    album_obj, shit = Album.objects.get_or_create(name__iexact=album.strip(), defaults={'name': album.strip()})
    track_obj, shit = Track.objects.get_or_create(
                        name__iexact=title.strip(),
                        album=album_obj,
                        artist=artist_obj,
                        track_number=track,
                        disc_number=disc,
                        length=length,
                        defaults={'name': title.strip()},
                      )
    assetfile = AssetFile.objects.create(asset=track_obj, name=filename,
                        contents=filepath,)
