from flask import request
from nanobox_libcloud import app
from nanobox_libcloud.adapters import get_adapter
from nanobox_libcloud.utils import output


# Server endpoints for the Nanobox Provider Adapter API
@app.route('/<adapter_id>/servers', methods=['POST'])
def server_create(adapter_id):
    """Creates a server using a certain adapter."""
    adapter = get_adapter(adapter_id)

    if not adapter:
        return output.failure("That adapter doesn't (yet) exist. Please check the adapter name and try again.", 501)

    if not adapter.do_verify(request.headers):
        return output.failure("Credential verification failed. Please check your credentials and try again.", 401)

    result = adapter.do_server_create(request.headers, request.json)

    if 'error' in result:
        return output.failure(result['error'], result['status'])

    return output.success(result['data'], result['status'])


@app.route('/<adapter_id>/servers/<server_id>', methods=['GET'])
def server_query(adapter_id, server_id):
    """Queries data about a server using a certain adapter."""
    adapter = get_adapter(adapter_id)

    if not adapter:
        return output.failure("That adapter doesn't (yet) exist. Please check the adapter name and try again.", 501)

    if not adapter.do_verify(request.headers):
        return output.failure("Credential verification failed. Please check your credentials and try again.", 401)

    result = adapter.do_server_query(request.headers, server_id)

    if 'error' in result:
        return output.failure(result['error'], result['status'])

    return output.success(result['data'], result['status'])


@app.route('/<adapter_id>/servers/<server_id>', methods=['DELETE'])
def server_cancel(adapter_id, server_id):
    """Cancels a server using a certain adapter."""
    adapter = get_adapter(adapter_id)

    if not adapter:
        return output.failure("That adapter doesn't (yet) exist. Please check the adapter name and try again.", 501)

    if not adapter.do_verify(request.headers):
        return output.failure("Credential verification failed. Please check your credentials and try again.", 401)

    result = adapter.do_server_cancel(request.headers, server_id)

    if isinstance(result, dict) and 'error' in result:
        return output.failure(result['error'], result['status'])

    return ""


@app.route('/<adapter_id>/servers/<server_id>/reboot', methods=['PATCH'])
def server_reboot(adapter_id, server_id):
    """Reboots a server using a certain adapter, if that adapter supports rebooting."""
    adapter = get_adapter(adapter_id)

    if not adapter:
        return output.failure("That adapter doesn't (yet) exist. Please check the adapter name and try again.", 501)

    if not adapter.can_reboot():
        return output.failure("This adapter doesn't support rebooting servers.", 501)

    if not adapter.do_verify(request.headers):
        return output.failure("Credential verification failed. Please check your credentials and try again.", 401)

    result = adapter.do_server_reboot(request.headers, server_id)

    if isinstance(result, dict) and 'error' in result:
        return output.failure(result['error'], result['status'])

    return ""


@app.route('/<adapter_id>/servers/<server_id>/rename', methods=['PATCH'])
def server_rename(adapter_id, server_id):
    """Renames a server using a certain adapter, if that adapter supports renaming."""
    adapter = get_adapter(adapter_id)

    if not adapter:
        return output.failure("That adapter doesn't (yet) exist. Please check the adapter name and try again.", 501)

    if not adapter.can_rename():
        return output.failure("This adapter doesn't support renaming servers.", 501)

    if not adapter.do_verify(request.headers):
        return output.failure("Credential verification failed. Please check your credentials and try again.", 401)

    result = adapter.do_server_rename(request.headers, server_id, request.json)

    if isinstance(result, dict) and 'error' in result:
        return output.failure(result['error'], result['status'])

    return ""
