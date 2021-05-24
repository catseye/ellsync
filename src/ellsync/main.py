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
    for stream_name, stream in sorted(router.items()):
        if os.path.isdir(stream['from']) and os.path.isdir(stream['to']):
            if options.stream_name_only:
                print(stream_name)
            else:
                print("{}: {} => {}".format(stream_name, stream['from'], stream['to']))


def sync(router, options):
    for stream_name in options.stream_names:
        if ':' in stream_name:
            stream_name, subdir = stream_name.split(':')
        else:
            subdir = None
        stream = router[stream_name]
        from_dir = stream['from']
        to_dir = stream['to']
        if subdir:
            from_dir = os.path.join(from_dir, subdir)
            to_dir = os.path.join(to_dir, subdir)
        sync_directories(from_dir, to_dir, options)
    if options.apply:
        run_command('sync')


def sync_directories(from_dir, to_dir, options):
    from_dir = clean_dir(from_dir)
    to_dir = clean_dir(to_dir)

    for d in (from_dir, to_dir):
        if not os.path.isdir(d):
            raise ValueError("Directory '{}' is not present".format(d))

    dry_run = not options.apply
    dry_run_option = '--dry-run ' if dry_run else ''
    checksum_option = '--checksum ' if options.thorough else ''
    cmd = 'rsync {}{}--archive --verbose --delete "{}" "{}"'.format(dry_run_option, checksum_option, from_dir, to_dir)
    run_command(cmd)


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


# - - - - driver - - - -


def main(args):
    argparser = ArgumentParser()

    argparser.add_argument('router', metavar='ROUTER', type=str,
        help='JSON file containing the backup router description'
    )
    argparser.add_argument('--version', action='version', version="%(prog)s 0.5")

    subparsers = argparser.add_subparsers()

    # - - - - list - - - -
    parser_list = subparsers.add_parser('list', help='List available sync streams')
    parser_list.add_argument('--stream-name-only', default=False, action='store_true',
        help='Output only the names of the available streams'
    )
    parser_list.set_defaults(func=list_)

    # - - - - sync - - - -
    parser_sync = subparsers.add_parser('sync', help='Sync contents across one or more sync streams')
    parser_sync.add_argument('stream_names', metavar='STREAM', type=str, nargs='+',
        help='Name of stream (or stream:subdirectory) to sync contents across'
    )
    parser_sync.add_argument('--apply', default=False, action='store_true',
        help='Actually run the rsync command'
    )
    parser_sync.add_argument('--thorough', default=False, action='store_true',
        help='Ignore the timestamp on all destination files, to ensure content is synced'
    )
    parser_sync.set_defaults(func=sync)

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

    options = argparser.parse_args(args)
    with open(options.router, 'r') as f:
        router = json.loads(f.read())
    try:
        func = options.func
    except AttributeError:
        argparser.print_usage()
        sys.exit(1)
    func(router, options)
