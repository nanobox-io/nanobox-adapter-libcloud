import nanobox_libcloud
from tests import NanoboxLibcloudTestCase


class KeysControllerTestCase(NanoboxLibcloudTestCase):
    def test_key_create(self):
        with self.app as c:
            with self.subTest(adapter='nonexistent-adapter'):
                rv = c.post('/nonexistent-adapter/keys')
                self.assertEqual(501, rv.status_code)
                self.assertIn(b"That adapter doesn't (yet) exist.", rv.data)

            for adapter in self.adapters:
                with self.subTest(adapter=adapter):
                    rv = c.post('/%s/keys' % (adapter))
                    self.assertEqual(401, rv.status_code)

    def test_key_query(self):
        with self.app as c:
            with self.subTest(adapter='nonexistent-adapter'):
                rv = c.get('/nonexistent-adapter/keys/test')
                self.assertEqual(501, rv.status_code)
                self.assertIn(b"That adapter doesn't (yet) exist.", rv.data)

            for adapter in self.adapters:
                with self.subTest(adapter=adapter):
                    rv = c.get('/%s/keys/test' % (adapter))
                    self.assertEqual(401, rv.status_code)

    def test_key_delete(self):
        with self.app as c:
            with self.subTest(adapter='nonexistent-adapter'):
                rv = c.delete('/nonexistent-adapter/keys/test')
                self.assertEqual(501, rv.status_code)
                self.assertIn(b"That adapter doesn't (yet) exist.", rv.data)

            for adapter in self.adapters:
                with self.subTest(adapter=adapter):
                    rv = c.delete('/%s/keys/test' % (adapter))
                    self.assertEqual(401, rv.status_code)
