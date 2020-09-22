import libcloud
from nanobox_libcloud.adapters import base
from tests import NanoboxLibcloudTestCase
from unittest.mock import MagicMock, patch


class BaseAdapterTestCase(NanoboxLibcloudTestCase):
    adapter = None
    driver = None
    key_pair = None

    def setUp(self):
        super().setUp()
        self.adapter = base.Adapter()
        self.adapter.id = 'dummy'
        self.adapter.generic_credentials = {'creds': 0}
        self.adapter._get_request_credentials = MagicMock(side_effect=lambda value: value or {'creds': 0})
        self.adapter._get_id = MagicMock(return_value='dummy')
        self.adapter.get_default_region = MagicMock(return_value='test')
        self.adapter.get_default_size = MagicMock(return_value='test')
        self.adapter.get_default_plan = MagicMock(return_value='test')
        self.adapter._get_cpu = MagicMock(return_value=0)
        self.adapter._get_create_args = MagicMock(return_value={})

        self.driver = self.adapter._get_driver_class()

        self.key_pair = libcloud.compute.base.KeyPair(
            name='test',
            public_key=self.test_key,
            fingerprint='fingerprint',
            driver=self.driver
        )
        self.driver.create_key_pair = MagicMock(return_value=self.key_pair)
        self.driver.list_key_pairs = MagicMock(return_value=[self.key_pair])
        self.driver.delete_key_pair = MagicMock(return_value=True)

    def test_91_do_meta(self):
        rv = self.adapter.do_meta()
        self.assertIn('id', rv)
        self.assertEqual('dummy', rv['id'])
        self.assertIn('name', rv)
        self.assertEqual('', rv['name'])
        self.assertIn('server_nick_name', rv)
        self.assertEqual('server', rv['server_nick_name'])
        self.assertIn('default_region', rv)
        self.assertEqual('test', rv['default_region'])
        self.assertIn('default_size', rv)
        self.assertEqual('test', rv['default_size'])
        self.assertIn('default_plan', rv)
        self.assertEqual('test', rv['default_plan'])
        self.assertIn('can_reboot', rv)
        self.assertEqual(False, rv['can_reboot'])
        self.assertIn('can_rename', rv)
        self.assertEqual(False, rv['can_rename'])
        self.assertIn('internal_iface', rv)
        self.assertEqual('eth1', rv['internal_iface'])
        self.assertIn('external_iface', rv)
        self.assertEqual('eth0', rv['external_iface'])
        self.assertIn('ssh_user', rv)
        self.assertEqual('root', rv['ssh_user'])
        self.assertIn('ssh_auth_method', rv)
        self.assertEqual('key', rv['ssh_auth_method'])
        self.assertIn('ssh_key_method', rv)
        self.assertEqual('reference', rv['ssh_key_method'])
        self.assertIn('bootstrap_script', rv)
        self.assertEqual('https://s3.amazonaws.com/tools.nanobox.io/bootstrap/ubuntu.sh', rv['bootstrap_script'])
        self.assertIn('credential_fields', rv)
        self.assertEqual([], rv['credential_fields'])
        self.assertIn('instructions', rv)
        self.assertEqual('', rv['instructions'])

    def test_92_do_catalog(self):
        rv = self.adapter.do_catalog()
        self.assertGreater(len(rv), 0)
        for region in rv:
            self.assertIn('id', region)
            self.assertIn('name', region)
            self.assertIn('plans', region)
            self.assertGreater(len(region['plans']), 0)
            for plan in region['plans']:
                self.assertIn('id', plan)
                self.assertIn('name', plan)
                self.assertIn('specs', plan)
                self.assertGreater(len(plan['specs']), 0)
                for spec in plan['specs']:
                    self.assertIn('id', spec)
                    self.assertIn('name', spec)
                    self.assertIn('ram', spec)
                    self.assertIn('cpu', spec)
                    self.assertIn('disk', spec)
                    self.assertIn('transfer', spec)
                    self.assertIn('dollars_per_hr', spec)
                    self.assertIn('dollars_per_mo', spec)

    def test_93_do_verify(self):
        rv = self.adapter.do_verify({'creds': 0})
        self.assertTrue(rv)

    def test_94_do_key_create(self):
        with self.subTest(check='None'):
            rv = self.adapter.do_key_create({'creds': 0}, None)
            self.assertIsInstance(rv, dict)
            self.assertIn('error', rv)
            self.assertIn("All keys need an 'id' and 'key' property.", rv['error'])

        with self.subTest(check='id only'):
            rv = self.adapter.do_key_create({'creds': 0}, {'id': 'test'})
            self.assertIsInstance(rv, dict)
            self.assertIn('error', rv)
            self.assertIn("All keys need an 'id' and 'key' property.", rv['error'])

        with self.subTest(check='key only'):
            rv = self.adapter.do_key_create({'creds': 0}, {'key': self.test_key})
            self.assertIsInstance(rv, dict)
            self.assertIn('error', rv)
            self.assertIn("All keys need an 'id' and 'key' property.", rv['error'])

        with self.subTest(check='valid key'):
            rv = self.adapter.do_key_create({'creds': 0}, {'id': 'test', 'key': self.test_key})
            self.assertIsInstance(rv, dict)
            self.assertIn('data', rv)
            self.assertIn('id', rv['data'])
            self.assertEqual('test', rv['data']['id'])

    def test_95_do_key_query(self):
        with self.subTest(check='None'):
            rv = self.adapter.do_key_query({'creds': 0}, None)
            self.assertIn('error', rv)
            self.assertEqual('SSH key not found', rv['error'])

        with self.subTest(check='with id'):
            rv = self.adapter.do_key_query({'creds': 0}, 'test')
            self.assertIn('data', rv)
            self.assertIn('id', rv['data'])
            self.assertEqual('test', rv['data']['id'])
            self.assertIn('name', rv['data'])
            self.assertEqual('test', rv['data']['name'])
            self.assertIn('public_key', rv['data'])
            self.assertEqual(self.test_key, rv['data']['public_key'])

    def test_96_do_key_delete(self):
        with self.subTest(check='None'):
            rv = self.adapter.do_key_delete({'creds': 0}, None)
            self.assertIn('error', rv)
            self.assertEqual('SSH key not found', rv['error'])

        with self.subTest(check='with id'):
            rv = self.adapter.do_key_delete({'creds': 0}, 'test')
            self.assertEqual(True, rv)

    def test_97_do_server_create(self):
        with self.subTest(check='None'):
            rv = self.adapter.do_server_create({'creds': 0}, None)
            self.assertIsInstance(rv, dict)
            self.assertIn('error', rv)
            self.assertIn("All servers need a 'name', 'region', and 'size' property.", rv['error'])

        with self.subTest(check='name only'):
            rv = self.adapter.do_server_create({'creds': 0}, {'name': 'test'})
            self.assertIsInstance(rv, dict)
            self.assertIn('error', rv)
            self.assertIn("All servers need a 'name', 'region', and 'size' property.", rv['error'])

        with self.subTest(check='region only'):
            rv = self.adapter.do_server_create({'creds': 0}, {'region': 'test'})
            self.assertIsInstance(rv, dict)
            self.assertIn('error', rv)
            self.assertIn("All servers need a 'name', 'region', and 'size' property.", rv['error'])

        with self.subTest(check='size only'):
            rv = self.adapter.do_server_create({'creds': 0}, {'size': 'test'})
            self.assertIsInstance(rv, dict)
            self.assertIn('error', rv)
            self.assertIn("All servers need a 'name', 'region', and 'size' property.", rv['error'])

        with self.subTest(check='name and region only'):
            rv = self.adapter.do_server_create({'creds': 0}, {'name': 'test', 'region': 'test'})
            self.assertIsInstance(rv, dict)
            self.assertIn('error', rv)
            self.assertIn("All servers need a 'name', 'region', and 'size' property.", rv['error'])

        with self.subTest(check='name and size only'):
            rv = self.adapter.do_server_create({'creds': 0}, {'name': 'test', 'size': 'test'})
            self.assertIsInstance(rv, dict)
            self.assertIn('error', rv)
            self.assertIn("All servers need a 'name', 'region', and 'size' property.", rv['error'])

        with self.subTest(check='region and size only'):
            rv = self.adapter.do_server_create({'creds': 0}, {'region': 'test', 'size': 'test'})
            self.assertIsInstance(rv, dict)
            self.assertIn('error', rv)
            self.assertIn("All servers need a 'name', 'region', and 'size' property.", rv['error'])

        with self.subTest(check='valid server'):
            rv = self.adapter.do_server_create({'creds': 0}, {'name': 'test', 'region': 'test', 'size': 'test'})
            self.assertIsInstance(rv, dict)
            self.assertIn('data', rv)
            self.assertIn('id', rv['data'])
            self.assertEqual('3', rv['data']['id'])

    def test_98_do_server_query(self):
        with self.subTest(check='None'):
            rv = self.adapter.do_server_query({'creds': 0}, None)
            self.assertIn('error', rv)
            self.assertEqual('%s not found' % (self.adapter.server_nick_name), rv['error'])

        with self.subTest(check='with id'):
            rv = self.adapter.do_server_query({'creds': 0}, '1')
            self.assertIn('data', rv)
            self.assertIn('id', rv['data'])
            self.assertEqual('1', rv['data']['id'])
            self.assertIn('name', rv['data'])
            self.assertEqual('dummy-1', rv['data']['name'])
            self.assertIn('status', rv['data'])
            self.assertEqual('active', rv['data']['status'])
            self.assertIn('external_ip', rv['data'])
            self.assertIn('internal_ip', rv['data'])

    def test_99_do_server_cancel(self):
        with self.subTest(check='None'):
            rv = self.adapter.do_server_cancel({'creds': 0}, None)
            self.assertIn('error', rv)
            self.assertEqual('%s not found' % (self.adapter.server_nick_name), rv['error'])

        with self.subTest(check='with id'):
            rv = self.adapter.do_server_cancel({'creds': 0}, '1')
            self.assertEqual(True, rv)

    def test_01__get_driver_class(self):
        rv = self.adapter._get_driver_class()
        self.assertTrue(issubclass(rv, libcloud.compute.base.NodeDriver))

    def test_02__get_user_driver(self):
        with self.subTest(check='no creds - first attempt'):
            with self.assertRaises(TypeError):
                rv = self.adapter._get_user_driver()

        with self.subTest(check='missing creds'):
            with self.assertRaises(TypeError):
                rv = self.adapter._get_user_driver({'waffle': 'iron'})

        with self.subTest(check='valid creds'):
            rv = self.adapter._get_user_driver(**self.adapter.generic_credentials)
            self.assertIsInstance(rv, libcloud.compute.base.NodeDriver)

        with self.subTest(check='no creds - after success'):
            rv = self.adapter._get_user_driver()
            self.assertIsInstance(rv, libcloud.compute.base.NodeDriver)

    def test_03__get_generic_driver(self):
        with self.subTest(check='initial call'):
            rv1 = self.adapter._get_generic_driver()
            self.assertIsInstance(rv1, libcloud.compute.base.NodeDriver)

        with self.subTest(check='second call'):
            rv2 = self.adapter._get_generic_driver()
            self.assertIsInstance(rv2, libcloud.compute.base.NodeDriver)
            self.assertEqual(rv1, rv2)

    def test_04_can_install_key(self):
        self.assertFalse(self.adapter.can_install_key())

    def test_05_can_reboot(self):
        self.assertFalse(self.adapter.can_reboot())

    def test_06_can_rename(self):
        self.assertFalse(self.adapter.can_rename())

    def test_07__get_locations(self):
        rv = self.adapter._get_locations()
        self.assertGreater(len(rv), 0)
        for location in rv:
            self.assertIsInstance(location, libcloud.compute.base.NodeLocation)

    def test_08__get_sizes(self):
        with self.subTest(check='no arguments'):
            with self.assertRaises(TypeError):
                rv = self.adapter._get_sizes()

        with self.subTest(check='one argument'):
            with self.assertRaises(TypeError):
                rv = self.adapter._get_sizes(None)

        with self.subTest(check='both arguments'):
            rv = self.adapter._get_sizes(None, None)
            self.assertGreater(len(rv), 0)
            for size in rv:
                self.assertIsInstance(size, libcloud.compute.base.NodeSize)

    def test_09__get_location_id(self):
        rv = self.adapter._get_location_id(MagicMock(id='test'))
        self.assertEqual('test', rv)

    def test_10__get_location_name(self):
        tv = MagicMock()
        tv.name = 'test'
        rv = self.adapter._get_location_name(tv)
        self.assertEqual('test', rv)

    def test_11__get_size_id(self):
        rv = self.adapter._get_size_id(None, None, MagicMock(id='test'))
        self.assertEqual('test', rv)

    def test_12__get_size_name(self):
        tv = MagicMock()
        tv.name = 'test'
        rv = self.adapter._get_size_name(None, None, tv)
        self.assertEqual('test', rv)

    def test_13__get_ram(self):
        rv = self.adapter._get_ram(None, None, MagicMock(ram=512))
        self.assertEqual(512, rv)

    def test_14__get_disk(self):
        rv = self.adapter._get_disk(None, None, MagicMock(disk=10))
        self.assertEqual(10, rv)

    def test_15__get_transfer(self):
        rv = self.adapter._get_transfer(None, None, MagicMock(bandwidth=None))
        self.assertIsNone(rv)

    def test_16__get_hourly_price(self):
        with self.subTest(check='None'):
            rv = self.adapter._get_hourly_price(None, None, MagicMock(price=None))
            self.assertIsNone(rv)

        with self.subTest(check='ten cents per hour'):
            rv = self.adapter._get_hourly_price(None, None, MagicMock(price=0.10))
            self.assertEqual(0.10, rv)

    def test_17__get_monthly_price(self):
        with self.subTest(check='None'):
            rv = self.adapter._get_monthly_price(None, None, MagicMock(price=None))
            self.assertIsNone(rv)

        with self.subTest(check='ten cents per hour'):
            rv = self.adapter._get_monthly_price(None, None, MagicMock(price=0.10))
            self.assertEqual(72.00, rv)

    def test_18__create_key(self):
        self.adapter._create_key(self.adapter._get_generic_driver(),
                                 {'id': 'test', 'key': self.test_key})
        self.driver.create_key_pair.assert_called_with('test', self.test_key)

    def test_19__delete_key(self):
        self.adapter._delete_key(self.adapter._get_generic_driver(), self.key_pair)
        self.driver.delete_key_pair.assert_called_with(self.key_pair)

    def test_20__get_node_id(self):
        rv = self.adapter._get_node_id(MagicMock(id='test'))
        self.assertEqual('test', rv)

    def test_21__get_ext_ip(self):
        with self.subTest(check='empty list'):
            rv = self.adapter._get_ext_ip(MagicMock(public_ips=[]))
            self.assertIsNone(rv)

        with self.subTest(check='test list'):
            rv = self.adapter._get_ext_ip(MagicMock(public_ips=['test']))
            self.assertEqual('test', rv)

    def test_22__get_int_ip(self):
        with self.subTest(check='empty list'):
            rv = self.adapter._get_int_ip(MagicMock(private_ips=[]))
            self.assertIsNone(rv)

        with self.subTest(check='test list'):
            rv = self.adapter._get_int_ip(MagicMock(private_ips=['test']))
            self.assertEqual('test', rv)

    def test_23__destroy_server(self):
        tv = MagicMock(**{'destroy.return_value': True})
        self.adapter._destroy_server(tv)
        tv.destroy.assert_called()

    def test_24__find_location(self):
        driver = self.adapter._get_generic_driver()

        with self.subTest(check='None'):
            rv = self.adapter._find_location(driver, None)
            self.assertIsNone(rv)

        with self.subTest(check='nonexistent'):
            rv = self.adapter._find_location(driver, 'nonexistent')
            self.assertIsNone(rv)

        with self.subTest(check='valid'):
            rv = self.adapter._find_location(driver, '1')
            self.assertIsInstance(rv, libcloud.compute.base.NodeLocation)

    def test_25__find_size(self):
        driver = self.adapter._get_generic_driver()

        with self.subTest(check='None'):
            rv = self.adapter._find_size(driver, None)
            self.assertIsNone(rv)

        with self.subTest(check='nonexistent'):
            rv = self.adapter._find_size(driver, 'nonexistent')
            self.assertIsNone(rv)

        with self.subTest(check='valid'):
            rv = self.adapter._find_size(driver, '1')
            self.assertIsInstance(rv, libcloud.compute.base.NodeSize)

    def test_26__find_image(self):
        driver = self.adapter._get_generic_driver()

        with self.subTest(check='None'):
            rv = self.adapter._find_image(driver, None)
            self.assertIsNone(rv)

        with self.subTest(check='nonexistent'):
            rv = self.adapter._find_image(driver, 'nonexistent')
            self.assertIsNone(rv)

        with self.subTest(check='valid'):
            rv = self.adapter._find_image(driver, '1')
            self.assertIsInstance(rv, libcloud.compute.base.NodeImage)

    def test_27__find_ssh_key(self):
        driver = self.adapter._get_generic_driver()

        with self.subTest(check='None'):
            rv = self.adapter._find_ssh_key(driver, None)
            self.assertIsNone(rv)

        with self.subTest(check='nonexistent'):
            rv = self.adapter._find_ssh_key(driver, 'nonexistent')
            self.assertIsNone(rv)

        with self.subTest(check='valid'):
            rv = self.adapter._find_ssh_key(driver, 'test')
            self.assertIsInstance(rv, libcloud.compute.base.KeyPair)

    def test_28__find_usable_ssh_keys(self):
        rv = self.adapter._find_usable_ssh_keys(self.adapter._get_generic_driver())
        self.assertGreater(len(rv), 0)
        for key in rv:
            self.assertIsInstance(key, libcloud.compute.base.KeyPair)

    def test_29__find_server(self):
        driver = self.adapter._get_generic_driver()

        with self.subTest(check='None'):
            rv = self.adapter._find_server(driver, None)
            self.assertIsNone(rv)

        with self.subTest(check='nonexistent'):
            rv = self.adapter._find_server(driver, 'nonexistent')
            self.assertIsNone(rv)

        with self.subTest(check='valid'):
            rv = self.adapter._find_server(driver, '1')
            self.assertIsInstance(rv, libcloud.compute.base.Node)

    def test_30__find_usable_servers(self):
        rv = self.adapter._find_usable_servers(self.adapter._get_generic_driver())
        self.assertGreater(len(rv), 0)
        for key in rv:
            self.assertIsInstance(key, libcloud.compute.base.Node)

    def test_31__config_error(self):
        with self.assertRaises(ValueError):
            self.adapter._config_error('')


