import os
import socket
from urllib import parse
from decimal import Decimal

import libcloud
from libcloud.compute.base import NodeAuthSSHKey
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
        '<a href="https://docs.microsoft.com/en-us/azure/azure-resource-manager/resource-group-create-service-principal-portal?view=azure-cli-latest">this link</a> '
        'to find and/or generate the values above. Your app registration can '
        'use any values you like, as this app won\'t be exposed to any end '
        'users, but select <code>Web app / API</code> as the application type. '
        'Whatever expiration you set for the Authentication Key will determine '
        'how often you need to generate a new one, and update your Nanobox '
        'hosting provider account settings. When assigning your app a role, '
        'select <code>Contributor</code> to grant Nanobox permission to create '
        'and manage servers & associated resources. For the Cloud Environment, '
        'either use the value <code>default</code> to access the global Azure '
        'infrastructure, or one of <code>AzureChinaCloud</code>, '
        '<code>AzureGermanCloud</code>, or <code>AzureUSGovernment</code> to '
        'access that particular specialized infrastructure. Note that your '
        'Azure account must have access to the infrastructure you select.')

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

    def __init__(self, **kwargs):
        self.generic_credentials = {
            'subscription_id': os.getenv('AZR_SUBSCRIPTION_ID', ''),
            'tenant_id': os.getenv('AZR_TENANT_ID', ''),
            'key': os.getenv('AZR_APPLICATION_ID', ''),
            'secret': os.getenv('AZR_AUTHENTICATION_KEY', ''),
            'cloud_environment': os.getenv('AZR_CLOUD_ENVIRONMENT', 'default')
        }

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
        # Ubuntu 16.04 x64
        image = self._find_image(driver, '')
        ssh_key = NodeAuthSSHKey(data['ssh_key'])

        return {
            "name": data['name'],
            "size": size,
            "image": image,
            "location": location,
            "auth": ssh_key
        }
