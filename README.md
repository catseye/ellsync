ellsync
=======

ellsync is an opinionated poka-yoke convenience wrapper for rsync.

*   opinionated: it was designed for a particular use case for using rsync
    for offline backups which will be described below.
*   poka-yoke: using rsync via ellsync prevents using it in dangerous ways.
*   convenience: ellsync provides common shortcuts for using rsync.

ellsync's operation is based on a *backup router* which is a JSON file
that looks like this:

    {
        "art": {
            "from": "/media/user/External1/art/",
            "to": "/home/user/art/"
        }
    }

In this, `art` is the name of a "backup stream", in which files in
`/media/user/External1/art/` (called the *canonical*) are periodically
synced to `/home/user/art/` (called the *cache*).

The idea is that all changes to the contents of the canonical directory
are bona fide changes, but any change to the contents of the cache can be
discarded.

Either depository may be offline, therefore neither directory is assumed
to exist (it might not exist if the volume is not mounted.)

With this router saved as `router.json` we can then say

    ellsync router.json /home/user/art/ /media/user/External1/art/

and this will in effect run

    rsync --archive --verbose --delete /home/user/art/ /media/user/External1/art/

but if we try

    ellsync router.json /media/user/External1/art/ /home/user/art/

we will be prevented, because it is an error, because the direction of
the backup stream is always from cache to canonical.

Various other configurations are prevented.  You may have noticed that rsync
is sensitive about whether a directory name ends in a slash or not.  ellsync
detects when a trailing slash is missing and adds it.  Thus

    ellsync router.json /media/user/External1/art /home/user/art/

is still interpreted as

    rsync --archive --verbose --delete /home/user/art/ /media/user/External1/art/

Since this configuration is named in the router, we don't even have to
give these directory names.  We can just give the name of the stream:

    ellsync router.json art

If either of the directories does not exist, this will be prevented.
Based on this, there is an option to list which streams are, at the moment,
backupable:

    ellsync router.json --list

Also, since the contents of the canonical and the cache normally
have the same directory structure, ellsync allows a subdirectory of
a stream to be synced:

    ellsync router.json /home/user/art/painting/ /media/user/External1/art/painting/

This is of course as long as it is the same subdirectory.  This will fail:

    ellsync router.json /home/user/art/painting/ /media/user/External1/art/sculpture/

And this can be combined with the short, name-the-stream syntax:

    ellsync router.json art:painting/

You might have a router you use almost always, in which case you might
want to establish an alias like

    alias myellsync ellsync $HOME/my-standard-router.json

(or whatever.)