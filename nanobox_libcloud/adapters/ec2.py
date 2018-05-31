import ipaddress
import os
import re
import time
from decimal import Decimal
from operator import attrgetter
from urllib import parse
from urllib.request import urlopen

try:
    import simplejson as json
except ImportError:
    import json

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
    configuration_fields = [
        {
            'key': 'vpc_id',
            'label': 'VPC ID',
            'description': 'The ID of a VPC to launch ec2 instances within.',
            'rebuild': True,
        },
        {
            'key': 'sg_id',
            'label': 'Security Group ID',
            'description': 'An additional, custom Security Group ID to attach to the ec2 instances',
            'rebuild': True,
        },
        {
            'key': 'az_distribution',
            'label': 'Availability Zone Distribution',
            'description': 'The number of AZs to distribute instances across.',
            'default': '1',
            'rebuild': True,
        },
    ]

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
    _prices = None

    def __init__(self, **kwargs):
        self.generic_credentials = {
            'key': os.getenv('EC2_KEY_ID', ''),
            'secret': os.getenv('EC2_ACCESS_KEY', ''),
            'region': self.get_default_region(),
        }

    # Internal overrides for provider retrieval
    def _get_request_credentials(self, headers):
        """Extracts credentials from request headers."""

        return {
            "key": headers.get("Auth-Access-Key-Id", ''),
            "secret": parse.unquote(headers.get("Auth-Secret-Access-Key", '')),
            "region": parse.unquote(headers.get("Region-Id",
                                                self.get_default_region())),
        }

    def _get_user_driver(self, **auth_credentials):
        """Returns a driver instance for a user with the appropriate authentication credentials set."""
        driver = super()._get_user_driver(**auth_credentials)

        driver.list_key_pairs()

        return driver

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

    def _get_hourly_price(self, location, plan, size):
        """Translates an hourly cost value for a given adapter to a ServerSpec value."""

        base_price = super()._get_hourly_price(location, plan, size) or 0

        return (base_price + self._calculate_disk_cost(location, plan, size)) or None

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
            'ubuntu/images/%s-ssd/ubuntu-xenial-16.04-amd64-server-*' %
            ('hvm' if 'currentGeneration' in size.extra and
                   size.extra['currentGeneration'] == 'Yes' else 'ebs'))

        segments = data['name'].split('.')
        instance = int(segments[-1] if len(segments) > 3 else segments[-2])
        az_distribution = max(min(int(data.get('config', {}).get('az_distribution', 1)),
            len(driver.list_locations())), 1)
        az = driver.list_locations()[(instance - 1) % az_distribution]

        vpc_id = data.get('config', {}).get('vpc_id')
        netlist = driver.ex_list_networks() if vpc_id is None \
             else driver.ex_list_networks(network_ids=[vpc_id])
        vpcs = self._find_usable_resources(netlist)
        vpc_id = vpcs[0].id if len(vpcs) > 0 else None
        if vpc_id is None:
            vpc = driver.ex_create_network('10.10.0.0/16', 'Nanobox')
            if vpc:
                driver.ex_create_tags(vpc, {'Nanobox': 'true'})
                gw = driver.ex_create_internet_gateway('Nanobox GW')
                driver.ex_create_tags(gw, {'Nanobox': 'true'})
                driver.ex_attach_internet_gateway(gw, vpc)
                tables = driver.ex_list_route_tables(filters={'vpc-id': vpc.id})
                if len(tables) > 0:
                    table = tables[0]
                else:
                    table = driver.ex_create_route_table(vpc, 'Nanobox Routes')
                driver.ex_create_route(table, '0.0.0.0/0', internet_gateway=gw)
                vpc_id = vpc.id

        subnet = self._get_subnet(vpc_id, az.name)

        group_names = ['Nanobox']
        extant_groups = [group.name for group in \
                         self._find_usable_resources(
                              driver.ex_get_security_groups(
                                     filters=({'vpc-id': vpc_id}
                                              if vpc_id is not None
                                              else None)
                              ))]

        sec_groups = []
        for group in group_names:
            sg = None
            if group in extant_groups:
                try:
                    sg = self._find_usable_resources(
                              driver.ex_get_security_groups(
                                  filters=({
                                      'group-name': group,
                                      'vpc-id': vpc_id
                                  }
                                  if vpc_id is not None
                                  else None)
                              ))[0]
                except Exception as e:
                    pass

            if sg is None:
                sg_id = driver.ex_create_security_group(group,
                    'Security group policy created by Nanobox.',
                    vpc_id=vpc_id)['group_id']
                sg = self._find_usable_resources(
                          driver.ex_get_security_groups(
                              filters=({
                                  'group-id': sg_id,
                                  'vpc-id': vpc_id
                              }
                              if vpc_id is not None
                              else None)
                          ))[0]
                driver.ex_create_tags(sg, {'Nanobox': 'true'})
                if group == 'Nanobox':
                    self._add_rules_to_sec_group(driver, sg.id)

            sec_groups.append(sg.id)

        # Add a custom security group if specified via the adapter config
        ex_sg_id = data.get('config', {}).get('sg_id')
        if ex_sg_id is not None:
            sec_groups.append(ex_sg_id)

        response = {
            "name": data['name'],
            "size": size,
            "image": image,
            "location": az,
            "ex_keyname": data['ssh_key'],
            "ex_security_group_ids": sec_groups,
            "ex_metadata": {
                'Nanobox': 'true',
                'Nanobox-Name': data['name'],
                'AZ-Distribution': az_distribution,
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
            "ex_subnet": subnet,
            # "ex_assign_public_ip": True,
            "ex_terminate_on_shutdown": False,
        }

        return response

    def _get_server_config(self, server):
        return [
            {'key': 'az_distribution', 'value': self._config_get_az_dist(server)},
            {'key': 'vpc_id', 'value': self._config_get_vpc(server)},
        ]

    # Misc Internal Overrides
    def _find_image(self, driver, id):
        return sorted(self._find_usable_resources(driver.list_images(ex_filters={
                'architecture': 'x86_64',
                'image-type': 'machine',
                'name': id,
                'root-device-type': 'ebs',
                'state': 'available',
            })), key=attrgetter('name'), reverse=True)[0]

    def _find_ssh_key(self, driver, id, public_key=None):
        try:
            return driver.get_key_pair(id)
        except libcloud.compute.types.KeyPairDoesNotExistError:
            pass

    def _find_usable_servers(self, driver):
        return self._find_usable_resources(driver.list_nodes())

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

    def _calculate_disk_cost(self, location, plan, size):
        source = 'https://a0.awsstatic.com/pricing/1/ebs/pricing-ebs.js'
        cache = '/tmp/ebs-pricing.json'

        if not self._prices:
            if os.path.isfile(cache) and os.path.getmtime(cache) > time.time() - 86400:
                with open(cache) as json_file:
                    self._prices = json.load(json_file)
            else:
                with urlopen(source) as js_file:
                    raw = js_file.read().decode('utf-8')

                json_data = json.loads(re.search(r'callback\(\n(.*)\n\);', raw)[1])
                self._prices = {}

                for region in json_data['config']['regions']:
                    self._prices[region['region']] = \
                        region['types'][0]['values'][0]['prices']['USD']

                with open(cache, 'w') as json_file:
                    json.dump(self._prices, json_file)

        gb = self._get_disk(location, plan, size)
        hourly = float(self._prices.get(location, 0)) / (24 * 30)

        return gb * hourly

    def _add_rules_to_sec_group(self, driver, sgid):
        sgobj = driver.ex_get_security_groups(group_ids=[sgid])[0]
        # Try to create a single rule that allows everything,
        # then fall back to one for each protocol
        for proto, low, high, skip_others in [
                    (-1, -1, -1, True),
                    ('tcp', 0, 65535, False),
                    ('udp', 0, 65535, False),
                    ('icmp', -1, -1, False)
                ]:
            try:
                driver.ex_authorize_security_group_ingress(
                    sgid, low, high, ['0.0.0.0/0'], None, proto)
                try:
                    driver.ex_authorize_security_group_egress(
                        sgid, low, high, ['0.0.0.0/0'], None, proto)
                except libcloud.common.exceptions.BaseHTTPError as e:
                    if 'InvalidPermission.Duplicate' not in e.message:
                        raise e
                if skip_others:
                    break
            except libcloud.common.exceptions.BaseHTTPError as e:
                if 'InvalidPermission.Malformed' not in e.message and \
                   'UnknownParameter' not in e.message:
                    raise e

    def _get_subnet(self, vpc_id=None, az_id=None):
        if vpc_id is None or az_id is None:
            return None

        driver = self._get_user_driver()

        vpcs = self._find_usable_resources(
            driver.ex_list_networks(network_ids=[vpc_id])
        )

        if len(vpcs) <= 0:
            return None

        subnets = self._find_usable_resources(
            driver.ex_list_subnets(filters={
                'vpc-id': vpc_id,
                'availabilityZone': az_id,
            })
        )

        if len(subnets) > 0:
            return subnets[0]

        nets = list(ipaddress.ip_network(vpcs[0].cidr_block).subnets(new_prefix=24))
        cidr = str(nets[ord(az_id[-1]) % len(nets)])
        subnet = driver.ex_create_subnet(vpc_id, cidr, az_id, 'Nanobox-%s' % (az_id))
        if subnet and driver.ex_create_tags(subnet, {'Nanobox': 'true'}):
            subnet.extra['tags']['Nanobox'] = 'true'
        driver.ex_modify_subnet_attribute(subnet, 'auto_public_ip', True)

        return subnet

    def _config_get_vpc(self, server):
        return server.extra.get('vpc_id')

    def _config_get_az_dist(self, server):
        return server.extra.get('tags', {}).get('AZ-Distribution', 1)

    def _find_usable_resources(self, all_resources):
        our_resources = [resource for resource in all_resources
                         if 'Nanobox' in resource.extra.get('tags', {}) and
                         resource.extra['tags']['Nanobox'] == 'true']

        our_ids = [resource.id for resource in our_resources]

        allowed_resources = [resource for resource in all_resources
                             if ('Nanobox' not in resource.extra.get('tags', {}) or
                                 resource.extra['tags']['Nanobox'] != 'false') and
                             resource.id not in our_ids]

        return our_resources + allowed_resources
