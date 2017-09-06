import typing
from decimal import Decimal

import libcloud
from libcloud.compute.base import NodeDriver, NodeLocation, NodeSize, Node

from nanobox_libcloud.utils import models


class AdapterBase(type):
    """
    Metaclass for Adapter classes registering defined adapters.
    """

    registry = {}

    def __new__(mcs, name, bases, attrs):
        cls = super(AdapterBase, mcs).__new__(mcs, name, bases, attrs)

        if name != 'Adapter':
            mcs.register(cls)

        return cls

    @classmethod
    def register(mcs, cls):
        adapter_id = cls.get_id()

        # Check if there is an existing adapter with the same id
        if adapter_id in mcs.registry:
            raise ValueError(
                "Cannot register adapter {}, there already exists an adapter with id {}.".format(
                    cls.__name__,
                    adapter_id,
                )
            )

        # Actually register the adapter
        mcs.registry[adapter_id] = cls


class Adapter(object, metaclass=AdapterBase):
    """
    Base class for Nanobox libcloud adapters. Implements basic functionality that should work for most libcloud drivers
    which can be overridden by subclasses for specific drivers.

    If subclasses are placed in the same package as this module they will automatically be discovered.
    """

    # Adapter metadata
    id = None  # type: str
    name = ''  # type: str
    server_nick_name = 'server'  # type: str

    # Provider-wide server properties
    server_internal_iface = 'eth1'  # type: str
    server_external_iface = 'eth0'  # type: str
    server_ssh_user = 'root'  # type: str
    server_ssh_auth_method = 'key'  # type: str
    server_ssh_key_method = 'reference'  # type: str
    server_bootstrap_script = 'https://s3.amazonaws.com/tools.nanobox.io/bootstrap/ubuntu.sh'  # type: str

    # Provider auth properties
    auth_credential_fields = []  # type: typing.Tuple[str, str]
    auth_instructions = ""  # type: str

    generic_credentials = {}  # type: dict
    _generic_driver = None  # type: NodeDriver
    _user_driver = None  # type: NodeDriver

    # Controller entry points
    def do_meta(self) -> typing.Dict[str, typing.Any]:
        """Returns the metadata of this adapter."""
        return models.AdapterMeta(
            id=self.id,
            name=self.name,
            server_nick_name=self.server_nick_name,
            default_region=self.get_default_region(),
            default_size=self.get_default_size(),
            default_plan=self.get_default_plan(),
            can_reboot=self.can_reboot(),
            can_rename=self.can_rename(),
            internal_iface=self.server_internal_iface,
            external_iface=self.server_external_iface,
            ssh_user=self.server_ssh_user,
            ssh_auth_method=self.server_ssh_auth_method,
            ssh_key_method=self.server_ssh_key_method,
            bootstrap_script=self.server_bootstrap_script,
            auth_credential_fields=self.auth_credential_fields,
            auth_instructions=self.auth_instructions,
        ).to_nanobox()

    def do_catalog(self) -> typing.List[dict]:
        """Returns the catalog for this adapter."""
        # Build catalog
        catalog = []

        try:
            # Use generic driver because there are no auth tokens
            for location in self._get_locations():
                catalog.append(models.ServerRegion(
                    id=self._get_location_id(location),
                    name=self._get_location_name(location),
                    plans=[
                        models.ServerPlan(
                            id=plan_id,
                            name=plan_name,
                            specs=[
                                models.ServerSpec(
                                    id=self._get_size_id(location, plan_id, size),
                                    ram=self._get_ram(location, plan_id, size),
                                    cpu=self._get_cpu(location, plan_id, size),
                                    disk=self._get_disk(location, plan_id, size),
                                    transfer=self._get_transfer(location, plan_id, size),
                                    dollars_per_hr=self._get_hourly_price(location, plan_id, size),
                                    dollars_per_mo=self._get_monthly_price(location, plan_id, size)
                                ) for size in self._get_sizes(location, plan_id)
                            ]
                        ) for plan_id, plan_name in self._get_plans(location)
                    ]
                ).to_nanobox())
        except libcloud.common.types.ProviderError:
            # TODO: Get cached data...
            pass

        return catalog

    def do_verify(self, headers) -> bool:
        """Verify the account credentials."""
        try:
            self._get_user_driver(**self._get_request_credentials(headers))
        except libcloud.common.types.ProviderError:
            return False
        else:
            return True

    def do_server_create(self, headers, data) -> typing.Dict[str, typing.Any]:
        """Create a server with a certain provider."""
        try:
            driver = self._get_user_driver(**self._get_request_credentials(headers))
            result = driver.create_node(**self._get_create_args(data))
        except libcloud.common.types.ProviderError as err:
            return {"error": err.value if hasattr(err, 'value') else err, "status": 500}
        else:
            return {"data": {"id": self._get_node_id(result)}, "status": 201}

    def do_server_query(self, headers, id) -> typing.Dict[str, typing.Any]:
        """Query a server with a certain provider."""
        try:
            driver = self._get_user_driver(**self._get_request_credentials(headers))
            server = self._find_server(driver, id)
        except libcloud.common.types.ProviderError as err:
            return {"error": err.value if hasattr(err, 'value') else err, "status": 500}
        else:
            if not server:
                return {"error": self.server_nick_name + " not found", "status": 404}

            return {"data": models.ServerInfo(
                id=self._get_node_id(server),
                status=server.state,
                name=server.name,
                external_ip=self._get_ext_ip(server),
                internal_ip=self._get_int_ip(server),
                password=self._get_password(server)
            ).to_nanobox(), "status": 201}

    def do_server_cancel(self, headers, id) -> typing.Union[bool, typing.Dict[str, typing.Any]]:
        """Cancel a server with a certain provider."""
        try:
            driver = self._get_user_driver(**self._get_request_credentials(headers))
            server = self._find_server(driver, id)

            if not server:
                return {"error": self.server_nick_name + " not found", "status": 404}

            result = server.destroy()
        except libcloud.common.types.ProviderError as err:
            return {"error": err.value if hasattr(err, 'value') else err, "status": 500}
        else:
            return True

    # Provider retrieval
    def _get_driver_class(self) -> typing.Type[NodeDriver]:
        """Returns the libcloud driver class for the id of this adapter."""
        return libcloud.get_driver(libcloud.DriverType.COMPUTE, self.get_id())

    def _get_user_driver(self, **auth_credentials) -> NodeDriver:
        """Returns a driver instance for a user with the appropriate authentication credentials set."""
        if self._user_driver is None:
            self._user_driver = self._get_driver_class()(**auth_credentials)

        return self._user_driver

    def _get_generic_driver(self) -> NodeDriver:
        """Returns a driver instance for an anonymous user."""
        if self._generic_driver is None:
            self._generic_driver = self._get_driver_class()(**self.generic_credentials)

        return self._generic_driver

    # Internal (overridable) methods for /meta
    @classmethod
    def get_id(cls) -> str:
        """"Returns the id of this adapter."""
        if not cls.id:
            cls._config_error("No id set for adapter {cls}.")

        return cls.id

    @classmethod
    def get_default_region(cls) -> str:
        """Returns the id of the default region for this adapter."""
        raise NotImplementedError()

    @classmethod
    def get_default_size(cls) -> str:
        """Returns the id of the default server size for this adapter."""
        raise NotImplementedError()

    @classmethod
    def get_default_plan(cls) -> str:
        """Returns the id of the default plan for this adapter."""
        raise NotImplementedError()

    @classmethod
    def can_reboot(cls) -> bool:
        """Returns whether this adapter allows servers to be rebooted."""
        return hasattr(cls, 'do_server_reboot') and callable(cls.do_server_reboot)

    @classmethod
    def can_rename(cls) -> bool:
        """Returns whether this adapter allows servers to be renamed."""
        return hasattr(cls, 'do_server_rename') and callable(cls.do_server_rename)

    # Internal (overridable) methods for /catalog
    def _get_locations(self) -> typing.List[NodeLocation]:
        """Retrieves a list of datacenter locations."""
        return self._get_generic_driver().list_locations()

    def _get_plans(self, location) -> typing.List[typing.Tuple[str, str]]:
        """Retrieves a list of plans."""
        return [('standard', 'Standard')]

    def _get_sizes(self, location, plan) -> typing.List[NodeSize]:
        """Retrieves a list of sizes."""
        return self._get_generic_driver().list_sizes(location)

    def _get_location_id(self, location) -> str:
        """Translates a location ID for a given adapter to a ServerSpec value."""
        return location.id

    def _get_location_name(self, location) -> str:
        """Translates a location name for a given adapter to a ServerSpec value."""
        return location.name

    def _get_size_id(self, location, plan, size) -> str:
        """Translates a server size ID for a given adapter to a ServerSpec value."""
        return size.id

    def _get_ram(self, location, plan, size) -> int:
        """Translates a RAM size value for a given adapter to a ServerSpec value."""
        return int(size.ram)

    @classmethod
    def _get_cpu(cls, location, plan, size) -> float:
        """Returns a CPU count value for a given adapter as a ServerSpec value."""
        raise NotImplementedError()

    def _get_disk(self, location, plan, size) -> int:
        """Translates a disk size value for a given adapter to a ServerSpec value."""

        return int(size.disk)

    def _get_transfer(self, location, plan, size) -> int:
        """Translates a transfer limit value for a given adapter to a ServerSpec value."""
        return int(size.bandwidth)

    def _get_hourly_price(self, location, plan, size) -> float:
        """Translates an hourly cost value for a given adapter to a ServerSpec value."""
        if size.price:
            return float(size.price)

        return size.price

    def _get_monthly_price(self, location, plan, size) -> float:
        """Translates an hourly cost value for a given adapter to a monthly cost ServerSpec value."""
        return float(Decimal(self._get_hourly_price(location, plan, size) or 0) * 30 * 24) or None

    # Internal (overridable) methods for /server endpoints
    @classmethod
    def _get_create_args(cls, data) -> typing.Dict[str, typing.Any]:
        """Returns the args used to create a server for this adapter."""
        raise NotImplementedError()

    @classmethod
    def _get_request_credentials(cls, headers) -> typing.Dict[str, str]:
        """Extracts credentials from request headers."""
        raise NotImplementedError()

    def _get_node_id(self, node) -> str:
        """Returns the node ID of a server for this adapter."""
        return node.id

    def _get_ext_ip(self, server) -> str:
        """Returns the external IP of a server for this adapter."""
        return server.public_ips[0]

    def _get_int_ip(self, server) -> str:
        """Returns the internal IP of a server for this adapter."""
        return server.private_ips[0]

    def _get_password(self, server) -> typing.Optional[str]:
        """Returns the password of a server for this adapter."""
        return None

    # Misc internal methods
    def _find_server(self, driver, id) -> Node:
        for server in driver.list_nodes():
            if server.id == id:
                return server

    @classmethod
    def _config_error(cls, msg, **kwargs):
        raise ValueError(msg.format(cls=cls.__name__, **kwargs))


