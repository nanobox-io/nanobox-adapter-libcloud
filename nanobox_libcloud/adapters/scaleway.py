import os
import socket
from urllib import parse
from decimal import Decimal

from flask import request

import libcloud
from nanobox_libcloud.adapters import Adapter
from nanobox_libcloud.adapters.base import RebootMixin


class Scaleway(RebootMixin, Adapter):
    """
    Adapter for the Scaleway service
    """

    # Adapter metadata
    id = "sw"
    name = "Scaleway (Beta)"

    # Provider-wide server properties
    server_internal_iface = 'ens3'
    server_external_iface = None

    # Provider auth properties
    auth_credential_fields = [
        ["Access Key", "Access Key"],
        ["Api-Token", "API Token"],
    ]
    auth_instructions = (''
        '')

    # Adapter-sepcific properties
    _plans = [
        ('Starter', 'Starter'),
        ('Baremetal', 'Bare Metal'),
        ('Intensive', 'Intensive'),
    ]
    _sizes = {}

    def __init__(self, **kwargs):
        self.generic_credentials = {
            'key': os.getenv('SCALEWAY_ACCESS_KEY', ''),
            'secret': os.getenv('SCALEWAY_API_TOKEN', ''),
        }

    # Internal overrides for provider retrieval
    def _get_request_credentials(self, headers):
        """Extracts credentials from request headers."""

        return {
            "key": headers.get("Auth-Access-Key", ''),
            "secret": headers.get("Auth-Api-Token", ''),
        }

    def _get_user_driver(self, **auth_credentials):
        """Returns a driver instance for a user with the appropriate authentication credentials set."""

        driver = super()._get_user_driver(**auth_credentials)

        driver.list_nodes()

        return driver

    @classmethod
    def _get_id(cls):
        return 'scaleway'

    # Internal overrides for /meta
    def get_default_region(self):
        """Gets the default region ID."""

        return 'par1'

    def get_default_size(self):
        """Gets the default size ID."""

        return 'VC1S'

    def get_default_plan(self):
        """Gets the default plan ID."""

        return 'Starter'

    # Internal overrides for /catalog
    def _get_plans(self, location):
        """Retrieves a list of plans for a given adapter."""

        # self._plans = []
        self._sizes = {}

        for size in self._get_generic_driver().list_sizes():
            plan = size.extra['range']

            if plan not in self._sizes:
                self._sizes[plan] = []

            if size.extra['arch'] not in ['arm']:
                self._sizes[plan].append(size)

        return self._plans

    def _get_sizes(self, location, plan):
        """Retrieves a list of sizes for a given adapter."""

        return self._sizes[plan]

    def _get_cpu(self, location, plan, size):
        """Translates a CPU count value for a given adapter to a ServerSpec value."""

        if size.extra['cores']:
            return float(size.extra['cores'])

        return size.extra['cores']

    def _get_monthly_price(self, location, plan, size):
        """Translates an monthly cost value for a given adapter to a ServerSpec value."""

        return float(size.extra.get('monthly', 0)) or None

    # Internal overrides for /key endpoints
    # def _delete_key(self, driver, key):
    #     return driver.delete_key_pair(key)

    # Internal overrides for /server endpoints
    def _get_create_args(self, data):
        """Returns the args used to create a server for this adapter."""

        driver = self._get_user_driver()

        location = self._find_location(driver, data['region'])
        size = self._find_size(driver, data['size'])
        image = self._find_image(driver, data['region'],
                                 'Ubuntu Xenial (16.04 latest)')
        # ssh_key = self._find_ssh_key(driver, data['ssh_key'])

        return {
            'name': data['name'],
            'size': size,
            'image': image,
            'region': location,
            # 'ex_ssh_key_ids': [ssh_key.id]
        }

    def _get_node_id(self, node):
        """Returns the node ID of a server for this adapter."""
        return '%s::%s' % (node.extra['region'], node.id)

    # Misc internal overrides
    def _find_image(self, driver, region, id):
        for image in driver.list_images(region):
            if image.name == id and image.extra['arch'] == 'x86_64':
                return image

    def _find_server(self, driver, id):
        (region, id) = id.split('::', 2)
        for server in driver.list_nodes(region):
            if server.id == id:
                return server
