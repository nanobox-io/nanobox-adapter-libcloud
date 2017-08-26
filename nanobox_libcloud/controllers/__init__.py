import importlib
import os

def import_controllers():
    """Finds and imports modules containing controller implementations."""
    for file in os.listdir(os.path.dirname(__file__)):
        if not file.startswith('_') and file.endswith('.py'):
            importlib.import_module('{}.{}'.format(__name__, file[:-3]))


# Import all modules containing controllers so they will be registered
import_controllers()
