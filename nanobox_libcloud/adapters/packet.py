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
    server_internal_iface = 'bond0'
    server_external_iface = None

    # Provider auth properties
    auth_credential_fields = [
        ["Api-Key", "API Key"],
        ["Project-Id", "Project ID"],
    ]
    auth_instructions = ('Your API Key can be found (or created) on the API Keys '
        'tab of your Packet account. Your Project ID is available in the Manage '
        'tab, just below your project\'s row in the table, or on the project\'s '
        'detail page. You will need to create a project if you don\'t have one '
        'already.')

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

        return self._get_generic_driver().list_sizes()

    def _get_cpu(self, location, plan, size):
        """Translates a CPU count value for a given adapter to a ServerSpec value."""

        if size.extra['cpus']:
            return float(size.extra['cpus'])

        return size.extra['cpus']

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

    # Misc internal overrides
    def _find_size(self, driver, id):
        for size in driver.list_sizes():
            if size.id == id:
                return size

    def _find_server(self, driver, id):
        for server in driver.list_nodes(self.project_id):
            if server.id == id:
                return server
