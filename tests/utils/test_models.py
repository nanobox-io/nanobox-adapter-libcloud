from nanobox_libcloud.utils import models
from tests import NanoboxLibcloudTestCase


class ModelsUtilTestCase(NanoboxLibcloudTestCase):
    server_spec = {
        'id': 'tst',
        'name': 'Test Data',
        'ram': 25,
        'cpu': 25,
        'disk': 25,
        'transfer': 25,
        'dollars_per_hr': 17.50,
        'dollars_per_mo': 17.50
    }

    server_plan = {
        'id': 'tst',
        'name': 'Test Data',
        'specs': [models.ServerSpec(**server_spec)]
    }

    server_region = {
        'id': 'tst',
        'name': 'Test Data',
        'plans': [models.ServerPlan(**server_plan)]
    }

    def test_adapter_meta(self):
        with self.subTest(check='Valid model creation'):
            model = models.AdapterMeta(
                id='tst',
                name='Test Data',
                server_nick_name='test',
                default_region='test',
                default_size='test',
                default_plan='test',
                can_reboot=False,
                can_rename=False,
                internal_iface='test0',
                external_iface=None,
                ssh_user='test',
                ssh_auth_method='key',
                ssh_key_method='object',
                bootstrap_script='./bootstrap.sh',
                auth_credential_fields=[],
                auth_instructions='Test Data'
            )
            self.assertIsInstance(model, models.AdapterMeta)
        with self.subTest(check='Valid output'):
            rv = model.to_nanobox()
            self.assertIn('id', rv)
            self.assertIn('name', rv)
            self.assertIn('server_nick_name', rv)
            self.assertIn('default_region', rv)
            self.assertIn('default_size', rv)
            self.assertIn('default_plan', rv)
            self.assertIn('can_reboot', rv)
            self.assertIn('can_rename', rv)
            self.assertIn('internal_iface', rv)
            self.assertIn('external_iface', rv)
            self.assertIn('ssh_user', rv)
            self.assertIn('ssh_auth_method', rv)
            self.assertIn('ssh_key_method', rv)
            self.assertIn('bootstrap_script', rv)
            self.assertIn('credential_fields', rv)
            self.assertIn('instructions', rv)

    def test_server_spec(self):
        with self.subTest(check='Valid model creation'):
            model = models.ServerSpec(**self.server_spec)
            self.assertIsInstance(model, models.ServerSpec)
        with self.subTest(check='Valid output'):
            rv = model.to_nanobox()
            self.assertIn('id', rv)
            self.assertIn('name', rv)
            self.assertIn('ram', rv)
            self.assertIn('cpu', rv)
            self.assertIn('disk', rv)
            self.assertIn('transfer', rv)
            self.assertIn('dollars_per_hr', rv)
            self.assertIn('dollars_per_mo', rv)

    def test_server_plan(self):
        with self.subTest(check='Valid model creation'):
            model = models.ServerPlan(**self.server_plan)
            self.assertIsInstance(model, models.ServerPlan)
        with self.subTest(check='Valid output'):
            rv = model.to_nanobox()
            self.assertIn('id', rv)
            self.assertIn('name', rv)
            self.assertIn('specs', rv)

    def test_server_region(self):
        with self.subTest(check='Valid model creation'):
            model = models.ServerRegion(**self.server_region)
            self.assertIsInstance(model, models.ServerRegion)
        with self.subTest(check='Valid output'):
            rv = model.to_nanobox()
            self.assertIn('id', rv)
            self.assertIn('name', rv)
            self.assertIn('plans', rv)

    def test_key_info(self):
        with self.subTest(check='Valid model creation'):
            model = models.KeyInfo(
                id='test',
                name='test',
                key='test'
            )
            self.assertIsInstance(model, models.KeyInfo)
        with self.subTest(check='Valid output'):
            rv = model.to_nanobox()
            self.assertIn('id', rv)
            self.assertIn('name', rv)
            self.assertIn('public_key', rv)

    def test_server_info(self):
        with self.subTest(check='Valid model creation'):
            model = models.ServerInfo(
                id='test',
                name='test',
                status='test',
                external_ip='test',
                internal_ip='test'
            )
            self.assertIsInstance(model, models.ServerInfo)
        with self.subTest(check='Valid output'):
            rv = model.to_nanobox()
            self.assertIn('id', rv)
            self.assertIn('name', rv)
            self.assertIn('status', rv)
            self.assertIn('external_ip', rv)
            self.assertIn('internal_ip', rv)
