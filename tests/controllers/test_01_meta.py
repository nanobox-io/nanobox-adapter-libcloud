import nanobox_libcloud
from tests import NanoboxLibcloudTestCase


class MetaControllerTestCase(NanoboxLibcloudTestCase):
    def test_01_overview(self):
        with self.app as c:
            rv = c.get('/')
            self.assertEqual(200, rv.status_code)
            self.assertIn(b'This is the libcloud meta-adapter for Nanobox.', rv.data)

    def test_02_docs(self):
        with self.app as c:
            rv = c.get('/docs')
            self.assertEqual(200, rv.status_code)
            self.assertIn(b'Swagger UI', rv.data)

            for adapter in self.adapters:
                with self.subTest(adapter=adapter):
                    self.assertIn(bytes('static/%s.json' % (adapter), encoding='utf-8'), rv.data)

    def test_03_usage(self):
        with self.app as c:
            with self.subTest(adapter='nonexistent-adapter'):
                rv = c.get('/nonexistent-adapter')
                self.assertEqual(501, rv.status_code)
                self.assertIn(b"That adapter doesn't (yet) exist.", rv.data)

            for adapter in self.adapters:
                with self.subTest(adapter=adapter):
                    rv = c.get('/%s' % (adapter))
                    self.assertEqual(200, rv.status_code)
                    self.assertIn(bytes('This is the libcloud-powered Nanobox adapter for %s.' % (nanobox_libcloud.adapters.get_adapter(adapter).name), encoding='utf-8'), rv.data)

    def test_04_adapter_docs(self):
        with self.app as c:
            for adapter in self.adapters:
                with self.subTest(adapter=adapter):
                    rv = c.get('/%s/docs' % (adapter))
                    self.assertEqual(200, rv.status_code)
                    self.assertIn(b'Swagger UI', rv.data)
                    self.assertIn(bytes('static/%s.json' % (adapter), encoding='utf-8'), rv.data)

    def test_05_meta(self):
        with self.app as c:
            with self.subTest(adapter='nonexistent-adapter'):
                rv = c.get('/nonexistent-adapter/meta')
                self.assertEqual(501, rv.status_code)
                self.assertIn(b"That adapter doesn't (yet) exist.", rv.data)

            for adapter in self.adapters:
                with self.subTest(adapter=adapter):
                    rv = c.get('/%s/meta' % (adapter))
                    self.assertEqual(200, rv.status_code)

    def test_06_catalog(self):
        with self.app as c:
            with self.subTest(adapter='nonexistent-adapter'):
                rv = c.get('/nonexistent-adapter/catalog')
                self.assertEqual(501, rv.status_code)
                self.assertIn(b"That adapter doesn't (yet) exist.", rv.data)

            for adapter in self.adapters:
                with self.subTest(adapter=adapter):
                    rv = c.get('/%s/catalog' % (adapter))
                    with self.subTest(check='code'):
                        self.assertEqual(200, rv.status_code)
                    with self.subTest(check='data'):
                        self.assertIn(b'"specs":', rv.data)

    def test_07_verify(self):
        with self.app as c:
            with self.subTest(adapter='nonexistent-adapter'):
                rv = c.post('/nonexistent-adapter/verify')
                self.assertEqual(501, rv.status_code)
                self.assertIn(b"That adapter doesn't (yet) exist.", rv.data)

            for adapter in self.adapters:
                with self.subTest(adapter=adapter):
                    with self.subTest(step='no-creds'):
                        rv = c.post('/%s/verify' % (adapter))
                        self.assertEqual(401, rv.status_code)
                    with self.subTest(step='with-creds'):
                        rv = c.post('/%s/verify' % (adapter),
                            headers=self.creds.get(adapter, {}))
                        self.assertEqual(200, rv.status_code)
