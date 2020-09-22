import nanobox_libcloud

from flask import json
from tests import NanoboxLibcloudTestCase
from time import sleep


class ServersControllerTestCase(NanoboxLibcloudTestCase):
    ids = {}

    def test_01_server_create(self):
        with self.app as c:
            with self.subTest(adapter='nonexistent-adapter'):
                rv = c.post('/nonexistent-adapter/servers')
                self.assertEqual(501, rv.status_code)
                self.assertIn(b"That adapter doesn't (yet) exist.", rv.data)

            for adapter in self.adapters:
                a = nanobox_libcloud.adapters.get_adapter(adapter)
                with self.subTest(adapter=adapter):

                    with self.subTest(step='no-creds'):
                        rv = c.post('/%s/servers' % (adapter))
                        self.assertEqual(401, rv.status_code)

                    with self.subTest(step='with-creds-no-data'):
                        rv = c.post('/%s/servers' % (adapter),
                            # content_type='application/json',
                            headers=self.creds.get(adapter, {}))
                        with self.subTest(value='code'):
                            self.assertEqual(400, rv.status_code)
                        with self.subTest(value='data'):
                            self.assertIn(b"\'name\'", rv.data)

                    with self.subTest(step='with-creds-and-data'):
                        rv = c.post('/%s/servers' % (adapter), data=json.dumps({
                                "name": "test-server-name",
                                "region": a.get_default_region(),
                                "size": a.get_default_size(),
                                "ssh_key": self.test_key\
                                    if a.server_ssh_key_method == 'object' else None
                            }), content_type='application/json',
                            headers=self.creds.get(adapter, {}))
                        with self.subTest(value='code'):
                            self.assertEqual(201, rv.status_code)
                        with self.subTest(value='data'):
                            self.assertIn(b'"id":', rv.data)
                        if b'"id":' in rv.data:
                            self.ids[adapter] = json.loads(rv.data).get('id')

    def test_02_server_query(self):
        with self.app as c:
            with self.subTest(adapter='nonexistent-adapter'):
                rv = c.get('/nonexistent-adapter/servers/test-server-name')
                self.assertEqual(501, rv.status_code)
                self.assertIn(b"That adapter doesn't (yet) exist.", rv.data)

            for adapter in self.adapters:
                a = nanobox_libcloud.adapters.get_adapter(adapter)
                with self.subTest(adapter=adapter):

                    with self.subTest(step='no-creds'):
                        rv = c.get('/%s/servers/%s' % (adapter, self.ids.get(adapter, 'test-server-name')))
                        self.assertEqual(401, rv.status_code)

                    with self.subTest(step='with-creds'):
                        rv = c.get('/%s/servers/%s' % (adapter, self.ids.get(adapter, 'test-server-name')),
                            headers=self.creds.get(adapter, {}))
                        with self.subTest(value='code'):
                            self.assertEqual(201, rv.status_code)
                        with self.subTest(value='data'):
                            self.assertIn(b'"id":', rv.data)

                        with self.subTest(step='wait for active'):

                            # 24 retries with {retries} seconds between is about 5 minutes
                            retries = 0
                            while retries < 24 and json.loads(rv.data).get('status', 'unknown') != 'active':
                                retries += 1
                                sleep(retries)
                                rv = c.get('/%s/servers/%s' % (adapter, self.ids.get(adapter, 'test-server-name')),
                                    headers=self.creds.get(adapter, {}))

                            self.assertEqual(json.loads(rv.data).get('status', 'unknown'), 'active')

    def test_03_server_install_key(self):
        with self.app as c:
            with self.subTest(adapter='nonexistent-adapter'):
                rv = c.patch('/nonexistent-adapter/servers/test-server-name/keys')
                self.assertEqual(501, rv.status_code)
                self.assertIn(b"That adapter doesn't (yet) exist.", rv.data)

            for adapter in self.adapters:
                a = nanobox_libcloud.adapters.get_adapter(adapter)
                with self.subTest(adapter=adapter):

                    with self.subTest(step='no-creds'):
                        rv = c.patch('/%s/servers/%s/keys' % (adapter, self.ids.get(adapter, 'test-server-name')))
                        if a.can_install_key():
                            self.assertEqual(401, rv.status_code)
                        else:
                            self.assertEqual(501, rv.status_code)

                    with self.subTest(step='with-creds-no-data'):
                        rv = c.patch('/%s/servers/%s/keys' % (adapter, self.ids.get(adapter, 'test-server-name')),
                            headers=self.creds.get(adapter, {}))
                        if a.can_install_key():
                            self.assertEqual(400, rv.status_code)
                        else:
                            self.assertEqual(501, rv.status_code)

                    with self.subTest(step='with-creds-and-data'):
                        rv = c.patch('/%s/servers/%s/keys' % (adapter, self.ids.get(adapter, 'test-server-name')),
                            data=json.dumps({
                                "id": "test",
                                "key": self.test_key
                            }), content_type='application/json',
                            headers=self.creds.get(adapter, {}))
                        if a.can_install_key():
                            with self.subTest(value='code'):
                                self.assertEqual(200, rv.status_code)
                            with self.subTest(value='data'):
                                self.assertIn(b'', rv.data)
                        else:
                            self.assertEqual(501, rv.status_code)

    def test_04_server_reboot(self):
        with self.app as c:
            with self.subTest(adapter='nonexistent-adapter'):
                rv = c.patch('/nonexistent-adapter/servers/test-server-name/reboot')
                self.assertEqual(501, rv.status_code)
                self.assertIn(b"That adapter doesn't (yet) exist.", rv.data)

            for adapter in self.adapters:
                a = nanobox_libcloud.adapters.get_adapter(adapter)
                with self.subTest(adapter=adapter):

                    with self.subTest(step='no-creds'):
                        rv = c.patch('/%s/servers/%s/reboot' % (adapter, self.ids.get(adapter, 'test-server-name')))
                        if a.can_reboot():
                            self.assertEqual(401, rv.status_code)
                        else:
                            self.assertEqual(501, rv.status_code)

                    with self.subTest(step='with-creds'):
                        rv = c.patch('/%s/servers/%s/reboot' % (adapter, self.ids.get(adapter, 'test-server-name')),
                            headers=self.creds.get(adapter, {}))
                        if a.can_reboot():
                            with self.subTest(value='code'):
                                self.assertEqual(200, rv.status_code)
                            with self.subTest(value='data'):
                                self.assertEqual(b'', rv.data)
                        else:
                            self.assertEqual(501, rv.status_code)

    def test_05_server_rename(self):
        with self.app as c:
            with self.subTest(adapter='nonexistent-adapter'):
                rv = c.patch('/nonexistent-adapter/servers/test-server-name/rename')
                self.assertEqual(501, rv.status_code)
                self.assertIn(b"That adapter doesn't (yet) exist.", rv.data)

            for adapter in self.adapters:
                a = nanobox_libcloud.adapters.get_adapter(adapter)
                with self.subTest(adapter=adapter):

                    with self.subTest(step='no-creds'):
                        rv = c.patch('/%s/servers/%s/rename' % (adapter, self.ids.get(adapter, 'test-server-name')))
                        if a.can_rename():
                            self.assertEqual(401, rv.status_code)
                        else:
                            self.assertEqual(501, rv.status_code)

                    with self.subTest(step='with-creds'):
                        rv = c.patch('/%s/servers/%s/rename' % (adapter, self.ids.get(adapter, 'test-server-name')),
                            headers=self.creds.get(adapter, {}))
                        if a.can_rename():
                            with self.subTest(value='code'):
                                self.assertEqual(200, rv.status_code)
                            with self.subTest(value='data'):
                                self.assertEqual(b'', rv.data)
                        else:
                            self.assertEqual(501, rv.status_code)

    def test_06_server_cancel(self):
        with self.app as c:
            with self.subTest(adapter='nonexistent-adapter'):
                rv = c.delete('/nonexistent-adapter/servers/test-server-name')
                self.assertEqual(501, rv.status_code)
                self.assertIn(b"That adapter doesn't (yet) exist.", rv.data)

            for adapter in self.adapters:
                a = nanobox_libcloud.adapters.get_adapter(adapter)
                with self.subTest(adapter=adapter):

                    with self.subTest(step='no-creds'):
                        rv = c.delete('/%s/servers/%s' % (adapter, self.ids.get(adapter, 'test-server-name')))
                        self.assertEqual(401, rv.status_code)

                    with self.subTest(step='with-creds'):
                        rv = c.delete('/%s/servers/%s' % (adapter, self.ids.get(adapter, 'test-server-name')),
                            headers=self.creds.get(adapter, {}))
                        with self.subTest(value='code'):
                            self.assertEqual(200, rv.status_code)
                        with self.subTest(value='data'):
                            self.assertEqual(b'', rv.data)
