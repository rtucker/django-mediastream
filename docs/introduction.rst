=The Problem=
I have a lot of music.  I want to listen to it, explore it, and enjoy it,
but I have many computers and mobile devices in various locations, with
various capabilities and amounts of local storage.

=Things That Don't Work, And Why=
* Most local music library applications: The MP3 format stores metadata
  within each file, which is not too difficult when the music is stored
  locally.  (Most applications cache this data in a database, anyway.)
  The trouble is that I do not want to store my music locally: I have
  multiple computers and nearly-ubiquitous high-speed Internet access, so
  I want to store my music elsewhere and download it just-in-time.  Suffice
  to say, thousands of MP3s on Amazon S3 with s3fs does not work well when
  it comes time to read ID3 tags.  About that time, Amazon Cloud Player
  started to look like a very good choice...

* Amazon Cloud Drive/Player: Too much metadata is stored on the client.
  My mobile device has limited internal storage, and the Amazon application
  will not let itself be moved to SD storage.  Thus, my phone melts.
  Also, it is not trivial to download your music from Amazon in bulk.
  I ultimately used Gladinet Cloud Desktop for Windows on Amazon EC2, which
  may be ironic.

* Google Music: I suspect the mobile software has similar faults as Amazon,
  but I never got a chance to test it.  I decided to use EC2 for the Amazon
  Cloud liberation project, and while Google Music Manager exists for
  Windows and Linux, I could not log in from either platform.  Apparently,
  MAC addresses are used to enforce licensing restrictions, and since EC2
  instances have dynamic, locally-assigned MAC addresses, too bad!  I
  could use real hardware, of course, but I already spent weeks uploading
  these files once...

At this point, I dumped all the ID3 information to a flat file with Mp3tag,
then used Gladinet to upload the files to Amazon S3.  (This was 5x faster
than downloading from Amazon Cloud Drive.)

=The Idea=
A common theme among the failures is the fat client.  Too much work is done
locally, far away from the files and the resource-rich servers of the cloud.
This is fine for small collections, and leads to a faster user experience
in a lot of cases.  But, for large libraries and resource-limited devices,
the synchronization and local storage requirements become significant.

An example of something that works well is Pandora.  They cannot use a fat
client.  Instead, the client authenticates to the server, and informs the
server that the user is requesting a particular "station."  The server
knows what the user has heard before, what they liked, what they didn't
like, etc.; the important part is that the client tells the server what the
user wants, and the server sends the client a short list of songs to play
next.

From here, the process is very similar to the fat clients.  The list of
songs has all the usual metadata (artist, title, album art URL, ...) and
an authenticated URL to retrieve the song.  The client plays the songs
and the user is happy.

The goal of this project is to implement a similar architecture.

=Architecture=
==Server==
Django is the framework of choice here, as it has the flexibility to
work with almost anything.  It could run on physical hardware in your
bikeshed, a VPS, or probably even something like Google App Engine.
It could run on the same device as the client, too.  The important part
is that it does not necessarily need to have the storage or bandwidth for
music files.

Metadata will be stored in a database (MySQL, PostgreSQL, SQLite, whatever).
Its template engine will be used to render the web-based UI.

==Storage==
Initially, Amazon S3 will be used, since that is what I'm using.  However,
the normal Django file handling stuff will be used, so really, you could
stick the files whereever.  With S3 (and presumably others), the ability
to generate pre-authenticated URLs with a limited valid time will be used,
rather than tromboning the file content through the server or leaving it
open to the world.

==Client==
The first client will be an Android 2.3 phone, but I'm lazy and would
rather avoid writing specifically for one platform.  So, a HTML5-based
experience will be used, initially with the Android browser.  jPlayer
seems like a good choice for this.

This also lets the "beaten path" be used for authentication, layout, etc.
Unfortunately, it limits UI options -- notifications, widgets, lock-screen
controls.  It also limits local storage options for offline or low-bandwidth
use.  We'll cross that duck when it quacks.
