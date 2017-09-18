import os
import socket
from urllib import parse
from decimal import Decimal

import libcloud
from nanobox_libcloud.adapters import Adapter
from nanobox_libcloud.adapters.base import RebootMixin


class Ovh(Adapter):
    """
    Adapter for the OVH service
    """

    # Adapter metadata
    id = "ovh"
    name = "OVH (Beta)"

    # Provider-wide server properties
    server_internal_iface = 'ens3'
    server_external_iface = None

    # Provider auth properties
    auth_credential_fields = [
        ["App-Region", "Application Region"],
        ["App-Key", "Application Key"],
        ["App-Secret", "Application Secret"],
        ["Consumer-Key", "Consumer Key"],
        ["Project-Id", "Project ID"],
    ]
    auth_instructions = (''
        '')

    # Adapter-sepcific properties
    _plans = [
        ('SSD', 'Standard SSD'),
        ('DEDICATED', 'Dedicated Server')
    ]
    _sizes = {}

    def __init__(self, **kwargs):
        self.generic_credentials = {
            # 'host': (os.getenv('OVH_APP_REGION', '') + '.api.ovh.com').lstrip('.'),
            'key': os.getenv('OVH_APP_KEY', ''),
            'secret': os.getenv('OVH_APP_SECRET', ''),
            'ex_consumer_key': os.getenv('OVH_CONSUMER_KEY', ''),
            'ex_project_id': os.getenv('OVH_PROJECT_ID', '')
        }

        # try:
        #     ip = socket.gethostbyname(os.getenv('APP_NAME', '') + '.nanoapp.io') or None
        # except socket.gaierror:
        #     ip = None
        #
        # self.auth_instructions += (' (If you need to be more specific about '
        #     'the access controls, you can use %s/32, but keep in mind that '
        #     'this address may change at any point in the future, and you will '
        #     'need to update your OVH account accordingly to continue '
        #     'deploying.)') % (ip) if ip else ''

    # Internal overrides for provider retrieval
    def _get_request_credentials(self, headers):
        """Extracts credentials from request headers."""

        return {
            # "host": (headers.get("Auth-App-Region", '') + '.api.ovh.com').lstrip('.'),
            "key": headers.get("Auth-App-Key", ''),
            "secret": headers.get("Auth-App-Secret", ''),
            "ex_consumer_key": headers.get("Auth-Consumer-Key", ''),
            "ex_project_id": headers.get("Auth-Project-Id", '')
        }

    # def _get_user_driver(self, **auth_credentials):
    #     """Returns a driver instance for a user with the appropriate authentication credentials set."""
    #
    #     driver = super()._get_user_driver(**auth_credentials)
    #
    #     driver.list_key_pairs()
    #
    #     return driver

    @classmethod
    def _get_id(cls):
        return 'ovh'

    # Internal overrides for /meta
    def get_default_region(self):
        """Gets the default region ID."""

        return ''

    def get_default_size(self):
        """Gets the default size ID."""

        return ''

    def get_default_plan(self):
        """Gets the default plan ID."""

        return ''

    # Internal overrides for /catalog
    # def _get_plans(self, location):
    #     """Retrieves a list of plans for a given adapter."""
    #
    #     # self._plans = []
    #     self._sizes = {}
    #
    #     for size in self._get_generic_driver().list_sizes():
    #         plan = size.extra['plan_type']
    #
    #         if plan in ['SATA']:
    #             next
    #
    #         if location.id not in size.extra['available_locations']:
    #             next
    #
    #         if plan not in self._sizes:
    #             self._sizes[plan] = []
    #
    #         self._sizes[plan].append(size)
    #
    #     return self._plans

    # def _get_sizes(self, location, plan):
    #     """Retrieves a list of sizes for a given adapter."""
    #
    #     return self._sizes[plan]

    def _get_cpu(self, location, plan, size):
        """Translates a CPU count value for a given adapter to a ServerSpec value."""

        if size.extra['vcpus']:
            return float(size.extra['vcpus'])

        return size.extra['vcpus']

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
        # Ubuntu 16.04 x64 - Current options at TODO
        image = self._find_image(driver, '')

        return {
            "name": data['name'],
            "size": size,
            "image": image,
            "location": location,
            "ex_keyname": data['ssh_key']
        }

    def _get_int_ip(self, server):
        """Returns the internal IP of a server for this adapter."""
        return self._get_ext_ip(server)
