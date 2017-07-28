class AdapterBase(type):
    """
    Metaclass for Adapter classes registering defined adapters.
    """
    registry = {}

    def __new__(mcs, name, bases, attrs):
        cls = super(AdapterBase, mcs).__new__(mcs, name, bases, attrs)
        mcs.register(cls)
        return cls

    @classmethod
    def register(mcs, cls):
        adapter_id = cls.id

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
    id = None  # type: str
    name = None  # type: str
