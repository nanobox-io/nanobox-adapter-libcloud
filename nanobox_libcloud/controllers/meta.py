from nanobox_libcloud import app
from nanobox_libcloud.adapters import get_adapter


@app.route('/<adapter_id>/meta')
def meta(adapter_id):
    """Provides the metadata for a certain adapter."""
    adapter = get_adapter(adapter_id)
