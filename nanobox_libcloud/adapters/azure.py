import os
import tempfile
from urllib import parse
from decimal import Decimal

from flask import after_this_request

import libcloud
from nanobox_libcloud.adapters import Adapter
from nanobox_libcloud.adapters.base import RebootMixin


class Azure(RebootMixin, Adapter):
    """
    Adapter for the Microsoft Azure service
    """

    # Adapter metadata
    id = "azr"
    name = "Microsoft Azure (Beta)"
    # server_nick_name = "instance"

    # Provider-wide server properties
    # server_internal_iface = 'ens4'
    # server_external_iface = None
    # server_ssh_user = 'ubuntu'
    # server_ssh_key_method = 'object'

    # Provider auth properties
    auth_credential_fields = [
        ["Subscription-Id", "Subscription ID"],
        ["Key-File", "Key"]
    ]
    auth_instructions = ('Using Azure is fairly complex. First, create a '
    'self-signed certificate. Then, follow the instructions '
    '<a href="https://docs.microsoft.com/en-us/azure/azure-api-management-certs">here</a> '
    'to add the certificate to your account. Finally, enter your subscription ID '
    'and the contents of the certificate\'s key file above.')

    # Adapter-sepcific properties
    _plans = [
        ('standard', 'Standard'),
        ('highspeed', 'High Speed'),
    ]
    _sizes = {}
    # _image_family = 'ubuntu-1604-lts'

    def __init__(self, **kwargs):
        self.generic_credentials = {
            'subscription_id': os.getenv('AZR_SUB_ID', ''),
            'key': os.getenv('AZR_KEY', '')
        }

    # Internal overrides for provider retrieval
    def _get_request_credentials(self, headers):
        """Extracts credentials from request headers."""

        return {
            "subscription_id": headers.get("Auth-Subscription-Id", ''),
            "key": parse.unquote(headers.get("Auth-Key-File", '')).replace('\\n', '\n')
        }

    def _get_user_driver(self, **auth_credentials):
        """Returns a driver instance for a user with the appropriate authentication credentials set."""

        if self._user_driver is None:
            with tempfile.NamedTemporaryFile(mode = 'w+', delete = False) as fp:
                key_file = fp.name
                fp.write(auth_credentials['key'])
                del auth_credentials['key']
                auth_credentials['key_file'] = key_file
                super()._get_user_driver(**auth_credentials)

            @after_this_request
            def clr_tmp_user(response):
                os.remove(key_file)
                return response

        return self._user_driver

    def _get_generic_driver(self):
        """Returns a driver instance for a user with the appropriate authentication credentials set."""

        if self._generic_driver is None:
            with tempfile.NamedTemporaryFile(mode = 'w+', delete = False) as fp:
                key_file = fp.name
                fp.write(self.generic_credentials['key'])
                del self.generic_credentials['key']
                self.generic_credentials['key_file'] = key_file
                super()._get_generic_driver()

            @after_this_request
            def clr_tmp_generic(response):
                os.remove(key_file)
                return response

        return self._generic_driver

    @classmethod
    def _get_id(cls):
        return 'azure'

    # Internal overrides for /meta
    def get_default_region(self):
        """Gets the default region ID."""

        return 'westus2'

    def get_default_size(self):
        """Gets the default size ID."""

        return 'ExtraSmall'

    def get_default_plan(self):
        """Gets the default plan ID."""

        return 'standard'

    # Internal overrides for /catalog
    def _get_plans(self, location):
        """Retrieves a list of plans for a given adapter."""

        self._sizes = {
            'standard': [],
            'highspeed': [],
        }

        for size in self._get_generic_driver().list_sizes():
            plan = {'A': 'standard', 'D': 'highspeed'}.get(
                size.id.replace('Standard_', '')[:1], size.id)

            if plan not in ['standard', 'highspeed']:
                plan = 'standard'

            self._sizes[plan].append(size)

        return self._plans

    def _get_sizes(self, location, plan):
        """Retrieves a list of sizes for a given adapter."""

        return self._sizes[plan]

    # def _get_location_id(self, location):
    #     """Translates a location ID for a given adapter to a ServerSpec value."""
    #
    #     return location.name

    # def _get_size_id(self, location, plan, size):
    #     """Translates a server size ID for a given adapter to a ServerSpec value."""
    #
    #     return size.name + ('-ssd' if plan.endswith('-ssd') else '')

    def _get_cpu(self, location, plan, size):
        """Translates a CPU count value for a given adapter to a ServerSpec value."""

        if size.extra['cores'] == 'Shared':
            return 0.5
        if size.extra['cores']:
            return float(size.extra['cores'])

        return size.extra['cores']

    # def _get_disk(self, location, plan, size):
    #     """Translates a disk size value for a given adapter to a ServerSpec value."""
    #
    #     gb_ram = Decimal(size.ram) / 1024
    #
    #     for test, value in [
    #         # if <, disk is #
    #         [1, 20],
    #         [2, 30],
    #         [4, 40],
    #         [8, 60],
    #     ]:
    #         if gb_ram < test:
    #             return value
    #
    #     return int(gb_ram * 10)

    # def _get_hourly_price(self, location, plan, size):
    #     """Translates an hourly cost value for a given adapter to a ServerSpec value."""
    #
    #     base_price = super()._get_hourly_price(location, plan, size) or 0
    #     disk_size = self._get_disk(location, plan, size)
    #
    #     return (base_price + float(
    #         disk_size * self._disk_cost_per_gb['ssd' if plan.endswith('-ssd') else 'standard'])) or None

    # Internal overrides for /server endpoints
    def _get_create_args(self, data):
        """Returns the args used to create a server for this adapter."""

        driver = self._get_user_driver()
        disk_type = 'pd-ssd' if data['size'].endswith('-ssd') else 'pd-standard'
        size = driver.ex_get_size(data['size'].split('-ssd')[0], data['region'])
        name = data['name'].replace('-', '--').replace('.', '-')

        # network = self._get_network(driver)
        #
        # volume = driver.create_volume(
        #     size=self._get_disk(data['region'], size.name.split('-')[1], size),
        #     name=name,
        #     location=data['region'],
        #     ex_disk_type=disk_type,
        #     ex_image_family=self._image_family
        # )

        return {
            "name": name,
            "size": size,
            "image": volume.extra['sourceImage'],
            "location": data['region'],
            # "ex_boot_disk": volume,
            # "ex_network": network,
            # "ex_can_ip_forward": True,
            # "ex_metadata": {'ssh-keys': '%s:%s %s' % (self.server_ssh_user, data['ssh_key'], self.server_ssh_user)}
        }

    # def _get_node_id(self, node):
    #     """Returns the node ID of a server for this adapter."""
    #     return node.name

    # Misc Internal Overrides
    # def _find_server(self, driver, id):
    #     try:
    #         return driver.ex_get_node(id)
    #     except libcloud.common.types.ProviderError:
    #         return None

    # Misc Internal Helpers (Adapter-Specific)
    # def _get_network(self, driver):
    #     try:
    #         return driver.ex_get_network('nanobox')
    #     except libcloud.common.types.ProviderError:
    #         network = driver.ex_create_network(
    #             name='nanobox',
    #             cidr=None,
    #             mode='auto',
    #             description='VPC for Nanobox servers'
    #         )
    #
    #         firewall = driver.ex_create_firewall(
    #             name='nanobox',
    #             allowed=[
    #                 {"IPProtocol": "all"},
    #             ],
    #             network=network
    #         )
    #
    #         return network
