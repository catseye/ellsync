`ellsync`
=========

_Version 0.2_
| _Entry_ [@ catseye.tc](https://catseye.tc/node/ellsync)
| _See also:_ [yastasoti](https://github.com/catseye/yastasoti)
∘ [tagfarm](https://github.com/catseye/tagfarm)
∘ [shelf](https://github.com/catseye/shelf)

- - - -

<img align="right" src="images/ellsync-logo.png?raw=true" />

**`ellsync`** is an opinionated poka-yoke for [`rsync`][].

*   [opinionated][]: it was designed for a particular use case for `rsync`
    (offline backups).
*   [poka-yoke][]: it exposes a restricted interface to `rsync`, which
    prevents using it in dangerous ways.

Because the restricted interface that `ellsync` presents can be accessed
by shorthand form, it also happens to provide some convenience over
using `rsync` directly — but its real purpose is to increase safety.
(I've been burned more than once when I've made a mistake using `rsync`.)

Quick start
-----------

Make sure you have Python (2.7 or 3.x) installed, clone this repository,
and put its `bin` directory on your executable search path.  You will
then be able to run `ellsync` from your terminal.

Usage guide
-----------

### Backup router

`ellsync`'s operation is based on a *backup router* which is a JSON file
that looks like this:

    {
        "art": {
            "from": "/media/user/External1/art/",
            "to": "/home/user/art/"
        }
    }

In this, `art` is the name of a _backup stream_, in which files in
`/media/user/External1/art/` (called the *canonical*) are periodically
synced to `/home/user/art/` (called the *cache*).

The idea is that all changes to the contents of the canonical directory
are bona fide changes, but any change to the contents of the cache can be
discarded.

### `syncdirs` command

With the above router saved as `router.json` we can then say

    ellsync router.json syncdirs /home/user/art/ /media/user/External1/art/

and this will in effect run

    rsync --archive --verbose --delete --dry-run /home/user/art/ /media/user/External1/art/

Note that by default it only runs a `--dry-run`.  It's a good practice to
do a dry run first, to see what will be changed.  As a bonus, the files
involved will often remain in the filesystem cache, meaning a subsequent
actual run will go quite quickly.  To do that actual run, use `--apply`:

    ellsync router.json syncdirs /home/user/art/ /media/user/External1/art/ --apply

Note that if we try

    ellsync router.json syncdirs /media/user/External1/art/ /home/user/art/

we will be prevented, because it is an error, because the direction of
the backup stream is always from canonical to cache.

Various other configurations are prevented.  You may have noticed that `rsync`
is sensitive about whether a directory name ends in a slash or not.  `ellsync`
detects when a trailing slash is missing and adds it.  Thus

    ellsync router.json syncdirs /media/user/External1/art /home/user/art/

is still interpreted as

    rsync --archive --verbose --delete /home/user/art/ /media/user/External1/art/

(but note that the directories in the router do need to have the
trailing slashes.)

Also, ince the contents of the canonical and the cache normally
have the same directory structure, `ellsync` allows specifying that
only a subdirectory of a stream is to be synced:

    ellsync router.json syncdirs /home/user/art/painting/ /media/user/External1/art/painting/

This is of course allowed only as long as it is the same subdirectory.
This will fail:

    ellsync router.json syncdirs /home/user/art/painting/ /media/user/External1/art/sculpture/

### `list` command

Either the canonical or the cache (or both) may be offline storage (removable
media), therefore neither directory is assumed to exist (it might not exist
if the volume is not mounted.)  If either of the directories does not exist,
`ellsync` will refuse to use this backup stream.  Based on this, there is a
subcommand to list which streams are, at the moment, backupable:

    ellsync router.json list

### `sync` command

Since each stream configuration is named in the router, we don't even have to
give these directory names.  We can use the `sync` command where we give
just the name of the stream, followed by a colon:

    ellsync router.json sync art:

The `sync` command syntax allows specifying that only a subdirectory of a
stream is to be synced, by giving the subdirectory name after the colon:

    ellsync router.json sync art:painting/

### `rename` command

Sometimes you want to rename a subdirectory somewhere under the canonical of
one of the streams.  It's completely fine to do this, but the next time it is synced,
`rsync` will treat it, in the cache, as the old subdirectory being deleted and
a new subdirectory being created.  If there are a large number of files in the
subdirectory, this delete-and-create sync can take a long time.  It's also not
obvious from `rsync`'s logging output that everything being deleted is also being
created somewhere else.

To ease this situation, `ellsync` has a `rename` command that works like so:

    ellsync router.json rename art: sclupture sculpture

This renames the `/media/user/External1/art/sclupture` directory to
`/media/user/External1/art/sculpture` and *also* renames the `/home/user/art/sclupture`
directory to `/home/user/art/sculpture`.  If the contents of the source and
destination directories were in sync before this rename occurred, they will
continue to be in sync after the rename happens.

Hints and Tips
--------------

You might have a router you use almost always, in which case you might
want to establish an alias like

    alias myellsync ellsync $HOME/my-standard-router.json

(or whatever.)

Notes
-----

If `rsync` encounters an error, it will abort, having only partially completed.
In particular, if it encounters a directory which it cannot read, because it
is for example owned by another user and not world-readable, it will abort.
`ellsync` does not currently detect this properly (if it is detectable (I hope
that it is!))

History
-------

### 0.2

Every `ellsync` functionality has an explicit subcommand (`list` and `sync` to
start.)

`sync` was split into `sync` (takes a stream) and `syncdirs` (takes to and
from dirs).

Added `rename` command.

### 0.1

Initial release.

[`rsync`]: https://rsync.samba.org/
[opinionated]: https://softwareengineering.stackexchange.com/questions/12182/what-does-opinionated-software-really-mean
[poka-yoke]: https://en.wikipedia.org/wiki/Poka-yoke
