import os
import socket
import re
import redis
from time import sleep
from urllib import parse
from decimal import Decimal

import libcloud
from libcloud.compute.base import NodeAuthSSHKey
from nanobox_libcloud import tasks
from nanobox_libcloud.adapters import Adapter
from nanobox_libcloud.adapters.base import RebootMixin


class AzureARM(RebootMixin, Adapter):
    """
    Adapter for the Azure Resource Manager service
    """

    # Adapter metadata
    id = "azr"
    name = "Microsoft Azure (Beta)"
    server_nick_name = "virtual machine"

    # Provider-wide server properties
    server_internal_iface = 'eth0'
    server_external_iface = None
    server_ssh_user = 'nanobox'
    server_ssh_key_method = 'object'

    # Provider auth properties
    auth_credential_fields = [
        ["Subscription-Id", "Subscription ID"],
        ["Tenant-Id", "Tenant ID"],
        ["Application-Id", "Application ID"],
        ["Authentication-Key", "Authentication Key"],
        ["Cloud-Environment", "Cloud Environment"],
    ]
    auth_instructions = ('Use the instructions at '
        '<a href="https://docs.microsoft.com/en-us/azure/'
        'azure-resource-manager/resource-group-create-service-principal-portal?'
        'view=azure-cli-latest">this link</a> to find and/or generate the '
        'values above. Your app registration can use any values you like, as '
        'this app won\'t be exposed to any end users, but select <code>Web app '
        '/ API</code> as the application type. Whatever expiration you set for '
        'the Authentication Key will determine how often you need to generate '
        'a new one and update your Nanobox hosting provider account settings. '
        'When assigning your app a role, select <code>Contributor</code> to '
        'grant Nanobox permission to create and manage servers and associated '
        'resources. For the Cloud Environment, either use the value '
        '<code>default</code> to access the global Azure infrastructure, or '
        'one of <code>AzureChinaCloud</code>, <code>AzureGermanCloud</code>, '
        'or <code>AzureUSGovernment</code> to access that particular '
        'specialized infrastructure. Note that your Azure account must have '
        'access to the infrastructure you select.')

    # Adapter-sepcific properties
    _plans = [
        ('basic', 'Basic'),
        ('standard', 'General Purpose'),
        ('burstable', 'Burstable (Preview)'),
        ('compute_opt', 'Compute Optimized'),
        ('memory_opt', 'Memory Optimized'),
        ('storage_opt', 'Storage Optimized'),
        ('gpu', 'GPU'),
        ('high_performance', 'High Performance'),
    ]
    _sizes = {}
    _rates = None

    def __init__(self, **kwargs):
        self.generic_credentials = {
            'subscription_id': os.getenv('AZR_SUBSCRIPTION_ID', ''),
            'tenant_id': os.getenv('AZR_TENANT_ID', ''),
            'key': os.getenv('AZR_APPLICATION_ID', ''),
            'secret': os.getenv('AZR_AUTHENTICATION_KEY', ''),
            'cloud_environment': os.getenv('AZR_CLOUD_ENVIRONMENT', 'default')
        }

    def do_server_create(self, headers, data):
        """Create a server with a certain provider."""
        result = super().do_server_create(headers, data)
        if 'data' in result:
            r = redis.StrictRedis(host=os.getenv('DATA_REDIS_HOST'))
            r.setex('%s:server:%s:status' % (self.id, result['data']['id']), 180, 'ordering')

        return result

    # Internal overrides for provider retrieval
    def _get_request_credentials(self, headers):
        """Extracts credentials from request headers."""

        return {
            "subscription_id": headers.get("Auth-Subscription-Id", ''),
            "tenant_id": headers.get("Auth-Tenant-Id", ''),
            "key": headers.get("Auth-Application-Id", ''),
            "secret": headers.get("Auth-Authentication-Key", ''),
            "cloud_environment": headers.get("Auth-Cloud-Environment", 'default')
        }

    def _get_user_driver(self, **auth_credentials):
        """Returns a driver instance for a user with the appropriate authentication credentials set."""

        driver = super()._get_user_driver(**auth_credentials)

        driver.list_nodes()

        return driver

    @classmethod
    def _get_id(cls):
        return 'azure_arm'

    # Internal overrides for /meta
    def get_default_region(self):
        """Gets the default region ID."""

        return 'westus2'

    def get_default_size(self):
        """Gets the default size ID."""

        return 'Basic_A0'

    def get_default_plan(self):
        """Gets the default plan ID."""

        return 'basic'

    # Internal overrides for /catalog
    def _get_plans(self, location):
        """Retrieves a list of plans for a given adapter."""

        self._sizes = {
            'basic': [],
            'standard': [],
            'burstable': [],
            'compute_opt': [],
            'memory_opt': [],
            'storage_opt': [],
            'gpu': [],
            'high_performance': [],
        }

        for size in self._get_generic_driver().list_sizes(location):
            plan = {
                'A': 'standard',
                'B': 'burstable',
                'D': 'standard',
                'F': 'compute_opt',
                'E': 'memory_opt',
                'G': 'memory_opt',
                'M': 'memory_opt',
                'L': 'storage_opt',
                'N': 'gpu',
                'H': 'high_performance',
            }.get(
                size.id.replace('Standard_', '').replace('Basic_', '')[:1], size.id)

            if plan not in [
                'standard',
                'burstable',
                'compute_opt',
                'memory_opt',
                'storage_opt',
                'gpu',
                'high_performance',
            ]:
                plan = 'standard'

            if size.id[:6] == 'Basic_':
                plan = 'basic'

            if size.id[-6:] != '_Promo':
                self._sizes[plan].append(size)

        return self._plans

    def _get_sizes(self, location, plan):
        """Retrieves a list of sizes for a given adapter."""

        return self._sizes[plan]

    def _get_cpu(self, location, plan, size):
        """Translates a CPU count value for a given adapter to a ServerSpec value."""

        if size.extra['numberOfCores'] == 'Shared':
            return 0.5
        if size.extra['numberOfCores']:
            return float(size.extra['numberOfCores'])

        return size.extra['numberOfCores']

    def _get_hourly_price(self, location, plan, size):
        """Translates an hourly cost value for a given adapter to a ServerSpec value."""

        region_map = {
            'eastasia': 'AP East',
            'southeastasia': 'AP Southeast',
            'australiaeast': 'AU East',
            'australiasoutheast': 'AU Southeast',
            'brazilsouth': 'BR South',
            'canadacentral': 'CA Central',
            'canadaeast': 'CA East',
            'northeurope': 'EU North',
            'westeurope': 'EU West',
            'centralindia': 'IN Central',
            'southindia': 'IN South',
            'westindia': 'IN West',
            'japaneast': 'JA East',
            'japanwest': 'JA West',
            'koreacentral': 'KR Central',
            'koreasouth': 'KR South',
            'uksouth': 'UK South',
            'ukwest': 'UK West',
            'centralus': 'US Central',
            'eastus': 'US East',
            'eastus2': 'US East 2',
            'northcentralus': 'US North Central',
            'southcentralus': 'US South Central',
            'westus': 'US West',
            'westus2': 'US West 2',
            'westcentralus': 'US West Central',
            # '': 'UK North',
            # '': 'UK South 2',
            # '': 'DoD (US)',
            # '': 'US DoD',
            # '': 'Gov (US)',
            # '': 'USGov',
            # '': 'US Gov AZ',
            # '': 'US Gov TX',
        }

        vm_size = '%s VM' % (re.sub(
            r"(?i:Standard_(A)(\d+)$|(Standard_(?:[BDEFGL]|N[CV]))S?(\d+m?)s?(?:-\d+s?)?|(Standard_M\d+)(?:-\d+)?)",
            r'\1\2\3\4\5',
            size.id.replace('Basic_', 'BASIC.')))

        base_price = float(
            (self._get_rates()['Virtual Machines'].get(vm_size, {})\
                    .get(region_map[location.id])
                or self._get_rates()['Virtual Machines'].get(vm_size, {})
                    .get('', {})
            ).get('Compute Hours', 0))

        if not base_price:
            return None

        ip_price = float(self._get_rates()['Networking']\
            ['Public IP Addresses']['']['IP Address Hours'])

        disk_price = 0

        return (base_price + ip_price + disk_price) or None

    # Internal overrides for /server endpoints
    def _get_create_args(self, data):
        """Returns the args used to create a server for this adapter."""

        driver = self._get_user_driver()

        app = data['name'].rsplit('-', 1)[0]
        location = self._find_location(driver, data['region'])
        size = self._find_size(driver, location, data['size'])
        image = self._find_image(driver, location, 'Canonical', 'UbuntuServer', '16.04-LTS')
        ssh_key = NodeAuthSSHKey(data['ssh_key'])

        if not self._find_resource_group(driver, app):
            driver.ex_create_resource_group(app, data['region'])

        network = self._find_network(driver, app)
        if not network:
            network = driver.ex_create_network(app, data['region'], app)

        ipaddr = driver.ex_create_public_ip(data['name'], app, location)

        subnet = self._find_subnet(driver, network, 'default')
        nic = driver.ex_create_network_interface(data['name'], subnet, app, location, ipaddr)

        return {
            "name": data['name'],
            "size": size,
            "image": image,
            "location": location,
            "auth": ssh_key,
            "ex_resource_group": app,
            "ex_storage_account": None,
            "ex_user_name": self.server_ssh_user,
            "ex_nic": nic,
            "ex_use_managed_disks": True,
            "ex_storage_account_type": 'Standard_LRS'
        }

    def _get_node_id(self, node):
        """Returns the node ID of a server for this adapter."""
        return node.name

    def _destroy_server(self, server):
        driver = self._get_user_driver()
        tasks.azure_arm.azure_destroy_arm.delay({
            'subscription_id': driver.subscription_id,
            'tenant_id': driver.tenant_id,
            'key': driver.key,
            'secret': driver.secret,
            'cloud_environment': driver.cloud_environment}, server.name)
        return True

    # Internal overrides for misc internal methods
    def _find_size(self, driver, location, id):
        for size in driver.list_sizes(location):
            if size.id == id:
                return size

    def _find_image(self, driver, location, vendor, product, version):
        return driver.list_images(location, vendor, product, version, 'latest')[0]

    def _find_server(self, driver, id):
        for server in driver.list_nodes():
            if server.name == id:
                return server

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

    # Internal-only methods
    def _find_resource_group(self, driver, name):
        for group in driver.ex_list_resource_groups():
            if group.name == name:
                return group

    def _find_network(self, driver, name):
        for net in driver.ex_list_networks():
            if net.name == name:
                return net

    def _find_subnet(self, driver, network, name='default'):
        for subnet in driver.ex_list_subnets(network):
            if subnet.name == name:
                return subnet

    def _get_rates(self):
        if not self._rates:
            driver = self._get_generic_driver()
            self._rates = {}

            # Pay As You Go pricing
            for mtr in driver.ex_get_ratecard('0003P')['Meters']:
                if mtr['MeterStatus'] == 'Active'\
                        and mtr['MeterCategory'] in [
                            'Networking',
                            'Storage',
                            'Virtual Machines']\
                        and mtr['MeterSubCategory'].startswith((
                            'A0 ','A1 ','A2 ','A3 ','A4 ','A5 ','A6 ','A7 ',
                            'A8 ','A9 ','A10 ','A11 ','BASIC.','Locally ',
                            'Public ','Standard_','Virtual '))\
                        and 'Windows' not in mtr['MeterSubCategory']\
                        and 'Low Priority' not in mtr['MeterSubCategory']:

                    if mtr['MeterCategory'] not in self._rates:
                        self._rates[mtr['MeterCategory']] = {}

                    if mtr['MeterSubCategory'] not in self._rates\
                            [mtr['MeterCategory']]:
                        self._rates[mtr['MeterCategory']]\
                            [mtr['MeterSubCategory']] = {}

                    if mtr['MeterRegion'] not in self._rates\
                            [mtr['MeterCategory']][mtr['MeterSubCategory']]:
                        self._rates[mtr['MeterCategory']]\
                            [mtr['MeterSubCategory']][mtr['MeterRegion']] = {}

                    self._rates[mtr['MeterCategory']]\
                        [mtr['MeterSubCategory']][mtr['MeterRegion']]\
                        [mtr['MeterName']] = mtr['MeterRates']['0']

        return self._rates
