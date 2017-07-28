import typing


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
    name = None  # type: str
    server_nick_name = None  # type: str

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

    @classmethod
    def get_id(cls) -> str:
        if not cls.id:
            cls._config_error("No id set for adapter {cls}.")
        return cls.id

    @classmethod
    def get_name(cls) -> str:
        if not cls.name:
            cls._config_error("No name set for adapter {cls}.")
        return cls.name

    @classmethod
    def get_server_nick_name(cls) -> str:
        if not cls.server_nick_name:
            cls._config_error("No server nick name set for adapter {cls}.")
        return cls.server_nick_name

    @classmethod
    def get_provider_capabilities(cls) -> typing.Dict[str, bool]:
        return {
            'can_reboot': cls._can_reboot(),
            'can_rename': cls._can_rename(),
        }

    @classmethod
    def get_server_properties(cls) -> typing.Dict[str, str]:
        return {
            'internal_iface': cls.server_internal_iface,
            'external_iface': cls.server_external_iface,
            'ssh_user': cls.server_ssh_user,
            'ssh_auth_method': cls.server_ssh_auth_method,
            'ssh_key_method': cls.server_ssh_key_method,
            'bootstrap_script': cls.server_bootstrap_script,
        }

    @classmethod
    def get_auth_properties(cls) -> typing.Dict[str, typing.Any]:
        return {
            'credential_fields': [{'key': field[0], 'label': field[1]} for field in cls.auth_credential_fields],
            'instructions': cls.auth_instructions,
        }

    @classmethod
    def _can_reboot(cls):
        return hasattr(cls, 'reboot_server') and callable(cls.reboot_server)

    @classmethod
    def _can_rename(cls):
        return hasattr(cls, 'rename_server') and callable(cls.rename_server)

    @classmethod
    def _config_error(cls, msg, **kwargs):
        raise ValueError(msg.format(cls=cls.__name__, **kwargs))


class RebootMixin(object):
    """
    Mixin for adapters to signify that servers can be rebooted.
    """
    @classmethod
    def reboot_server(cls, server):
        raise NotImplementedError()


class RenameMixin(object):
    """
    Mixin for adapters to signify that servers can be renamed.
    """
    @classmethod
    def rename_server(cls, server):
        raise NotImplementedError()
