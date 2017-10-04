import os
import tempfile
import logging
from urllib import parse
import hashlib
from base64 import standard_b64encode as b64enc
from decimal import Decimal
from time import sleep
import redis

from flask import after_this_request
from celery.signals import task_postrun

import libcloud
from libcloud.compute.base import NodeAuthPassword, Node
from libcloud.compute.deployment import ScriptDeployment
from nanobox_libcloud import tasks
from nanobox_libcloud.adapters import Adapter
from nanobox_libcloud.adapters.base import KeyInstallMixin, RebootMixin


class AzureClassic(RebootMixin, KeyInstallMixin, Adapter):
    """
    Adapter for the Classic Microsoft Azure service
    """

    # Adapter metadata
    id = "azc"
    name = "Microsoft Azure Classic (Experimental)"
    server_nick_name = "virtual machine"

    # Provider-wide server properties
    server_internal_iface = 'eth0'
    server_external_iface = None
    server_ssh_user = 'nanobox'
    server_ssh_auth_method = 'password'
    server_ssh_key_method = 'object'

    # Provider auth properties
    auth_credential_fields = [
        ["Subscription-Id", "Subscription ID"],
        ["Key-File", "Certificate"]
    ]
    auth_instructions = ('Using Azure CLassic is fairly complex. First, create a '
        'self-signed certificate. Then, follow the instructions '
        '<a href="https://docs.microsoft.com/en-us/azure/azure-api-management-certs">here</a> '
        'to add the certificate to your account. Finally, enter your '
        'subscription ID and the contents of the private certificate file above, '
        'using <code>\n</code> to replace new lines.')

    # Adapter-sepcific properties
    _plans = [
        ('standard', 'Standard'),
        ('highspeed', 'High Speed'),
    ]
    _sizes = {}

    def __init__(self, **kwargs):
        self.generic_credentials = {
            'subscription_id': os.getenv('AZC_SUB_ID', ''),
            'key': os.getenv('AZC_KEY', '')
        }

    def do_server_create(self, headers, data):
        """Create a server with a certain provider."""
        try:
            self._get_user_driver(**self._get_request_credentials(headers))
        except (libcloud.common.types.LibcloudError, libcloud.common.exceptions.BaseHTTPError) as err:
            return {"error": err.value if hasattr(err, 'value') else repr(err), "status": 500}
        else:
            r = redis.StrictRedis(host=os.getenv('DATA_REDIS_HOST'))
            r.setex('%s:server:%s:status' % (self.id, data['name']), 180, 'ordering')
            tasks.azure.azure_create_classic.delay(dict(headers), data)
            return {"data": {"id": data['name']}, "status": 201}

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

            try:
                @after_this_request
                def clr_tmp_user(response):
                    os.remove(key_file)
                    return response
            except AttributeError:
                @task_postrun.connect
                def clr_tmp_user(**kwargs):
                    os.remove(key_file)

        try:
            self._user_driver.list_locations()
        except AttributeError:
            pass

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

        logger = logging.getLogger(__name__)
        driver = self._get_user_driver()
        storage = data['name'].rsplit('-', 1)[0].replace('-', '')
        size = self._find_size(driver, data['size'])
        image = self._find_image(driver, 'Ubuntu Server 16.04 LTS')

        try:
            storage_pending = driver._is_storage_service_unique(storage)
        except AttributeError:
            storage_pending = True

        if storage_pending:
            logger.info('Creating storage service...')
            try:
                driver.ex_create_storage_service(
                    name = storage,
                    location = data['region']
                )
            except libcloud.common.types.LibcloudError:
                pass

        logger.info('Waiting for storage service...')
        while storage_pending:
            try:
                storage_pending = driver._is_storage_service_unique(storage)
            except AttributeError:
                pass
            finally:
                sleep(0.5)

        try:
            cs_list = [serv for serv in driver.ex_list_cloud_services()
                if serv.service_name == data['name']
                    and serv.hosted_service_properties.status == 'Created']
        except AttributeError:
            cs_list = []

        if len(cs_list) < 1:
            logger.info('Creating cloud service...')
            try:
                driver.ex_create_cloud_service(
                    name = data['name'],
                    location = data['region']
                )
            except libcloud.common.types.LibcloudError:
                pass

        logger.info('Waiting for cloud service...')
        while len(cs_list) < 1:
            try:
                cs_list = [serv for serv in driver.ex_list_cloud_services()
                    if serv.service_name == data['name']
                        and serv.hosted_service_properties.status == 'Created']
            except AttributeError:
                pass
            finally:
                sleep(0.5)

        logger.info('Creating server...')
        return {
            "name": data['name'],
            "size": size,
            "image": image,
            "auth": NodeAuthPassword(self._get_password(data['name'])),
            "ex_new_deployment": True,
            "ex_admin_user_id": self.server_ssh_user,
            "ex_storage_service_name": storage,
            "ex_cloud_service_name": data['name']
        }

    def _get_int_ip(self, server):
        """Returns the internal IP of a server for this adapter."""
        return server.public_ips[0] if len(server.public_ips) > 0 else None

    def _install_key(self, server, key_data):
        """Installs key on server."""
        server.driver._connect_and_run_deployment_script(
            task = ScriptDeployment('echo "%s %s" >> ~/.ssh/authorized_keys' % (key_data['key'], key_data['id'])),
            node = server,
            ssh_hostname = server.public_ips[0],
            ssh_port = 22,
            ssh_username = self.server_ssh_user,
            ssh_password = self._get_password(server),
            ssh_key_file = None,
            ssh_timeout = 10,
            timeout = 300,
            max_tries = 3
        )

        return True

    def _destroy_server(self, server):
        driver = self._get_user_driver()
        name = server.name

        result = server.destroy()

        with open(driver.key_file, 'r') as key_file:
            tasks.azure.azure_destroy_classic.delay({
                'subscription_id': driver.subscription_id,
                'key': key_file.read()}, name)

        return result

    # Misc internal method overrides
    def _find_image(self, driver, name):
        return sorted([img for img in driver.list_images()
            if img.name == name and 'amd64' in img.id
                and 'DAILY' not in img.id], key=id, reverse=True)[0]

    def _find_server(self, driver, id):
        err = None

        try:
            for server in driver.list_nodes(id):
                if server.id == id:
                    return server
        except (libcloud.common.types.LibcloudError, libcloud.common.exceptions.BaseHTTPError, AttributeError) as e:
            err = e

        r = redis.StrictRedis(host=os.getenv('DATA_REDIS_HOST'))
        status = r.get('%s:server:%s:status' % (self.id, id))

        if status:
            return Node(
                id = id,
                name = id,
                state = status,
                public_ips = [],
                private_ips = [],
                driver = driver,
                extra = {}
            )
        elif err:
            raise err

    # Misc internal-only methods
    def _get_password(self, server):
        """Returns the password of a server for this adapter."""
        base = server.name if hasattr(server, 'name') else server

        return b64enc(hashlib.sha256(base.encode('utf-8')).digest()).decode('utf-8')
