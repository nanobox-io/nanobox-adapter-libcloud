import nanobox_libcloud

from flask import json
from tests import NanoboxLibcloudTestCase


class KeysControllerTestCase(NanoboxLibcloudTestCase):
    ids = {}

    def test_01_key_create(self):
        with self.app as c:
            with self.subTest(adapter='nonexistent-adapter'):
                rv = c.post('/nonexistent-adapter/keys')
                self.assertEqual(501, rv.status_code)
                self.assertIn(b"That adapter doesn't (yet) exist.", rv.data)

            for adapter in self.adapters:
                with self.subTest(adapter=adapter):

                    with self.subTest(step='no-creds'):
                        rv = c.post('/%s/keys' % (adapter))
                        self.assertEqual(401, rv.status_code)

                    with self.subTest(step='with-creds-no-data'):
                        rv = c.post('/%s/keys' % (adapter),
                            # content_type='application/json',
                            headers=self.creds.get(adapter, {}))
                        if nanobox_libcloud.adapters.get_adapter(adapter).\
                                server_ssh_key_method == 'reference':
                            with self.subTest(check='code'):
                                self.assertEqual(400, rv.status_code)
                            with self.subTest(check='data'):
                                self.assertIn(b"\'id\'", rv.data)
                        else:
                            self.assertEqual(501, rv.status_code)

                    with self.subTest(step='with-creds-and-data'):
                        rv = c.post('/%s/keys' % (adapter), data=json.dumps({
                                "id": "test",
                                "key": self.test_key
                            }), content_type='application/json',
                            headers=self.creds.get(adapter, {}))
                        if nanobox_libcloud.adapters.get_adapter(adapter).\
                                server_ssh_key_method == 'reference':
                            with self.subTest(check='code'):
                                self.assertEqual(201, rv.status_code)
                            with self.subTest(check='data'):
                                self.assertIn(b'"id":', rv.data)
                            if b'"id":' in rv.data:
                                self.ids[adapter] = json.loads(rv.data).get('id')
                        else:
                            self.assertEqual(501, rv.status_code)

    def test_02_key_query(self):
        with self.app as c:
            with self.subTest(adapter='nonexistent-adapter'):
                rv = c.get('/nonexistent-adapter/keys/test')
                self.assertEqual(501, rv.status_code)
                self.assertIn(b"That adapter doesn't (yet) exist.", rv.data)

            for adapter in self.adapters:
                with self.subTest(adapter=adapter):

                    with self.subTest(step='no-creds'):
                        rv = c.get('/%s/keys/%s' % (adapter, self.ids.get(adapter, 'test')))
                        self.assertEqual(401, rv.status_code)

                    with self.subTest(step='with-creds'):
                        rv = c.get('/%s/keys/%s' % (adapter, self.ids.get(adapter, 'test')),
                            headers=self.creds.get(adapter, {}))
                        if nanobox_libcloud.adapters.get_adapter(adapter).\
                                server_ssh_key_method == 'reference':
                            self.assertEqual(201, rv.status_code)
                        else:
                            self.assertEqual(501, rv.status_code)

    def test_03_key_delete(self):
        with self.app as c:
            with self.subTest(adapter='nonexistent-adapter'):
                rv = c.delete('/nonexistent-adapter/keys/test')
                self.assertEqual(501, rv.status_code)
                self.assertIn(b"That adapter doesn't (yet) exist.", rv.data)

            for adapter in self.adapters:
                with self.subTest(adapter=adapter):

                    with self.subTest(step='no-creds'):
                        rv = c.delete('/%s/keys/%s' % (adapter, self.ids.get(adapter, 'test')))
                        self.assertEqual(401, rv.status_code)

                    with self.subTest(step='with-creds'):
                        rv = c.delete('/%s/keys/%s' % (adapter, self.ids.get(adapter, 'test')),
                            headers=self.creds.get(adapter, {}))
                        if nanobox_libcloud.adapters.get_adapter(adapter).\
                                server_ssh_key_method == 'reference':
                            self.assertEqual(200, rv.status_code)
                        else:
                            self.assertEqual(501, rv.status_code)
