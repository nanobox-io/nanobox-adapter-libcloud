import os
from urllib import parse
from decimal import Decimal

import libcloud
from nanobox_libcloud.adapters import Adapter
from nanobox_libcloud.adapters.base import RebootMixin


class Gce(RebootMixin, Adapter):
    """
    Adapter for the Google Compute Engine service
    """

    # Adapter metadata
    id = "gce"
    name = "Google Compute Engine (Beta)"
    server_nick_name = "instance"

    # Provider-wide server properties
    server_internal_iface = 'ens4'
    server_external_iface = None
    server_ssh_user = 'ubuntu'
    server_ssh_key_method = 'object'

    # Provider auth properties
    auth_credential_fields = [
        ["Service-Email", "Service Email"],
        ["Service-Key", "Service Key"],
        ["Project-Id", "Project ID"]
    ]
    auth_instructions = ('You can retrieve all three of these values by visiting '
        '<a href="https://console.cloud.google.com/apis/credentials">the API '
        'credentials page for your GCE project</a>, selecting Create Credentials '
        ' → Service Account Key, selecting or creating a service account, '
        'choosing JSON for the Key Type, and clicking Create. Open the JSON file '
        'it downloads, and copy the <code>client_email</code> to the Service '
        'Email field, the <code>private_key</code> to the Service Key field, and '
        'the <code>project_id</code> to the Project ID field here.')

    # Adapter-sepcific properties
    _plans = [
        ('standard', 'Standard'),
        ('highcpu', 'High CPU'),
        ('highmem', 'High Memory'),
        ('standard-ssd', 'Standard with SSD'),
        ('highcpu-ssd', 'High CPU with SSD'),
        ('highmem-ssd', 'High Memory with SSD')
    ]
    _sizes = {}
    _image_family = 'ubuntu-1604-lts'

    def __init__(self, **kwargs):
        self.generic_credentials = {
            'user_id': os.getenv('GCE_SERVICE_EMAIL', ''),
            'key': parse.unquote(os.getenv('GCE_SERVICE_KEY', '')).replace('\\n', '\n'),
            'project': os.getenv('GCE_PROJECT_ID', ''),
            'auth_type': 'SA'
        }

        self._disk_cost_per_gb = {
            'standard': Decimal(os.getenv('GCE_MONTHLY_DISK_COST', 0)) / 30 / 24,
            'ssd': Decimal(os.getenv('GCE_MONTHLY_SSD_COST', 0)) / 30 / 24
        }

    # Internal overrides for provider retrieval
    def _get_request_credentials(self, headers):
        """Extracts credentials from request headers."""

        return {
            "user_id": headers.get("Auth-Service-Email", ''),
            "key": parse.unquote(headers.get("Auth-Service-Key", '')).replace('\\n', '\n'),
            "project": headers.get("Auth-Project-Id", '')
        }

    def _get_user_driver(self, **auth_credentials):
        """Returns a driver instance for a user with the appropriate authentication credentials set."""

        auth_credentials['auth_type'] = 'SA'

        try:
            return super()._get_user_driver(**auth_credentials)
        except IndexError as e:
            raise libcloud.compute.types.InvalidCredsError("Couldn't load service key")

    # Internal overrides for /meta
    def get_default_region(self):
        """Gets the default region ID."""

        return 'us-west1-a'

    def get_default_size(self):
        """Gets the default size ID."""

        return 'f1-micro'

    def get_default_plan(self):
        """Gets the default plan ID."""

        return 'standard'

    # Internal overrides for /catalog
    def _get_plans(self, location):
        """Retrieves a list of plans for a given adapter."""

        self._sizes = {
            'standard': [],
            'standard-ssd': [],
            'highcpu': [],
            'highcpu-ssd': [],
            'highmem': [],
            'highmem-ssd': [],
        }

        for size in self._get_generic_driver().list_sizes(location):
            plan = size.name.split('-')[1]

            if plan in ['micro', 'small']:
                plan = 'standard'
            if plan in ['megamem', 'ultramem']:
                plan = 'highmem'

            self._sizes[plan].append(size)
            self._sizes[plan + '-ssd'].append(size)

        return self._plans

    def _get_sizes(self, location, plan):
        """Retrieves a list of sizes for a given adapter."""

        return self._sizes[plan]

    def _get_location_id(self, location):
        """Translates a location ID for a given adapter to a ServerSpec value."""

        return location.name

    def _get_size_id(self, location, plan, size):
        """Translates a server size ID for a given adapter to a ServerSpec value."""

        return size.name + ('-ssd' if plan.endswith('-ssd') else '')

    def _get_cpu(self, location, plan, size):
        """Translates a CPU count value for a given adapter to a ServerSpec value."""

        if size.extra['guestCpus']:
            return float(size.extra['guestCpus'])

        return size.extra['guestCpus']

    def _get_disk(self, location, plan, size):
        """Translates a disk size value for a given adapter to a ServerSpec value."""

        gb_ram = Decimal(size.ram) / 1024

        for test, value in [
            # if <, disk is #
            [1, 20],
            [2, 30],
            [4, 40],
            [8, 60],
        ]:
            if gb_ram < test:
                return value

        return int(gb_ram * 10)

    def _get_hourly_price(self, location, plan, size):
        """Translates an hourly cost value for a given adapter to a ServerSpec value."""

        base_price = super()._get_hourly_price(location, plan, size)
        disk_price = float(self._get_disk(location, plan, size) * self._disk_cost_per_gb[
            'ssd' if plan.endswith('-ssd') else 'standard'
        ])

        return (base_price + disk_price) if base_price else None

    # Internal overrides for /server endpoints
    def _get_create_args(self, data):
        """Returns the args used to create a server for this adapter."""

        driver = self._get_user_driver()
        disk_type = 'pd-ssd' if data['size'].endswith('-ssd') else 'pd-standard'
        size = driver.ex_get_size(data['size'].split('-ssd')[0], data['region'])
        name = data['name'].replace('-', '--').replace('.', '-')

        network = self._get_network(driver)

        volume = driver.create_volume(
            size=self._get_disk(data['region'], size.name.split('-')[1], size),
            name=name,
            location=data['region'],
            ex_disk_type=disk_type,
            ex_image_family=self._image_family
        )

        return {
            "name": name,
            "size": size,
            "image": volume.extra['sourceImage'],
            "location": data['region'],
            "ex_boot_disk": volume,
            "ex_network": network,
            "ex_can_ip_forward": True,
            "ex_metadata": {'ssh-keys': '%s:%s %s' % (self.server_ssh_user, data['ssh_key'], self.server_ssh_user)}
        }

    def _get_node_id(self, node):
        """Returns the node ID of a server for this adapter."""
        return node.name

    # Misc Internal Overrides
    def _find_server(self, driver, id):
        try:
            return driver.ex_get_node(id)
        except libcloud.common.types.ProviderError:
            return super()._find_server(driver, id)

    def _find_usable_servers(self, driver):
        return []

    # Misc Internal Helpers (Adapter-Specific)
    def _get_network(self, driver):
        try:
            return driver.ex_get_network('nanobox')
        except libcloud.common.types.ProviderError:
            network = driver.ex_create_network(
                name='nanobox',
                cidr=None,
                mode='auto',
                description='VPC for Nanobox servers'
            )

            firewall = driver.ex_create_firewall(
                name='nanobox',
                allowed=[
                    {"IPProtocol": "all"},
                ],
                network=network
            )

            return network
