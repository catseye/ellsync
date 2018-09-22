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
            "cache": "/home/user/art/",
            "canonical": "/media/user/External1/art/",
        }
    }

In this, `art` is the name of a "backup stream", in which files are
added, edited, and removed in `/media/user/External1/art/`
(called the *canonical depository*), and
periodically  `/home/user/art/` (called the *cache*) is synced to match it.

Either depository may be offline, therefore 
neither directory is assumed to exist
(the directory might not exist, if the volume is not mounted.)

With this router we can then say

    ellsync --router=router.json /home/user/art/ /media/user/External1/art/

and this will in effect run

    rsync --archive --verbose --delete /home/user/art/ /media/user/External1/art/

but if we try

    ellsync --router=router.json /media/user/External1/art/ /home/user/art/

we will be prevented, because it is an error, because the direction of
the backup stream is always from cache to canonical.

Various other configurations are prevented.
