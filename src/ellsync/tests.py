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
        sys.stdout = StringIO()
        self.maxDiff = None
        check_call("rm -rf canonical cache", shell=True)
        check_call("mkdir -p canonical", shell=True)
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
        sys.stdout = self.saved_stdout
        super(TestEllsync, self).tearDown()

    def test_failure(self):
        with self.assertRaises(SystemExit):
            main(['backup.json'])

    def test_basic(self):
        main(['backup.json', 'canonical', 'cache'])


if __name__ == '__main__':
    unittest.main()