class KeyInstallMixinTestClass(base.KeyInstallMixin, base.Adapter):
    id = 'key-mixin'

    def _get_request_credentials(self, headers):
        return headers

    def _get_driver_class(self):
        return libcloud.get_driver(libcloud.DriverType.COMPUTE, 'dummy')

    def _install_key(self, server, key_data):
        return True


class KeyInstallMixinTestCase(NanoboxLibcloudTestCase):
    def setUp(self):
        super().setUp()
        self.mixin = KeyInstallMixinTestClass()

    def test_do_install_key(self):
        with self.subTest(check='None'):
            rv = self.mixin.do_install_key({'creds': 0}, None, {})
            self.assertIn('error', rv)
            self.assertEqual("All keys need an 'id' and 'key' property. (Got {})", rv['error'])

        with self.subTest(check='with id'):
            rv = self.mixin.do_install_key({'creds': 0}, '1', {})
            self.assertIn('error', rv)
            self.assertEqual("All keys need an 'id' and 'key' property. (Got {})", rv['error'])

        with self.subTest(check='with data'):
            rv = self.mixin.do_install_key({'creds': 0}, None, {'id': 'test', 'key': self.test_key})
            self.assertIn('error', rv)
            self.assertEqual('%s not found' % (self.mixin.server_nick_name), rv['error'])

        with self.subTest(check='with id and data'):
            rv = self.mixin.do_install_key({'creds': 0}, '1', {'id': 'test', 'key': self.test_key})
            self.assertEqual(True, rv)


