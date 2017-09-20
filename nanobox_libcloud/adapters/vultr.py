import os
import socket
from urllib import parse
from decimal import Decimal

from flask import request

import libcloud
from nanobox_libcloud.adapters import Adapter
from nanobox_libcloud.adapters.base import RebootMixin


class Vultr(RebootMixin, Adapter):
    """
    Adapter for the Vultr service
    """

    # Adapter metadata
    id = "vtr"
    name = "Vultr (Beta)"

    # Provider-wide server properties
    server_internal_iface = 'ens3'
    server_external_iface = None

    # Provider auth properties
    auth_credential_fields = [
        ["Api-Key", "API Key"],
    ]
    auth_instructions = ('<strong>The $2.50/month server size is not available '
        'via the Vultr API. It is a sandbox size, and is limited to two '
        'instances per account, for testing purposes. You will not be able to '
        'use this server size with Nanobox.</strong><br /><br />'
        'Enter your Personal Access Token from '
        '<a href="https://my.vultr.com/settings/#settingsapi">your API Settings '
        'page</a>, and ensure you allow Any IPv4 in Access Control.')

    # Adapter-sepcific properties
    _plans = [
        ('SSD', 'Standard SSD'),
        ('DEDICATED', 'Dedicated Server')
    ]
    _sizes = {}

    def __init__(self, **kwargs):
        self.generic_credentials = {
            'key': os.getenv('VULTR_API_KEY', '')
        }

        for host in [request.host, os.getenv('APP_NAME', '') + '.nanoapp.io']:
            try:
                ip = socket.gethostbyname(host) or None
            except socket.gaierror:
                ip = None

            if ip:
                break

        self.auth_instructions += (' (If you need to be more specific about '
            'the access controls, you can use %s/32, but keep in mind that '
            'this address may change at any point in the future, and you will '
            'need to update your Vultr account accordingly to continue '
            'deploying.)') % (ip) if ip else ''

    # Internal overrides for provider retrieval
    def _get_request_credentials(self, headers):
        """Extracts credentials from request headers."""

        return {
            "key": headers.get("Auth-Api-Key", '')
        }

    def _get_user_driver(self, **auth_credentials):
        """Returns a driver instance for a user with the appropriate authentication credentials set."""

        driver = super()._get_user_driver(**auth_credentials)

        driver.list_key_pairs()

        return driver

    @classmethod
    def _get_id(cls):
        return 'vultr'

    # Internal overrides for /meta
    def get_default_region(self):
        """Gets the default region ID."""

        return '4'

    def get_default_size(self):
        """Gets the default size ID."""

        return '201'

    def get_default_plan(self):
        """Gets the default plan ID."""

        return 'SSD'

    # Internal overrides for /catalog
    def _get_plans(self, location):
        """Retrieves a list of plans for a given adapter."""

        # self._plans = []
        self._sizes = {}

        for size in self._get_generic_driver().list_sizes():
            plan = size.extra['plan_type']

            if plan in ['SATA']:
                next

            if location.id not in size.extra['available_locations']:
                next

            if plan not in self._sizes:
                self._sizes[plan] = []

            self._sizes[plan].append(size)

        return self._plans

    def _get_sizes(self, location, plan):
        """Retrieves a list of sizes for a given adapter."""

        return self._sizes[plan]

    def _get_cpu(self, location, plan, size):
        """Translates a CPU count value for a given adapter to a ServerSpec value."""

        if size.extra['vcpu_count']:
            return float(size.extra['vcpu_count'])

        return size.extra['vcpu_count']

    def _get_hourly_price(self, location, plan, size):
        """Translates an hourly cost value for a given adapter to a ServerSpec value."""

        base_price = super()._get_hourly_price(location, plan, size) or 0
        return float(base_price / (30 * 24)) or None

    # Internal overrides for /key endpoints
    def _delete_key(self, driver, key):
        return driver.delete_key_pair(key)

    # Internal overrides for /server endpoints
    def _get_create_args(self, data):
        """Returns the args used to create a server for this adapter."""

        driver = self._get_user_driver()

        location = self._find_location(driver, data['region'])
        size = self._find_size(driver, data['size'])
        # Ubuntu 16.04 x64 - Current options at https://api.vultr.com/v1/os/list
        image = self._find_image(driver, '215')
        ssh_key = self._find_ssh_key(driver, data['ssh_key'])

        return {
            "name": data['name'],
            "size": size,
            "image": image,
            "location": location,
            "ex_ssh_key_ids": [ssh_key.id]
        }

    def _get_int_ip(self, server):
        """Returns the internal IP of a server for this adapter."""
        return self._get_ext_ip(server)
