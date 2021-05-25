import json
import os
import sys
from tempfile import mkdtemp
import unittest
from subprocess import check_call

try:
    from StringIO import StringIO
except ImportError:
    from io import StringIO
assert StringIO

from ellsync.main import main


class TestEllsync(unittest.TestCase):

    def setUp(self):
        super(TestEllsync, self).setUp()
        self.saved_stdout = sys.stdout
        self.saved_stderr = sys.stderr
        sys.stdout = StringIO()
        sys.stderr = StringIO()
        self.maxDiff = None
        self.dirname = mkdtemp()
        self.prevdir = os.getcwd()
        os.chdir(self.dirname)
        check_call("mkdir -p canonical", shell=True)
        check_call("touch canonical/thing", shell=True)
        check_call("mkdir -p cache", shell=True)
        check_call("mkdir -p canonical3", shell=True)
        check_call("mkdir -p cache3", shell=True)
        router = {
            'basic': {
                'from': 'canonical',
                'to': 'cache',
            },
            'notfound': {
                'from': 'canonical2',
                'to': 'cache2',
            },
            'other': {
                'from': 'canonical3',
                'to': 'cache3',
            },
        }
        with open('backup.json', 'w') as f:
            f.write(json.dumps(router))

    def tearDown(self):
        os.chdir(self.prevdir)
        check_call("rm -rf {}".format(self.dirname), shell=True)
        sys.stdout = self.saved_stdout
        sys.stderr = self.saved_stderr
        super(TestEllsync, self).tearDown()

    def test_failure(self):
        with self.assertRaises(SystemExit):
            main(['backup.json'])

    def test_list(self):
        main(['backup.json', 'list'])
        output = sys.stdout.getvalue()
        self.assertEqual(output.split('\n'), [
            'basic: canonical => cache',
            'other: canonical3 => cache3',
            '',
        ])

    def test_sync_dry_run(self):
        main(['backup.json', 'sync', 'basic:'])
        self.assertFalse(os.path.exists('cache/thing'))
        output = sys.stdout.getvalue()
        self.assertEqual(output.split('\n')[0], 'rsync --dry-run --archive --verbose --delete canonical/ cache/')
        self.assertIn('DRY RUN', output)

    def test_sync_apply(self):
        main(['backup.json', 'sync', 'basic:', '--apply'])
        self.assertTrue(os.path.exists('cache/thing'))
        output = sys.stdout.getvalue()
        self.assertEqual(output.split('\n')[:4], [
            'rsync --archive --verbose --delete canonical/ cache/',
            'sending incremental file list',
            'thing',
            ''
        ])

    def test_sync_subdirectory(self):
        check_call("mkdir -p canonical/subdir", shell=True)
        check_call("mkdir -p cache/subdir", shell=True)
        check_call("touch canonical/subdir/stuff", shell=True)
        main(['backup.json', 'sync', 'basic:subdir', '--apply'])
        self.assertTrue(os.path.exists('cache/subdir/stuff'))
        self.assertFalse(os.path.exists('cache/thing'))
        output = sys.stdout.getvalue()
        self.assertEqual(output.split('\n')[:4], [
            'rsync --archive --verbose --delete canonical/subdir/ cache/subdir/',
            'sending incremental file list',
            'stuff',
            ''
        ])

    def test_sync_stream_does_not_exist(self):
        with self.assertRaises(ValueError) as ar:
            main(['backup.json', 'sync', 'notfound', '--apply'])
        self.assertIn("Directory 'canonical2/' is not present", str(ar.exception))

    def test_sync_multiple_streams(self):
        main(['backup.json', 'sync', 'other', 'basic'])
        output = sys.stdout.getvalue()
        lines = [l for l in output.split('\n') if l.startswith('rsync')]
        self.assertEqual(lines, [
            'rsync --dry-run --archive --verbose --delete canonical3/ cache3/',
            'rsync --dry-run --archive --verbose --delete canonical/ cache/',
        ])

    def test_sync_thorough(self):
        main(['backup.json', 'sync', 'basic', '--thorough'])
        output = sys.stdout.getvalue()
        lines = [l for l in output.split('\n') if l.startswith('rsync')]
        self.assertEqual(lines, [
            'rsync --dry-run --checksum --archive --verbose --delete canonical/ cache/',
        ])

    def test_sync_with_spaces_in_dirnames(self):
        check_call("mkdir -p 'can onical'", shell=True)
        check_call("mkdir -p 'ca che'", shell=True)
        router = {
            'spaced': {
                'from': 'can onical',
                'to': 'ca che',
            },
        }
        with open('backup.json', 'w') as f:
            f.write(json.dumps(router))
        main(['backup.json', 'sync', 'spaced'])
        output = sys.stdout.getvalue()
        lines = [l for l in output.split('\n') if l.startswith('rsync')]
        self.assertEqual(lines, [
            'rsync --dry-run --archive --verbose --delete "can onical/" "ca che/"',
        ])

    def test_rename(self):
        check_call("mkdir -p canonical/sclupture", shell=True)
        check_call("mkdir -p cache/sclupture", shell=True)
        main(['backup.json', 'rename', 'basic:', 'sclupture', 'sculpture'])
        self.assertTrue(os.path.exists('canonical/sculpture'))
        self.assertTrue(os.path.exists('cache/sculpture'))

    def test_rename_not_both_subdirs_exist(self):
        check_call("mkdir -p canonical/sclupture", shell=True)
        with self.assertRaises(ValueError) as ar:
            main(['backup.json', 'rename', 'basic:', 'sclupture', 'sculpture'])
        self.assertIn("Directory 'cache/sclupture/' is not present", str(ar.exception))
        self.assertFalse(os.path.exists('canonical/sculpture'))

    def test_rename_new_subdir_already_exists(self):
        check_call("mkdir -p canonical/sclupture", shell=True)
        check_call("mkdir -p canonical/sculpture", shell=True)
        check_call("mkdir -p cache/sclupture", shell=True)
        with self.assertRaises(ValueError) as ar:
            main(['backup.json', 'rename', 'basic:', 'sclupture', 'sculpture'])
        self.assertIn("Directory 'canonical/sculpture/' already exists", str(ar.exception))
        self.assertFalse(os.path.exists('cache/sculpture'))


if __name__ == '__main__':
    unittest.main()
