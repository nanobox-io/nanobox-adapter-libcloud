import nanobox_libcloud
import unittest
import warnings


class NanoboxLibcloudTestCase(unittest.TestCase):

    def setUp(self):
        nanobox_libcloud.app.testing = True
        self.app = nanobox_libcloud.app.test_client()
        self.adapters = sorted(nanobox_libcloud.adapters.base.AdapterBase.registry.keys())
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
