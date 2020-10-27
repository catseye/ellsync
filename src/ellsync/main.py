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
    run_command(cmd)
    if not dry_run:
        run_command('sync')


def run_command(cmd):
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


def list_(router, options):
    for stream_name, stream in router.items():
        if os.path.isdir(stream['from']) and os.path.isdir(stream['to']):
            if options.stream_name_only:
                print(stream_name)
            else:
                print("{}: {} => {}".format(stream_name, stream['from'], stream['to']))


def sync(router, options):
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

    if options.thorough and options.apply:
        cmd = 'find "{}" -exec touch --date "1970-01-01" {} \;'.format(to_dir, '{}')
        run_command(cmd)

    perform_sync(from_dir, to_dir, dry_run=(not options.apply))


def syncdirs(router, options):
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

    if options.thorough and options.apply:
        cmd = 'find "{}" -exec touch --date "1970-01-01" {} \;'.format(to_dir, '{}')
        run_command(cmd)

    perform_sync(from_dir, to_dir, dry_run=(not options.apply))


def rename(router, options):
    stream_name = options.stream_name
    if ':' in stream_name:
        stream_name, subdir = options.stream_name.split(':')
        assert subdir == ''

    stream = router[stream_name]
    from_dir = stream['from']
    to_dir = stream['to']

    existing_subdir_a = clean_dir(os.path.join(from_dir, options.existing_subdir_name))
    new_subdir_a = clean_dir(os.path.join(from_dir, options.new_subdir_name))

    if not os.path.isdir(existing_subdir_a):
        raise ValueError("Directory '{}' is not present".format(existing_subdir_a))
    if os.path.isdir(new_subdir_a):
        raise ValueError("Directory '{}' already exists".format(new_subdir_a))

    existing_subdir_b = clean_dir(os.path.join(to_dir, options.existing_subdir_name))
    new_subdir_b = clean_dir(os.path.join(to_dir, options.new_subdir_name))

    if not os.path.isdir(existing_subdir_b):
        raise ValueError("Directory '{}' is not present".format(existing_subdir_b))
    if os.path.isdir(new_subdir_b):
        raise ValueError("Directory '{}' already exists".format(new_subdir_b))

    print("Renaming {} to {}".format(existing_subdir_a, new_subdir_a))
    os.rename(existing_subdir_a, new_subdir_a)
    print("Renaming {} to {}".format(existing_subdir_b, new_subdir_b))
    os.rename(existing_subdir_b, new_subdir_b)


def deepcheck(router, options):
    stream_name = options.stream_name

    stream = router[stream_name]
    from_dir = stream['from']
    to_dir = stream['to']

    cmd = 'diff -ruq "{}" "{}"'.format(from_dir, to_dir)
    run_command(cmd)

    # TODO: run `touch --date "1970-01-01"` on all files downstream where there were differences


# - - - - driver - - - -


def main(args):
    argparser = ArgumentParser()

    argparser.add_argument('router', metavar='ROUTER', type=str,
        help='JSON file containing the backup router description'
    )
    argparser.add_argument('--version', action='version', version="%(prog)s 0.3")

    subparsers = argparser.add_subparsers()

    # - - - - list - - - -
    parser_list = subparsers.add_parser('list', help='List available sync streams')
    parser_list.add_argument('--stream-name-only', default=False, action='store_true',
        help='Output only the names of the available streams'
    )
    parser_list.set_defaults(func=list_)

    # - - - - sync - - - -
    parser_sync = subparsers.add_parser('sync', help='Sync contents across a sync stream specified by name')
    parser_sync.add_argument('stream_name', metavar='STREAM', type=str,
        help='Name of stream (or stream:subdirectory) to sync contents across'
    )
    parser_sync.add_argument('--apply', default=False, action='store_true',
        help='Actually run the rsync command'
    )
    parser_sync.add_argument('--thorough', default=False, action='store_true',
        help='Invalidate the timestamp on all destination files, to ensure content is synced'
    )
    parser_sync.set_defaults(func=sync)

    # - - - - syncdirs - - - -
    parser_syncdirs = subparsers.add_parser(
        'syncdirs', help='Sync contents across a sync stream specified by source and dest directories'
    )
    parser_syncdirs.add_argument('from_dir', metavar='FROM_DIR', type=str,
        help='Canonical directory to sync contents from'
    )
    parser_syncdirs.add_argument('to_dir', metavar='TO_DIR', type=str,
        help='Cache directory to sync contents to'
    )
    parser_syncdirs.add_argument('--apply', default=False, action='store_true',
        help='Actually run the rsync command'
    )
    parser_syncdirs.add_argument('--thorough', default=False, action='store_true',
        help='Invalidate the timestamp on all destination files, to ensure content is synced'
    )
    parser_syncdirs.set_defaults(func=syncdirs)

    # - - - - rename - - - -
    parser_rename = subparsers.add_parser(
        'rename', help='Rename a subdirectory in both source and dest of sync stream'
    )
    parser_rename.add_argument('stream_name', metavar='STREAM', type=str,
        help='Name of stream to operate under'
    )
    parser_rename.add_argument('existing_subdir_name', metavar='DIRNAME', type=str,
        help='Existing subdirectory to be renamed'
    )
    parser_rename.add_argument('new_subdir_name', metavar='DIRNAME', type=str,
        help='New name for subdirectory'
    )
    parser_rename.set_defaults(func=rename)

    # - - - - deepcheck - - - -
    parser_deepcheck = subparsers.add_parser(
        'deepcheck', help='Report files that are not byte-for-byte identical'
    )
    parser_deepcheck.add_argument('stream_name', metavar='STREAM', type=str,
        help='Name of stream to operate under'
    )
    parser_deepcheck.set_defaults(func=deepcheck)

    options = argparser.parse_args(args)
    with open(options.router, 'r') as f:
        router = json.loads(f.read())
    try:
        func = options.func
    except AttributeError:
        argparser.print_usage()
        sys.exit(1)
    func(router, options)
