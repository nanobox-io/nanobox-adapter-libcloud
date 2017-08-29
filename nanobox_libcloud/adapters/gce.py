import os
from decimal import Decimal

from nanobox_libcloud.adapters import Adapter


class Gce(Adapter):
    """
    Adapter for the Google Compute Engine service
    """
    # Adapter metadata
    id = "gce"
    name = "Google Compute Engine"
    server_nick_name = "instance"

    # Provider auth properties
    auth_credential_fields = [
        ["Service-Email", "Service Email"],
        ["Service-Key", "Service Key"],
        ["Project-Id", "Project ID"]
    ]
    auth_instructions = ""

    def __init__(self, **kwargs):
        self.generic_credentials = {
            'user_id': os.getenv('GCE_SERVICE_EMAIL'),
            'key': os.getenv('GCE_SERVICE_KEY'),
            'project': os.getenv('GCE_PROJECT_ID')
        }

        self._disk_cost_per_gb = Decimal(os.getenv('GCE_MONTHLY_DISK_COST')) / 30 / 24

    @classmethod
    def get_default_region(cls):
        """Gets the default region ID."""
        return 'us-west1-a'

    @classmethod
    def get_default_size(cls):
        """Gets the default size ID."""
        return '1000'

    @classmethod
    def get_default_plan(cls):
        """Gets the default plan ID."""
        return cls.id

    @classmethod
    def get_cpu(cls, size):
        """Translates a RAM size value for a given adapter to a ServerSpec value."""
        if size.extra['guestCpus']:
            return float(size.extra['guestCpus'])
        return size.extra['guestCpus']

    @classmethod
    def get_disk(cls, size):
        """Translates a disk size value for a given adapter to a ServerSpec value."""
        gb_ram = Decimal(size.ram) / 1024
        for test, value in [
            [1, 20],
            [2, 30],
            [4, 40],
            [8, 60],
        ]:
            if gb_ram < test:
                return value
        return int(gb_ram * 10)

    @classmethod
    def get_hourly_price(cls, size):
        """Translates an hourly cost value for a given adapter to a ServerSpec value."""
        base_price = super().get_hourly_price(size) or 0
        disk_size = cls.get_disk(size)
        return (base_price + float(disk_size * cls._disk_cost_per_gb)) or None

    @classmethod
    def _get_request_credentials(cls, headers):
        """Extracts credentials from request headers."""
        return {
            "user_id": headers.get("Service-Email"),
            "key": headers.get("Service-Key"),
            "project": headers.get("Project-Id")
        }

    @classmethod
    def _get_user_driver(cls, **auth_credentials):
        """Returns a driver instance for a user with the appropriate authentication credentials set."""
        auth_credentials['auth_type'] = 'SA'
        return super()._get_user_driver(**auth_credentials)
