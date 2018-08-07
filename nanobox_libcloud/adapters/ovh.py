import os
import socket
from urllib import parse
from decimal import Decimal

import libcloud
from nanobox_libcloud.adapters import Adapter


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
    server_ssh_user = 'ubuntu'
    server_ssh_key_method = 'object'

    # Provider auth properties
    auth_credential_fields = [
        ["App-Key", "Application Key"],
        ["App-Secret", "Application Secret"],
        ["Consumer-Key", "Consumer Key"],
        ["Project-Id", "Project ID"],
        ["App-Region", "Application Region"],
    ]
    auth_instructions = ('Generate API credentials by visiting the Create Tokens '
        'page for '
        '<a href="https://api.ovh.com/createToken/index.cgi?GET=/*&PUT=/*&POST=/*&DELETE=/*">Europe and Africa</a>, or '
        '<a href="https://ca.api.ovh.com/createToken/index.cgi?GET=/*&PUT=/*&POST=/*&DELETE=/*">Everywhere Else</a>, '
        'and filling in the required information. For your Project ID, extract '
        'that value from the URL of your cloud project information page in your '
        'OVH Control Panel. Your Application Region is <code>.</code> for Europe '
        'and Africa, or <code>ca</code> for the rest of the world.')

    # Adapter-sepcific properties
    _plans = [
        ('eg', 'General Purpose'),
        ('cpu', 'CPU'),
        ('ram', 'RAM'),
        ('gpu', 'GPU'),
    ]
    _sizes = {}
    _pricing = {}

    def __init__(self, **kwargs):
        self.generic_credentials = {
            'key': os.getenv('OVH_APP_KEY', ''),
            'secret': os.getenv('OVH_APP_SECRET', ''),
            'ex_consumer_key': os.getenv('OVH_CONSUMER_KEY', ''),
            'ex_project_id': os.getenv('OVH_PROJECT_ID', ''),
            'ex_datacenter': os.getenv('OVH_APP_REGION', '')
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
            "key": headers.get("Auth-App-Key", ''),
            "secret": headers.get("Auth-App-Secret", ''),
            "ex_consumer_key": headers.get("Auth-Consumer-Key", ''),
            "ex_project_id": headers.get("Auth-Project-Id", ''),
            "ex_datacenter": headers.get("Auth-App-Region", '')
        }

    def _get_user_driver(self, **auth_credentials):
        """Returns a driver instance for a user with the appropriate authentication credentials set."""

        driver = super()._get_user_driver(**auth_credentials)

        driver.list_key_pairs()

        return driver

    @classmethod
    def _get_id(cls):
        return 'ovh'

    # Internal overrides for /meta
    def get_default_region(self):
        """Gets the default region ID."""

        return 'BHS3'

    def get_default_size(self):
        """Gets the default size ID."""

        return 'b2-7'

    def get_default_plan(self):
        """Gets the default plan ID."""

        return 'eg'

    # Internal overrides for /catalog
    def _get_plans(self, location):
        """Retrieves a list of plans for a given adapter."""

        # self._plans = []
        self._sizes = {
            'eg': [],
            'cpu': [],
            'ram': [],
            'gpu': [],
        }

        for size in self._get_generic_driver().list_sizes(location):
            plan = size.extra['type'].split('.')[-1]

            if 'win' in size.name\
                    or 'flex' in size.name\
                    or plan not in self._sizes\
                    or location.id not in size.extra['region']:
                next
            else:
                self._sizes[plan].append(size)

        return self._plans

    def _get_sizes(self, location, plan):
        """Retrieves a list of sizes for a given adapter."""

        return self._sizes[plan]

    def _get_size_id(self, location, plan, size):
        """Translates a server size ID for a given adapter to a ServerSpec value."""
        return size.name

    def _get_cpu(self, location, plan, size):
        """Translates a CPU count value for a given adapter to a ServerSpec value."""

        if size.extra['vcpus']:
            return float(size.extra['vcpus'])

        return size.extra['vcpus']

    def _get_hourly_price(self, location, plan, size):
        """Translates an hourly cost value for a given adapter to a ServerSpec value."""

        if size.id not in self._pricing:
            self._pricing[size.id] = self._get_generic_driver()\
                .ex_get_pricing(size.id)
        return float(self._pricing[size.id]['hourly']) or None

    def _get_monthly_price(self, location, plan, size):
        """Translates a monthly cost value for a given adapter to a ServerSpec value."""

        if size.id not in self._pricing:
            self._pricing[size.id] = self._get_generic_driver()\
                .ex_get_pricing(size.id)
        return float(self._pricing[size.id]['monthly']) or None

    # Internal overrides for /server endpoints
    def _get_create_args(self, data):
        """Returns the args used to create a server for this adapter."""

        driver = self._get_user_driver()

        location = self._find_location(driver, data['region'])
        size = self._find_size(driver, location, data['size'])
        image = self._find_image(driver, location, 'Ubuntu 16.04')

        keyname = '-'.join(data['name'].split('-')[:-1])
        try:
            driver.get_key_pair(keyname, location)
        except Exception as e:
            if 'No key named' in str(e):
                driver.import_key_pair_from_string(keyname, data['ssh_key'], location)
            else:
                raise

        return {
            "name": data['name'],
            "size": size,
            "image": image,
            "location": location,
            "ex_keyname": keyname
        }

    def _get_int_ip(self, server):
        """Returns the internal IP of a server for this adapter."""
        return self._get_ext_ip(server)

    # Internal overrides of misc internal methods
    def _find_size(self, driver, location, id):
        for size in driver.list_sizes(location):
            if size.name == id:
                return size

    def _find_image(self, driver, location, id):
        for image in driver.list_images(location):
            if image.name == id:
                return image
