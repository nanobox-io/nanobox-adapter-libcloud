import os
import socket
from urllib import parse
from decimal import Decimal
from currency_converter import CurrencyConverter

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
    server_internal_iface = 'eth0'
    server_external_iface = None
    server_bootstrap_timeout = 900

    # Provider auth properties
    auth_credential_fields = [
        ["Access-Key", "Access Key"],
        ["Api-Token", "API Token"],
    ]
    auth_instructions = ('Your Access Key can be found in the Tokens section of '
        '<a href="https://cloud.scaleway.com/#/credentials">your credentials '
        'page</a>, directly above the token list. Use the <code>Create new '
        'token</code> button to create an API Token for use by Nanobox.')

    # Adapter-sepcific properties
    _plans = [
        ('Start', 'Start'),
        ('Baremetal', 'Bare Metal'),
        ('Pro', 'Pro'),
        ('Deprecated', 'Deprecated\n(UPGRADE TO NEW\n"Start"\nSIZE ASAP)'),
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

        return 'START1-XS'

    def get_default_plan(self):
        """Gets the default plan ID."""

        return 'Start'

    # Internal overrides for /catalog
    def _get_plans(self, location):
        """Retrieves a list of plans for a given adapter."""

        # self._plans = []
        self._sizes = {}

        for size in self._get_generic_driver().list_sizes():
            if size.id.upper().startswith('START'):
                plan = 'Start'
            elif size.id.upper().startswith('VC'):
                plan = 'Deprecated'
            elif size.extra['baremetal']:
                plan = 'Baremetal'
            else:
                plan = 'Pro'

            if plan not in self._sizes:
                self._sizes[plan] = []

            if size.extra['arch'] not in ['arm', 'arm64']:
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

    def _get_hourly_price(self, location, plan, size):
        """Translates an hourly cost value for a given adapter to a ServerSpec value."""

        c = CurrencyConverter('http://www.ecb.europa.eu/stats/eurofxref/eurofxref.zip')
        return c.convert(float(size.price or 0), 'EUR', 'USD') or None

    def _get_monthly_price(self, location, plan, size):
        """Translates a monthly cost value for a given adapter to a ServerSpec value."""

        c = CurrencyConverter('http://www.ecb.europa.eu/stats/eurofxref/eurofxref.zip')
        return c.convert(float(size.extra.get('monthly', 0) or 0), 'EUR', 'USD') or None

    # Internal overrides for /key endpoints
    def _create_key(self, driver, key):
        return driver.import_key_pair_from_string(key['id'], key['key'])

    # Internal overrides for /server endpoints
    def _get_create_args(self, data):
        """Returns the args used to create a server for this adapter."""

        driver = self._get_user_driver()

        location = self._find_location(driver, data['region'])
        size = self._find_size(driver, data['size'])
        image = self._find_image(driver, data['region'], size,
                                 'Ubuntu Xenial')

        if location is None:
            raise libcloud.common.exceptions.exception_from_message(404,
                  'Invalid region')

        if size is None:
            raise libcloud.common.exceptions.exception_from_message(404,
                  'Invalid server size')

        if image is None:
            raise libcloud.common.exceptions.exception_from_message(404,
                  'Unable to find required server image')

        return {
            'name': data['name'],
            'size': size,
            'image': image,
            'region': location,
        }

    def _get_node_id(self, node):
        """Returns the node ID of a server for this adapter."""
        return '%s::%s' % (node.extra['region'], node.id)

    # Misc internal overrides
    def _find_image(self, driver, region, size, id):
        for image in driver.list_images(region):
            if (image.name == id and
                image.extra['arch'] == size.extra['arch'] and
                image.extra['size'] <= size.extra['max_disk']):
                    return image

    def _find_server(self, driver, id):
        (region, id) = id.split('::', 2)
        for server in driver.list_nodes(region):
            if server.id == id:
                return server

        return super()._find_server(driver, id)

    def _find_usable_servers(self, driver):
        return []
