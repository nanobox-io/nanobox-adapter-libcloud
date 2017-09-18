import os
from urllib import parse
from decimal import Decimal

import libcloud
from nanobox_libcloud.adapters import Adapter
from nanobox_libcloud.adapters.base import RebootMixin


class Packet(RebootMixin, Adapter):
    """
    Adapter for the Packet service
    """

    # Adapter metadata
    id = "pkt"
    name = "Packet (Beta)"

    # Provider-wide server properties
    # server_internal_iface = 'ens3'
    # server_external_iface = None

    # Provider auth properties
    auth_credential_fields = [
        ["Api-Key", "API Key"],
        ["Project-Id", "Project ID"],
    ]
    auth_instructions = (''
        '')

    # Adapter-sepcific properties
    _plans = [
        ('baremetal', 'Bare Metal')
    ]
    project_id = None

    def __init__(self, **kwargs):
        self.generic_credentials = {
            'key': os.getenv('PKT_API_KEY', ''),
            'secret': None
        }

    # Internal overrides for provider retrieval
    def _get_request_credentials(self, headers):
        """Extracts credentials from request headers."""

        self.project_id = headers.get("Auth-Project-Id", '')

        return {
            "key": headers.get("Auth-Api-Key", ''),
            "secret": None
        }

    def _get_user_driver(self, **auth_credentials):
        """Returns a driver instance for a user with the appropriate authentication credentials set."""

        driver = super()._get_user_driver(**auth_credentials)

        driver.list_key_pairs()

        return driver

    @classmethod
    def _get_id(cls):
        return 'packet'

    # Internal overrides for /meta
    def get_default_region(self):
        """Gets the default region ID."""

        return 'sjc1'

    def get_default_size(self):
        """Gets the default size ID."""

        return 'baremetal_0'

    def get_default_plan(self):
        """Gets the default plan ID."""

        return 'baremetal'

    # Internal overrides for /catalog
    def _get_plans(self, location):
        """Retrieves a list of plans for a given adapter."""

        return self._plans

    def _get_sizes(self, location, plan):
        """Retrieves a list of sizes for a given adapter."""

        data = self._get_generic_driver().connection.request('/plans').object['plans']
        return list(map(self._to_size, [size for size in data if size['line'] not in ['storage']]))

    def _get_cpu(self, location, plan, size):
        """Translates a CPU count value for a given adapter to a ServerSpec value."""

        if size.extra['cpus']:
            return float(size.extra['cpus'])

        return size.extra['cpus']

    # def _get_hourly_price(self, location, plan, size):
    #     """Translates an hourly cost value for a given adapter to a ServerSpec value."""
    #
    #     base_price = super()._get_hourly_price(location, plan, size) or 0
    #     return float(base_price / (30 * 24)) or None

    # Internal overrides for /server endpoints
    def _get_create_args(self, data):
        """Returns the args used to create a server for this adapter."""

        driver = self._get_user_driver()

        location = self._find_location(driver, data['region'])
        size = self._find_size(driver, data['size'])
        image = self._find_image(driver, 'ubuntu_16_04')

        return {
            "name": data['name'],
            "size": size,
            "image": image,
            "location": location,
            "ex_project_id": self.project_id
        }

    # def _get_int_ip(self, server):
    #     """Returns the internal IP of a server for this adapter."""
    #     return self._get_ext_ip(server)

    # Misc internal overrides
    def _find_size(self, driver, id):
        for size in self._get_sizes(None, None):
            if size.id == id:
                return size

    def _find_server(self, driver, id):
        for server in driver.list_nodes(self.project_id):
            if server.id == id:
                return server

    # Internal-only methods
    def _to_size(self, data):
        extra = {'description': data['description'], 'line': data['line'],
                 'cpus': sum([cpus['count'] for cpus in data['specs']['cpus']])}

        ram = data['specs']['memory']['total'].lower()
        if 'mb' in ram:
            ram = int(ram.replace('mb', ''))
        elif 'gb' in ram:
            ram = int(ram.replace('gb', '')) * 1024

        disk = 0
        for disks in data['specs']['drives']:
            disk_count = disks['count'] if hasattr(data, 'features') and \
                hasattr(data['features'], 'raid') and \
                    not data['features']['raid'] else 1
            if 'GB' in disks['size']:
                disk += int(disk_count * float(disks['size'].replace('GB', '')))
            elif 'TB' in disks['size']:
                disk += int(disk_count * float(disks['size'].replace('TB', '')) * 1024)

        price = data['pricing']['hour']

        return libcloud.compute.base.NodeSize(id=data['slug'], name=data['name'], ram=ram, disk=disk,
                        bandwidth=0, price=price, extra=extra, driver=self)
