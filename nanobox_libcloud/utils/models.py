import typing

from libcloud.compute.types import NodeState


class Model(object):
    """
    Base class for the intermediate data models.
    """
    def __init__(self, **kwargs):
        # Set the keyword arguments on the fields, if present
        for key, value in kwargs.items():
            if not hasattr(self, key):
                raise AttributeError("The {} model has no field {}.".format(self.__class__.__name__, key))
            setattr(self, key, value)

    def to_nanobox(self) -> dict:
        """Returns the data in a representation which can be converted to JSON and is expected by the Nanobox client."""
        raise NotImplementedError()


class AdapterMeta(Model):
    """
    Data model representing the metadata of an adapter.
    """
    id = None  # type: str
    name = None  # type: str
    server_nick_name = None  # type: str
    default_region = None  # type: str
    default_size = None  # type: str
    default_plan = None  # type: str
    can_reboot = None  # type: bool
    can_rename = None  # type: bool
    internal_iface = None  # type: str
    external_iface = None  # type: str
    ssh_user = None  # type: str
    ssh_auth_method = None  # type: str
    ssh_key_method = None  # type: str
    bootstrap_script = None  # type: str
    bootstrap_timeout = None  # type: int
    auth_credential_fields = None  # type: typing.Tuple[str, str]
    auth_instructions = None  # type: str

    def to_nanobox(self) -> typing.Dict[str, typing.Any]:
        return {
            'id': self.id,
            'name': self.name,
            'server_nick_name': self.server_nick_name,
            'default_region': self.default_region,
            'default_size': self.default_size,
            'default_plan': self.default_plan,
            'can_reboot': self.can_reboot,
            'can_rename': self.can_rename,
            'internal_iface': self.internal_iface,
            'external_iface': self.external_iface,
            'ssh_user': self.ssh_user,
            'ssh_auth_method': self.ssh_auth_method,
            'ssh_key_method': self.ssh_key_method,
            'bootstrap_script': self.bootstrap_script,
            'bootstrap_timeout': self.bootstrap_timeout\
                                 if self.bootstrap_timeout is not None else 300,
            'credential_fields': [{'key': field[0], 'label': field[1]}
                                  for field in self.auth_credential_fields],
            'instructions': self.auth_instructions,
        }


class ServerSpec(Model):
    """
    Data model representing a server specification that can be ordered.
    """
    id = None  # type: str
    name = None  # type: str
    ram = None  # type: int
    cpu = None  # type: int
    disk = None  # type: int
    transfer = None  # type: int
    dollars_per_hr = None  # type: float
    dollars_per_mo = None  # type: float

    def to_nanobox(self) -> typing.Dict[str, typing.Any]:
        return {
            'id': self.id,
            'name': self.name,
            'ram': self.ram,
            'cpu': self.cpu,
            'disk': self.disk,
            'transfer': self.transfer or 'unlimited',
            'dollars_per_hr': '%0.3f' % (self.dollars_per_hr)\
                              if self.dollars_per_hr is not None else 'Unknown',
            'dollars_per_mo': '%0.2f' % (self.dollars_per_mo)\
                              if self.dollars_per_mo is not None else 'Unknown',
        }


class ServerPlan(Model):
    """
    Data model representing a server plan.
    """
    id = None  # type: str
    name = None  # type: str
    specs = []  # type: typing.List[ServerSpec]

    def to_nanobox(self) -> typing.Dict[str, typing.Any]:
        return {
            'id': self.id,
            'name': self.name,
            'specs': [spec.to_nanobox() for spec in self.specs],
        }


class ServerRegion(Model):
    """
    Data model representing a server region.
    """
    id = None  # type: str
    name = None  # type: str
    plans = []  # type: typing.List[ServerPlan]

    def to_nanobox(self) -> typing.Dict[str, typing.Any]:
        return {
            'id': self.id,
            'name': self.name,
            'plans': [plan.to_nanobox() for plan in self.plans],
        }


class KeyInfo(Model):
    """
    Data model representing an SSH key.
    """
    id = None  # type: str
    name = None  # type: str
    key = None  # type: str

    def to_nanobox(self) -> typing.Dict[str, typing.Any]:
        return {
            'id': self.id,
            'name': self.name,
            'public_key': self.key,
        }

        if self.key is not None:
            key['public_key'] = self.key
        else:
            key['fingerprint'] = self.fingerprint

class ServerInfo(Model):
    """
    Data model representing an actual server.
    """
    id = None  # type: str
    status = None  # type: NodeState
    name = None  # type: str
    external_ip = None  # type: str
    internal_ip = None  # type: str

    def to_nanobox(self) -> typing.Dict[str, typing.Any]:
        return {
            'id': self.id,
            'status': 'active' if self.status == NodeState.RUNNING else self.status,
            'name': self.name,
            'external_ip': self.external_ip,
            'internal_ip': self.internal_ip,
        }
