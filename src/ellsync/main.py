from argparse import ArgumentParser
import json
import os
import sys
from subprocess import Popen, STDOUT, PIPE


def clean_dir(dirname):
    if not dirname.endswith('/'):
        dirname += '/'
    return dirname


def main(args):

    argparser = ArgumentParser()
    
    argparser.add_argument('router', metavar='ROUTER', type=str,
        help='JSON file containing the backup router description'
    )
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

    with open(options.router, 'r') as f:
        router = json.loads(f.read())

    if options.to_dir is None:
        if ':' in options.from_dir:
            stream_name, subdir = options.from_dir.split(':')
        else:
            command = options.from_dir
            if command == 'list':
                for stream_name, stream in router.items():
                    if os.path.isdir(stream['from']) and os.path.isdir(stream['to']):
                        print("{}: {} => {}".format(stream_name, stream['from'], stream['to']))
                sys.exit(0)
            else:
                raise NotImplementedError("Arg must be stream:subdir or command; command must be one of: list")
        stream = router[stream_name]
        from_dir = stream['from']
        to_dir = stream['to']
        if subdir:
            from_dir = clean_dir(os.path.join(from_dir, subdir))
            to_dir = clean_dir(os.path.join(to_dir, subdir))
    else:
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

    for d in (from_dir, to_dir):
        if not os.path.isdir(d):
            raise ValueError("Directory '{}' is not present".format(d))
    rsync_options = '--dry-run ' if (not options.apply) else ''
    cmd = 'rsync {}--archive --verbose --delete "{}" "{}"'.format(rsync_options, from_dir, to_dir)
    sys.stdout.write(cmd + '\n')
    try:
        p = Popen(cmd, shell=True, stderr=STDOUT, stdout=PIPE, encoding='utf-8')
    except TypeError:
        # python 2.x
        p = Popen(cmd, shell=True, stderr=STDOUT, stdout=PIPE)
    pipe = p.stdout
    for line in p.stdout:
        sys.stdout.write(line.decode('utf-8'))
        sys.stdout.flush()
    p.wait()