class RebootMixinTestClass(base.RebootMixin, base.Adapter):
    id = 'reboot-mixin'

    def _get_request_credentials(self, headers):
        return headers

    def _get_driver_class(self):
        return libcloud.get_driver(libcloud.DriverType.COMPUTE, 'dummy')


class RebootMixinTestCase(NanoboxLibcloudTestCase):
    def setUp(self):
        super().setUp()
        self.mixin = RebootMixinTestClass()

    def test_do_server_reboot(self):
        with self.subTest(check='None'):
            rv = self.mixin.do_server_reboot({'creds': 0}, None)
            self.assertIn('error', rv)
            self.assertEqual('%s not found' % (self.mixin.server_nick_name), rv['error'])

        with self.subTest(check='with id'):
            rv = self.mixin.do_server_reboot({'creds': 0}, '1')
            self.assertEqual(True, rv)


class RenameMixinTestClass(base.RenameMixin, base.Adapter):
    id = 'rename-mixin'

    def _get_request_credentials(self, headers):
        return headers

    def _get_driver_class(self):
        return libcloud.get_driver(libcloud.DriverType.COMPUTE, 'dummy')

    def _rename_server(self, server, name):
        return True


class RenameMixinTestCase(NanoboxLibcloudTestCase):
    def setUp(self):
        super().setUp()
        self.mixin = RenameMixinTestClass()

    def test_do_server_rename(self):
        with self.subTest(check='None'):
            rv = self.mixin.do_server_rename({'creds': 0}, None, {})
            self.assertIn('error', rv)
            self.assertEqual("A 'name' property is required for rename. (Got {})", rv['error'])

        with self.subTest(check='with id'):
            rv = self.mixin.do_server_rename({'creds': 0}, '1', {})
            self.assertIn('error', rv)
            self.assertEqual("A 'name' property is required for rename. (Got {})", rv['error'])

        with self.subTest(check='with data'):
            rv = self.mixin.do_server_rename({'creds': 0}, None, {'name': 'test'})
            self.assertIn('error', rv)
            self.assertEqual('%s not found' % (self.mixin.server_nick_name), rv['error'])

        with self.subTest(check='with id and data'):
            rv = self.mixin.do_server_rename({'creds': 0}, '1', {'name': 'test'})
            self.assertEqual(True, rv)