class RebootMixin(object):
    """
    Mixin for adapters to signify that servers can be rebooted.
    """

    def do_server_reboot(self, headers, id) -> typing.Union[bool, typing.Dict[str, typing.Any]]:
        """Reboot a server with a certain provider."""
        try:
            driver = self._get_user_driver(**self._get_request_credentials(headers))
            server = self._find_server(driver, id)

            if not server:
                return {"error": self.server_nick_name + " not found", "status": 404}

            if not server.reboot():
                return {"error": "Reboot failed.", "status": 500}
        except libcloud.common.types.ProviderError as err:
            return {"error": err.value if hasattr(err, 'value') else err, "status": 500}
        else:
            return True


class RenameMixin(object):
    """
    Mixin for adapters to signify that servers can be renamed.
    """

    def do_server_rename(self, headers, id, data) -> typing.Union[bool, typing.Dict[str, typing.Any]]:
        """Rename a server with a certain provider."""
        try:
            driver = self._get_user_driver(**self._get_request_credentials(headers))
            server = self._find_server(driver, id)

            if not server:
                return {"error": self.server_nick_name + " not found", "status": 404}

            # TODO: Actually rename the server.
        except libcloud.common.types.ProviderError as err:
            return {"error": err.value if hasattr(err, 'value') else err, "status": 500}
        else:
            return True
