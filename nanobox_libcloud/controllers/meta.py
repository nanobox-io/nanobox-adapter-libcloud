from flask import render_template, request
from nanobox_libcloud import app
from nanobox_libcloud.adapters import get_adapter
from nanobox_libcloud.adapters.base import AdapterBase
from nanobox_libcloud.utils import output


# Overview and usage endpoints, to explain how this meta-adapter works
@app.route('/', methods=['GET'])
def overview():
    """Provides an overview of the libcloud meta-adapter, and how to use it, in the most general sense."""
    adapters = AdapterBase.registry.keys()
    return render_template("overview.html", adapters=adapters)

@app.route('/<adapter_id>', methods=['GET'])
def usage(adapter_id):
    """Provides usage info for a certain adapter, and how to use it, in a more specific sense."""
    adapter = get_adapter(adapter_id)
    if adapter:
        return render_template("usage.html", adapter=adapter)
    return output.failure("That adapter doesn't (yet) exist. Please check the adapter name and try again.", 501)

# Actual metadata endpoints for the Nanobox Provider Adapter API
@app.route('/<adapter_id>/meta', methods=['GET'])
def meta(adapter_id):
    """Provides the metadata for a certain adapter."""
    adapter = get_adapter(adapter_id)
    if adapter:
        return output.success(adapter.do_meta())
    return output.failure("That adapter doesn't (yet) exist. Please check the adapter name and try again.", 501)

@app.route('/<adapter_id>/catalog', methods=['GET'])
def catalog(adapter_id):
    """Provides the catalog data for a certain adapter."""
    adapter = get_adapter(adapter_id)
    if adapter:
        return output.success(adapter.do_catalog())
    return output.failure("That adapter doesn't (yet) exist. Please check the adapter name and try again.", 501)

@app.route('/<adapter_id>/verify', methods=['POST'])
def verify(adapter_id):
    """Verifies user credentials for a certain adapter."""
    adapter = get_adapter(adapter_id)
    if adapter:
        if adapter.do_verify(request.headers):
            return ""
        return output.failure("Credential verification failed. Please check your credentials and try again.", 401)
    return output.failure("That adapter doesn't (yet) exist. Please check the adapter name and try again.", 501)
