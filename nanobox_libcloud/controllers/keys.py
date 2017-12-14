from flask import request
from nanobox_libcloud import app
from nanobox_libcloud.adapters import get_adapter
from nanobox_libcloud.utils import output


# SSH Key endpoints for the Nanobox Provider Adapter API
@app.route('/<adapter_id>/keys', methods=['POST'])
def key_create(adapter_id):
    """Creates a key using a certain adapter."""
    adapter = get_adapter(adapter_id)

    if not adapter:
        return output.failure("That adapter doesn't (yet) exist. Please check the adapter name and try again.", 501)

    result = adapter.do_verify(request.headers)
    if result is not True:
        return output.failure("Credential verification failed. Please check your credentials and try again. (Error %s)" % (result), 401)

    result = adapter.do_key_create(request.headers, request.json)

    if 'error' in result:
        return output.failure(result['error'], result['status'])

    return output.success(result['data'], result['status'])


@app.route('/<adapter_id>/keys/<key_id>', methods=['GET'])
def key_query(adapter_id, key_id):
    """Queries data about a key using a certain adapter."""
    adapter = get_adapter(adapter_id)

    if not adapter:
        return output.failure("That adapter doesn't (yet) exist. Please check the adapter name and try again.", 501)

    result = adapter.do_verify(request.headers)
    if result is not True:
        return output.failure("Credential verification failed. Please check your credentials and try again. (Error %s)" % (result), 401)

    result = adapter.do_key_query(request.headers, key_id)

    if 'error' in result:
        return output.failure(result['error'], result['status'])

    return output.success(result['data'], result['status'])


@app.route('/<adapter_id>/keys/<key_id>', methods=['DELETE'])
def key_delete(adapter_id, key_id):
    """Deletes a key using a certain adapter."""
    adapter = get_adapter(adapter_id)

    if not adapter:
        return output.failure("That adapter doesn't (yet) exist. Please check the adapter name and try again.", 501)

    result = adapter.do_verify(request.headers)
    if result is not True:
        return output.failure("Credential verification failed. Please check your credentials and try again. (Error %s)" % (result), 401)

    result = adapter.do_key_delete(request.headers, key_id)

    if isinstance(result, dict) and 'error' in result:
        return output.failure(result['error'], result['status'])

    return ""
