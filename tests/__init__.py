import libcloud
import nanobox_libcloud
import os
import unittest
import warnings

from flask import json


class NanoboxLibcloudTestCase(unittest.TestCase):
    adapters = None
    creds = None
    patches = []
    skip_adapters = ['azure']
    test_key = None

    def setUp(self):
        nanobox_libcloud.app.testing = True
        self.app = nanobox_libcloud.app.test_client()

        if not self.adapters or not self.creds:
            with open(os.path.join(
                os.path.dirname(os.path.abspath(__file__)),
                'cred_evars.json'
            )) as fp:
                creds = json.loads(fp.read())

            self.adapters = sorted(nanobox_libcloud.adapters.base.AdapterBase.registry.keys())
            for a in self.skip_adapters:
                self.adapters.remove(a)

            self.creds = {adapter: {
                header: os.getenv(evar, '').replace('\n', '\\n')
                for header, evar in creds.get(adapter, {}).items()
            } for adapter in self.adapters}

        if not self.test_key:
            with open(os.path.join(
                os.path.dirname(os.path.abspath(__file__)),
                'id_rsa.pub'
            )) as fp:
                self.test_key = fp.read()

        with nanobox_libcloud.app.app_context():
            warnings.simplefilter("ignore", ResourceWarning)
            pass

    def tearDown(self):
        for path, original in self.patches:
            exec('%s = original' % path)

        self.patches = []

    def patch(self, original, mock):
        path = '%s.%s' % (original.__module__, original.__qualname__)
        self.patches.append((path, original))
        exec('%s = mock' % path)
        # original = mock


if __name__ == '__main__':
    unittest.defaultTestLoader.loadTestsFromModule('tests.utils')
    unittest.defaultTestLoader.loadTestsFromModule('tests.adapters')
    unittest.defaultTestLoader.loadTestsFromModule('tests.tasks')
    unittest.defaultTestLoader.loadTestsFromModule('tests.controllers')
    unittest.main()
