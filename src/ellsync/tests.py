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
        router = {
            'basic': {
                'from': 'canonical',
                'to': 'cache',
            },
            'other': {
                'from': 'canonical2',
                'to': 'cache2',
            }
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

    def test_dry_run(self):
        main(['backup.json', 'syncdirs', 'canonical', 'cache'])
        self.assertFalse(os.path.exists('cache/thing'))
        output = sys.stdout.getvalue()
        self.assertEqual(output.split('\n')[0], 'rsync --dry-run --archive --verbose --delete "canonical/" "cache/"')
        self.assertIn('DRY RUN', output)

    def test_apply(self):
        main(['backup.json', 'syncdirs', 'canonical', 'cache', '--apply'])
        self.assertTrue(os.path.exists('cache/thing'))
        output = sys.stdout.getvalue()
        self.assertEqual(output.split('\n')[:4], [
            'rsync --archive --verbose --delete "canonical/" "cache/"',
            'sending incremental file list',
            'thing',
            ''
        ])

    def test_stream(self):
        main(['backup.json', 'sync', 'basic:', '--apply'])
        output = sys.stdout.getvalue()
        self.assertEqual(output.split('\n')[:4], [
            'rsync --archive --verbose --delete "canonical/" "cache/"',
            'sending incremental file list',
            'thing',
            ''
        ])

    def test_stream_not_exist(self):
        with self.assertRaises(ValueError) as ar:
            main(['backup.json', 'sync', 'other:', '--apply'])
        self.assertIn("Directory 'canonical2/' is not present", str(ar.exception))

    def test_rename(self):
        check_call("mkdir -p canonical/sclupture", shell=True)
        check_call("mkdir -p cache/sclupture", shell=True)
        main(['backup.json', 'rename', 'basic:', 'sclupture', 'sculpture'])
        self.assertTrue(os.path.exists('canonical/sculpture'))
        self.assertTrue(os.path.exists('cache/sculpture'))

    def test_rename_not_both_subdirs_exist(self):
        check_call("mkdir -p canonical/sclupture", shell=True)
        with self.assertRaises(OSError) as ar:
            main(['backup.json', 'rename', 'basic:', 'sclupture', 'sculpture'])
        self.assertIn('Errno 2', str(ar.exception))


if __name__ == '__main__':
    unittest.main()
