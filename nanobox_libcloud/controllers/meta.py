from flask import render_template, request
from nanobox_libcloud import app
from nanobox_libcloud.adapters import get_adapter
from nanobox_libcloud.adapters.base import AdapterBase
from nanobox_libcloud.utils import output


# Overview and usage endpoints, to explain how this meta-adapter works
@app.route('/', methods=['GET'])
def overview():
    """Provides an overview of the libcloud meta-adapter, and how to use it, in the most general sense."""
    adapters = sorted(AdapterBase.registry.keys())

    return render_template("overview.html", adapters=adapters)


@app.route('/docs', methods=['GET'])
def docs():
    """Loads Swagger UI with all the supported adapters' OpenAPI Spec Files pre-loaded into the Topbar for exploration."""
    adapters = sorted(AdapterBase.registry.keys())

    return render_template("docs.html", adapters=adapters)


@app.route('/<adapter_id>', methods=['GET'])
def usage(adapter_id):
    """Provides usage info for a certain adapter, and how to use it, in a more specific sense."""
    adapter = get_adapter(adapter_id)

    if not adapter:
        return output.failure("That adapter doesn't (yet) exist. Please check the adapter name and try again.", 501)

    return render_template("usage.html", adapter=adapter)


@app.route('/<adapter_id>/docs', methods=['GET'])
def adapter_docs(adapter_id):
    """Loads Swagger UI with a certain adapter's OpenAPI Spec File pre-loaded."""
    return render_template("docs.html", adapters=[adapter_id])


# Actual metadata endpoints for the Nanobox Provider Adapter API
@app.route('/<adapter_id>/meta', methods=['GET'])
def meta(adapter_id):
    """Provides the metadata for a certain adapter."""
    adapter = get_adapter(adapter_id)

    if not adapter:
        return output.failure("That adapter doesn't (yet) exist. Please check the adapter name and try again.", 501)

    return output.success(adapter.do_meta())


@app.route('/<adapter_id>/catalog', methods=['GET'])
def catalog(adapter_id):
    """Provides the catalog data for a certain adapter."""
    adapter = get_adapter(adapter_id)

    if not adapter:
        return output.failure("That adapter doesn't (yet) exist. Please check the adapter name and try again.", 501)

    result = adapter.do_catalog(request.headers)
    if not isinstance(result, list):
        return output.failure('%d: %s' % (result.code, result.message) if hasattr(result, 'code') and hasattr(result, 'message') else repr(result), result.code if hasattr(result, 'code') else 500)

    return output.success(result)


@app.route('/<adapter_id>/verify', methods=['POST'])
def verify(adapter_id):
    """Verifies user credentials for a certain adapter."""
    adapter = get_adapter(adapter_id)

    if not adapter:
        return output.failure("That adapter doesn't (yet) exist. Please check the adapter name and try again.", 501)

    result = adapter.do_verify(request.headers)
    if result is not True:
        return output.failure("Credential verification failed. Please check your credentials and try again. (Error %s)" % (result), 401)

    return ""
