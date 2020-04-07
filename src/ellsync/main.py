from argparse import ArgumentParser
import json
import os
import sys
from subprocess import Popen, STDOUT, PIPE


# - - - - utilities - - - -


def clean_dir(dirname):
    if not dirname.endswith('/'):
        dirname += '/'
    return dirname


def perform_sync(from_dir, to_dir, dry_run=True):
    for d in (from_dir, to_dir):
        if not os.path.isdir(d):
            raise ValueError("Directory '{}' is not present".format(d))
    rsync_options = '--dry-run ' if dry_run else ''
    cmd = 'rsync {}--archive --verbose --delete "{}" "{}"'.format(rsync_options, from_dir, to_dir)
    sys.stdout.write(cmd + '\n')
    try:
        p = Popen(cmd, shell=True, stderr=STDOUT, stdout=PIPE, encoding='utf-8')
        decode_line = lambda line: line
    except TypeError:
        # python 2.x
        p = Popen(cmd, shell=True, stderr=STDOUT, stdout=PIPE)
        decode_line = lambda line: line.decode('utf-8')
    pipe = p.stdout
    for line in p.stdout:
        sys.stdout.write(decode_line(line))
        sys.stdout.flush()
    p.wait()


# - - - - commands - - - -


def list_(router, args):
    for stream_name, stream in router.items():
        if os.path.isdir(stream['from']) and os.path.isdir(stream['to']):
            print("{}: {} => {}".format(stream_name, stream['from'], stream['to']))


def sync(router, args):
    argparser = ArgumentParser()
    argparser.add_argument('stream_name', metavar='STREAM', type=str,
        help='Name of stream (or stream:subdirectory) to sync contents across'
    )
    argparser.add_argument('--apply', default=False, action='store_true',
        help='Actually run the rsync command'
    )
    options = argparser.parse_args(args)

    if ':' in options.stream_name:
        stream_name, subdir = options.stream_name.split(':')
    else:
        raise NotImplementedError("Arg must be stream:subdir")
    stream = router[stream_name]
    from_dir = stream['from']
    to_dir = stream['to']
    if subdir:
        from_dir = os.path.join(from_dir, subdir)
        to_dir = os.path.join(to_dir, subdir)

    from_dir = clean_dir(from_dir)
    to_dir = clean_dir(to_dir)

    perform_sync(from_dir, to_dir, dry_run=(not options.apply))


def syncdirs(router, args):
    argparser = ArgumentParser()
    argparser.add_argument('from_dir', metavar='FROM_DIR', type=str,
        help='Canonical directory to sync contents from, or name of stream to use'
    )
    argparser.add_argument('to_dir', metavar='TO_DIR', nargs='?', default=None, type=str,
        help='Cache directory to sync contents to (only required when canonical dir, '
        'not stream, was specified)'
    )
    argparser.add_argument('--apply', default=False, action='store_true',
        help='Actually run the rsync command'
    )
    options = argparser.parse_args(args)

    from_dir = clean_dir(options.from_dir)
    to_dir = clean_dir(options.to_dir)
    selected_stream_name = None
    for stream_name, stream in router.items():
        if from_dir.startswith(stream['from']) and to_dir.startswith(stream['to']):
            from_suffix = from_dir[len(stream['from']):]
            to_suffix = to_dir[len(stream['to']):]
            if from_suffix != to_suffix:
                raise ValueError( (from_suffix, to_suffix) )
            selected_stream_name = stream_name
            break
    if selected_stream_name is None:
        raise ValueError("Stream {} => {} was not found in router".format(from_dir, to_dir))

    perform_sync(from_dir, to_dir, dry_run=(not options.apply))


def rename(router, args):
    argparser = ArgumentParser()
    argparser.add_argument('stream_name', metavar='STREAM', type=str,
        help='Name of stream to operate under'
    )
    argparser.add_argument('existing_subdir_name', metavar='DIRNAME', type=str,
        help='Existing subdirectory to be renamed'
    )
    argparser.add_argument('new_subdir_name', metavar='DIRNAME', type=str,
        help='New name for subdirectory'
    )
    options = argparser.parse_args(args)

    stream_name = options.stream_name
    if ':' in stream_name:
        stream_name, subdir = options.stream_name.split(':')
        assert subdir == ''

    stream = router[stream_name]
    from_dir = stream['from']
    to_dir = stream['to']

    existing_subdir_a = clean_dir(os.path.join(from_dir, options.existing_subdir_name))
    new_subdir_a = clean_dir(os.path.join(from_dir, options.new_subdir_name))

    print("Renaming {} to {}".format(existing_subdir_a, new_subdir_a))
    os.rename(existing_subdir_a, new_subdir_a)

    existing_subdir_b = clean_dir(os.path.join(to_dir, options.existing_subdir_name))
    new_subdir_b = clean_dir(os.path.join(to_dir, options.new_subdir_name))

    print("Renaming {} to {}".format(existing_subdir_b, new_subdir_b))
    os.rename(existing_subdir_b, new_subdir_b)


# - - - - driver - - - -


def main(args):
    argparser = ArgumentParser()

    argparser.add_argument('router', metavar='ROUTER', type=str,
        help='JSON file containing the backup router description'
    )
    argparser.add_argument('command', metavar='COMMAND', type=str,
        help='The action to take. One of: list, sync, syncdirs, rename'
    )

    options, remaining_args = argparser.parse_known_args(args)

    with open(options.router, 'r') as f:
        router = json.loads(f.read())

    if options.command == 'list':
        list_(router, remaining_args)
    elif options.command == 'sync':
        sync(router, remaining_args)
    elif options.command == 'syncdirs':
        syncdirs(router, remaining_args)
    elif options.command == 'rename':
        rename(router, remaining_args)
    else:
        argparser.print_usage()
        sys.exit(1)
