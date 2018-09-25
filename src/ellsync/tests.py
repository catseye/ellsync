import json
import os
import sys
from StringIO import StringIO
import unittest
from subprocess import check_call

from ellsync.main import main


class TestEllsync(unittest.TestCase):

    def setUp(self):
        super(TestEllsync, self).setUp()
        self.saved_stdout = sys.stdout
        self.saved_stderr = sys.stderr
        sys.stdout = StringIO()
        sys.stderr = StringIO()
        self.maxDiff = None
        check_call("rm -rf canonical cache", shell=True)
        check_call("mkdir -p canonical", shell=True)
        check_call("touch canonical/thing", shell=True)
        check_call("mkdir -p cache", shell=True)
        router = {
            'basic': {
                'from': 'canonical',
                'to': 'cache',
            }
        }
        with open('backup.json', 'w') as f:
            f.write(json.dumps(router))

    def tearDown(self):
        check_call("rm -rf canonical cache", shell=True)
        sys.stdout = self.saved_stdout
        sys.stderr = self.saved_stderr
        super(TestEllsync, self).tearDown()

    def test_failure(self):
        with self.assertRaises(SystemExit):
            main(['backup.json'])

    def test_dry_run(self):
        main(['backup.json', 'canonical', 'cache'])
        self.assertFalse(os.path.exists('cache/thing'))
        output = sys.stdout.getvalue()
        self.assertEqual(output, 'rsync --archive --verbose --delete canonical/ cache/\n')

    def test_apply(self):
        main(['backup.json', 'canonical', 'cache', '--apply'])
        self.assertTrue(os.path.exists('cache/thing'))


if __name__ == '__main__':
    unittest.main()
