import importlib
import os


def import_tasks():
    """Finds and imports modules containing task implementations."""
    for file in os.listdir(os.path.dirname(__file__)):
        if not file.startswith('_') and file.endswith('.py'):
            importlib.import_module('{}.{}'.format(__name__, file[:-3]))


# Import all modules containing tasks so they will be registered
import_tasks()
