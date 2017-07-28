import typing


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
    default_region = None  # type: str,
    default_size = None  # type: str,
    default_plan = None  # type: str,
    can_reboot = None  # type: bool,
    can_rename = None  # type: bool,
    internal_iface = None  # type: str
    external_iface = None  # type: str
    ssh_user = None  # type: str
    ssh_auth_method = None  # type: str
    ssh_key_method = None  # type: str
    bootstrap_script = None  # type: str
    credential_fields = None  # type: typing.Tuple[str, str]
    instructions = None  # type: str

    def to_nanobox(self) -> dict:
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
            'credential_fields': [{'key': field[0], 'label': field[1]} for field in self.credential_fields],
            'instructions': self.instructions,
        }


class ServerSpec(Model):
    """
    Data model representing a server specification that can be ordered.
    """
    id = None  # type: str
    ram = None  # type: int
    cpu = None  # type: int
    disk = None  # type: int
    transfer = None  # type: int
    dollars_per_hr = None  # type: float
    dollars_per_mo = None  # type: float

    def to_nanobox(self) -> dict:
        return {
            'id': self.id,
            'ram': self.ram,
            'cpu': self.cpu,
            'disk': self.disk,
            'transfer': self.transfer,
            'dollars_per_hr': self.dollars_per_hr,
            'dollars_per_mo': self.dollars_per_mo,
        }


class ServerPlan(Model):
    """
    Data model representing a server plan.
    """
    id = None  # type: str
    name = None  # type: str
    specs = []  # type: typing.List[ServerSpec]

    def to_nanobox(self) -> dict:
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

    def to_nanobox(self) -> dict:
        return {
            'id': self.id,
            'name': self.name,
            'plans': [plan.to_nanobox() for plan in self.plans],
        }
