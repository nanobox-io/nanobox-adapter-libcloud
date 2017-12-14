import nanobox_libcloud
from tests import NanoboxLibcloudTestCase


class MetaControllerTestCase(NanoboxLibcloudTestCase):
    def test_overview(self):
        with self.app as c:
            rv = c.get('/')
            self.assertEqual(200, rv.status_code)
            self.assertIn(b'This is the libcloud meta-adapter for Nanobox.', rv.data)

    def test_docs(self):
        with self.app as c:
            rv = c.get('/docs')
            self.assertEqual(200, rv.status_code)
            self.assertIn(b'Swagger UI', rv.data)

            for adapter in self.adapters:
                with self.subTest(adapter=adapter):
                    self.assertIn(bytes('static/%s.json' % (adapter), encoding='utf-8'), rv.data)

    def test_usage(self):
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

    def test_adapter_docs(self):
        with self.app as c:
            for adapter in self.adapters:
                with self.subTest(adapter=adapter):
                    rv = c.get('/%s/docs' % (adapter))
                    self.assertEqual(200, rv.status_code)
                    self.assertIn(b'Swagger UI', rv.data)
                    self.assertIn(bytes('static/%s.json' % (adapter), encoding='utf-8'), rv.data)

    def test_meta(self):
        with self.app as c:
            with self.subTest(adapter='nonexistent-adapter'):
                rv = c.get('/nonexistent-adapter/meta')
                self.assertEqual(501, rv.status_code)
                self.assertIn(b"That adapter doesn't (yet) exist.", rv.data)

            for adapter in self.adapters:
                with self.subTest(adapter=adapter):
                    rv = c.get('/%s/meta' % (adapter))
                    self.assertEqual(200, rv.status_code)

    def test_catalog(self):
        with self.app as c:
            with self.subTest(adapter='nonexistent-adapter'):
                rv = c.get('/nonexistent-adapter/catalog')
                self.assertEqual(501, rv.status_code)
                self.assertIn(b"That adapter doesn't (yet) exist.", rv.data)

            for adapter in self.adapters:
                with self.subTest(adapter=adapter):
                    rv = c.get('/%s/catalog' % (adapter))
                    with self.subTest(step='code'):
                        self.assertEqual(200, rv.status_code)
                    with self.subTest(step='data'):
                        self.assertIn(b'"specs":', rv.data)

    def test_verify(self):
        with self.app as c:
            with self.subTest(adapter='nonexistent-adapter'):
                rv = c.post('/nonexistent-adapter/verify')
                self.assertEqual(501, rv.status_code)
                self.assertIn(b"That adapter doesn't (yet) exist.", rv.data)

            for adapter in self.adapters:
                with self.subTest(adapter=adapter):
                    rv = c.post('/%s/verify' % (adapter))
                    self.assertEqual(401, rv.status_code)
