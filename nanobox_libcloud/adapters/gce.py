import os
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
        ["Client-Id", "Client ID"],
        ["Client-Secret", "Client Secret"],
        ["Project-Id", "Project ID"]
    ]
    auth_instructions = ""

    def __init__(self, **kwargs):
        self.generic_credentials = {
            'user_id': os.getenv('GENERIC_GCE_CLIENT_ID'),
            'key': os.getenv('GENERIC_GCE_CLIENT_SECRET'),
            'project': os.getenv('GENERIC_GCE_PROJECT_ID')
        }

    @classmethod
    def get_default_region(cls):
        """Gets the default region ID."""
        return None

    @classmethod
    def get_default_size(cls):
        """Gets the default size ID."""
        return None

    @classmethod
    def get_default_plan(cls):
        """Gets the default plan ID."""
        return None

    @classmethod
    def _get_request_credentials(cls, headers):
        """Extracts credentials from request headers."""
        return {
            "user_id": headers.get("Client-Id"),
            "key": headers.get("Client-Secret"),
            "project": headers.get("Project-Id")
        }

    @classmethod
    def _get_user_driver(cls, **auth_credentials):
        """Returns a driver instance for a user with the appropriate authentication credentials set."""
        auth_credentials['auth_type'] = 'SA'
        return super()._get_user_driver(**auth_credentials)
