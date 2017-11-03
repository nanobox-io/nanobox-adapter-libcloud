import os
from urllib import parse
from decimal import Decimal
from operator import attrgetter

import libcloud
from nanobox_libcloud.adapters import Adapter
from nanobox_libcloud.adapters.base import RebootMixin, RenameMixin


class EC2(RebootMixin, RenameMixin, Adapter):
    """
    Adapter for the Amazon Web Services service
    """

    # Adapter metadata
    id = "aws"
    name = "Amazon Web Services EC2 (Beta)"
    server_nick_name = "EC2 instance"

    # Provider-wide server properties
    server_internal_iface = 'eth0'
    server_external_iface = None
    server_ssh_user = 'ubuntu'
    server_ssh_key_method = 'reference'

    # Provider auth properties
    auth_credential_fields = [
        ["Access-Key-Id", "Access Key ID"],
        ["Secret-Access-Key", "Secret Access Key"]
    ]
    auth_instructions = ('<a href="//console.aws.amazon.com/iam/home#/home" '
        'target="_blank">Create an IAM Account</a> in your AWS Management '
        'Console that has read/write access to EC2 instances, security groups, '
        'and ssh keys, then add the access key id and access key here.')

    # Adapter-sepcific properties
    _plans = [
        ('general_purpose', 'General Puropse'),
        ('compute_optimized', 'Compute Optimized'),
        ('memory_optimized', 'Memory Optimized'),
        ('storage_optimized', 'Storage Optimized'),
        ('accelerated_computing', 'Accelerated Computing'),
    ]
    _sizes = {}
    _image_family = 'ubuntu-1604-lts'

    def __init__(self, **kwargs):
        self.generic_credentials = {
            'key': os.getenv('EC2_KEY_ID', ''),
            'secret': os.getenv('EC2_ACCESS_KEY', ''),
            'region': self.get_default_region(),
        }

        # self._disk_cost_per_gb = {
        #     'standard': Decimal(os.getenv('EC2_MONTHLY_DISK_COST', 0)) / 30 / 24,
        #     'ssd': Decimal(os.getenv('EC2_MONTHLY_SSD_COST', 0)) / 30 / 24
        # }

    # Internal overrides for provider retrieval
    def _get_request_credentials(self, headers):
        """Extracts credentials from request headers."""

        return {
            "key": headers.get("Auth-Access-Key-Id", ''),
            "secret": parse.unquote(headers.get("Auth-Secret-Access-Key", '')),
            "region": parse.unquote(headers.get("Region-Id",
                                                self.get_default_region())),
        }

    # def _get_user_driver(self, **auth_credentials):
    #     """Returns a driver instance for a user with the appropriate authentication credentials set."""
    #
    #     auth_credentials['auth_type'] = 'SA'
    #
    #     return super()._get_user_driver(**auth_credentials)

    @classmethod
    def _get_id(cls):
        return 'ec2'

    # Internal overrides for /meta
    def get_default_region(self):
        """Gets the default region ID."""

        return 'us-west-2'

    def get_default_size(self):
        """Gets the default size ID."""

        return 't2.nano'

    def get_default_plan(self):
        """Gets the default plan ID."""

        return 'general_purpose'

    # Internal overrides for /catalog
    def _get_locations(self):
        """Retrieves a list of datacenter locations."""
        return self._get_generic_driver().list_regions()

    def _get_plans(self, location):
        """Retrieves a list of plans for a given adapter."""

        self._sizes[location] = {
            'general_purpose': [],
            'compute_optimized': [],
            'memory_optimized': [],
            'storage_optimized': [],
            'accelerated_computing': [],
        }

        keys = {
            't': 'general_purpose',
            'm': 'general_purpose',
            'c': 'compute_optimized',
            'x': 'memory_optimized',
            'r': 'memory_optimized',
            'h': 'storage_optimized',
            'i': 'storage_optimized',
            'd': 'storage_optimized',
            'p': 'accelerated_computing',
            'g': 'accelerated_computing',
        }

        for size in self._switch_region(self._get_generic_driver(),
                                        location).list_sizes():
            plan = keys[size.id[0] if not size.id[0:2] == 'cr'[0:2]
                        else size.id[1]]

            self._sizes[location][plan].append(size)

        return self._plans

    def _get_sizes(self, location, plan):
        """Retrieves a list of sizes for a given adapter."""

        return self._sizes[location][plan]

    def _get_location_id(self, location):
        """Translates a location ID for a given adapter to a ServerSpec value."""

        return location

    def _get_location_name(self, location):
        """Translates a location name for a given adapter to a ServerSpec value."""

        return location

    def _get_cpu(self, location, plan, size):
        """Translates a CPU count value for a given adapter to a ServerSpec value."""

        if hasattr(size.extra, 'cpu') and size.extra['cpu']:
            return float(size.extra['cpu'])

        return size.extra.get('cpu', 0.5)

    def _get_disk(self, location, plan, size):
        """Translates a disk size value for a given adapter to a ServerSpec value."""

        gb_ram = Decimal(size.ram) / 1024

        for test, value in [
            # if <, disk is #
            [1, 20],
            [2, 30],
            [4, 40],
            [8, 60],
        ]:
            if gb_ram < test:
                return value

        return int(gb_ram * 10) + size.disk

    # def _get_hourly_price(self, location, plan, size):
    #     """Translates an hourly cost value for a given adapter to a ServerSpec value."""
    #
    #     base_price = super()._get_hourly_price(location, plan, size) or 0
    #     disk_size = self._get_disk(location, plan, size)
    #
    #     return (base_price + float(
    #         disk_size * self._disk_cost_per_gb['ssd' if plan.endswith('-ssd') else 'standard'])) or None

    # Internal overrides for /key endpoints
    def _create_key(self, driver, key):
        return driver.import_key_pair_from_string(key['id'], key['key'])

    # Internal overrides for /server endpoints
    def _get_create_args(self, data):
        """Returns the args used to create a server for this adapter."""

        # Reconnect to the correct region before continuing
        driver = self._get_user_driver()
        size = self._find_size(driver, data['size'])
        image = self._find_image(driver,
            'ubuntu/images/hvm-ssd/ubuntu-xenial-16.04-amd64-server-*')
        sec_groups = ['Nanobox']
        extant_groups = [group for group in driver.ex_list_security_groups()
                         if group in sec_groups]
        if len(extant_groups) < len(sec_groups):
            for group in sec_groups:
                if group not in extant_groups:
                    sgid = driver.ex_create_security_group(group,
                        'Security group policy created by Nanobox.')['group_id']
                    if group == 'Nanobox':
                        sgobj = driver.ex_get_security_groups(group_ids=[sgid])[0]
                        for proto, low, high in [
                                                    # ('tcp', 0, 65535),
                                                    # ('udp', 0, 65535),
                                                    # ('icmp', -1, -1)
                                                    (-1, -1, -1)
                                                ]:
                            driver.ex_authorize_security_group_ingress(
                                sgid, low, high, ['0.0.0.0/0'], None, proto)
                            try:
                                driver.ex_authorize_security_group_egress(
                                    sgid, low, high, ['0.0.0.0/0'], None, proto)
                            except libcloud.common.exceptions.BaseHTTPError as e:
                                if 'InvalidPermission.Duplicate' not in e.message:
                                    raise e

        return {
            "name": data['name'],
            "size": size,
            "image": image,
            "ex_keyname": data['ssh_key'],
            "ex_security_groups": sec_groups,
            "ex_metadata": {
                'Nanobox': 'true',
                'Nanobox-Name': data['name'],
            },
            "ex_blockdevicemappings": [
                {
                    'DeviceName': '/dev/sda1',
                    'Ebs': {
                        'VolumeType': 'gp2',
                        'VolumeSize': self._get_disk(None, None, size),
                        'DeleteOnTermination': True,
                    }
                }
            ],
            # "ex_assign_public_ip": True,
            "ex_terminate_on_shutdown": False,
        }

    # Misc Internal Overrides
    def _find_image(self, driver, id):
        return sorted(driver.list_images(ex_filters={
                'architecture': 'x86_64',
                'name': id,
            }), key=attrgetter('name'), reverse=True)[0]

    def _find_ssh_key(self, driver, id, public_key=None):
        try:
            return driver.get_key_pair(id)
        except libcloud.compute.types.KeyPairDoesNotExistError:
            pass

    def _rename_server(self, server, name):
        """Renames server."""
        return server.driver.ex_create_tags(server, {
            'Name': name,
            'Nanobox-Name': name,
            'Nanobox': 'true',
        })

    # Misc Internal Methods (Adapter-Specific)
    def _switch_region(self, driver, region):
        driver.__init__(key=driver.key, secret=driver.secret,
                        token=driver.token, region=region)
        return driver
