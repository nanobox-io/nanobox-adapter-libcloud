import os
import tempfile
from urllib import parse
import hashlib
from base64 import standard_b64encode as b64enc
from decimal import Decimal

from flask import after_this_request

import libcloud
from libcloud.compute.base import NodeAuthPassword
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
    server_internal_iface = 'eth0'
    server_external_iface = None
    server_ssh_user = 'nanobox'
    server_ssh_auth_method = 'password'
    server_ssh_key_method = 'object'

    # Provider auth properties
    auth_credential_fields = [
        ["Subscription-Id", "Subscription ID"],
        ["Key-File", "Key"]
    ]
    auth_instructions = ('Using Azure is fairly complex. First, create a '
        'self-signed certificate. Then, follow the instructions '
        '<a href="https://docs.microsoft.com/en-us/azure/azure-api-management-certs">here</a> '
        'to add the certificate to your account. Finally, enter your '
        'subscription ID and the contents of the certificate\'s key file above.')

    # Adapter-sepcific properties
    _plans = [
        ('standard', 'Standard'),
        ('highspeed', 'High Speed'),
    ]
    _sizes = {}

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

        return 'West US 2'

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

    def _get_cpu(self, location, plan, size):
        """Translates a CPU count value for a given adapter to a ServerSpec value."""

        if size.extra['cores'] == 'Shared':
            return 0.5
        if size.extra['cores']:
            return float(size.extra['cores'])

        return size.extra['cores']

    # Internal overrides for /server endpoints
    def _get_create_args(self, data):
        """Returns the args used to create a server for this adapter."""

        driver = self._get_user_driver()
        size = self._find_size(driver, data['size'])
        image = self._find_image(driver, 'Ubuntu Server 16.04 LTS')

        try:
            driver.ex_create_storage_service(
                # name = data['name'],
                name = 'nanobox',
                location = data['region']
            )
        except libcloud.common.types.LibcloudError:
            pass

        try:
            driver.ex_create_cloud_service(
                name = data['name'],
                location = data['region']
            )
        except libcloud.common.types.LibcloudError:
            pass

        cs_list = []
        while len(cs_list) < 1:
            try:
                cs_list = [serv for serv in driver.ex_list_cloud_services()
                    if serv.service_name == data['name']
                        and serv.hosted_service_properties.status == 'Created']
            except AttributeError:
                pass

        return {
            "name": data['name'],
            "size": size,
            "image": image,
            "auth": NodeAuthPassword(self._get_password(data['name'])),
            "ex_new_deployment": True,
            "ex_admin_user_id": 'nanobox',
            # "ex_storage_service_name": data['name'],
            "ex_storage_service_name": 'nanobox',
            "ex_cloud_service_name": data['name']
        }

    def _get_password(self, server):
        """Returns the password of a server for this adapter."""
        base = server.name if hasattr(server, 'name') else server

        return b64enc(hashlib.sha256(base.encode('utf-8')).digest()).decode('utf-8')

    def _destroy_server(self, server):
        driver = self._get_user_driver()
        name = server.name

        result = server.destroy()

        while self._find_server(driver, name) is not None:
            pass

        driver.ex_destroy_cloud_service(name)

        return result

    # Misc internal method overrides
    def _find_image(self, driver, name):
        return sorted([img for img in driver.list_images()
            if img.name == name and 'amd64' in img.id
                and 'DAILY' not in img.id], key=id, reverse=True)[0]

    def _find_server(self, driver, id):
        for server in driver.list_nodes(ex_cloud_service_name = id):
            if server.id == id:
                return server
