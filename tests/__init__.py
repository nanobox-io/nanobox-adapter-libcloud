import nanobox_libcloud
import os
import unittest
import warnings

from flask import json


class NanoboxLibcloudTestCase(unittest.TestCase):

    def setUp(self):
        nanobox_libcloud.app.testing = True
        self.app = nanobox_libcloud.app.test_client()

        with open(os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            'cred_evars.json'
        )) as fp:
            content = fp.read()
        creds = json.loads(content)
        self.adapters = sorted(nanobox_libcloud.adapters.base.AdapterBase.registry.keys())
        self.creds = {adapter: {
            header: os.getenv(evar, '').replace('\n', '\\n')
            for header, evar in creds.get(adapter, {}).items()
        } for adapter in self.adapters}

        with open(os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            'id_rsa.pub'
        )) as fp:
            self.test_key = fp.read()

        with nanobox_libcloud.app.app_context():
            warnings.simplefilter("ignore", ResourceWarning)
            pass

    def tearDown(self):
        pass


if __name__ == '__main__':
    unittest.defaultTestLoader.loadTestsFromModule('tests.controllers')
    unittest.defaultTestLoader.loadTestsFromModule('tests.adapters')
    unittest.defaultTestLoader.loadTestsFromModule('tests.tasks')
    unittest.main()
