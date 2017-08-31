from flask import request
from nanobox_libcloud import app
from nanobox_libcloud.adapters import get_adapter
from nanobox_libcloud.utils import output


# Server endpoints for the Nanobox Provider Adapter API
@app.route('/<adapter_id>/servers', methods=['POST'])
def server_create(adapter_id):
    """Creates a server using a certain adapter."""
    adapter = get_adapter(adapter_id)
    if adapter:
        if adapter.do_verify(request.headers):
            result = adapter.do_server_create(request.headers, request.json)
            if result.error:
                return output.failure(result.error, result.status)
            return output.success(result.data, result.status)
        return output.failure("Credential verification failed. Please check your credentials and try again.", 401)
    return output.failure("That adapter doesn't (yet) exist. Please check the adapter name and try again.", 501)

@app.route('/<adapter_id>/servers/<server_id>', methods=['GET'])
def server_query(adapter_id):
    """Queries data about a server using a certain adapter."""
    adapter = get_adapter(adapter_id)
    if adapter:
        if adapter.do_verify(request.headers):
            result = adapter.do_server_query(request.headers, request.json)
            if result.error:
                return output.failure(result.error, result.status)
            return output.success(result.data, result.status)
        return output.failure("Credential verification failed. Please check your credentials and try again.", 401)
    return output.failure("That adapter doesn't (yet) exist. Please check the adapter name and try again.", 501)

@app.route('/<adapter_id>/servers/<server_id>', methods=['GET'])
def server_cancel(adapter_id):
    """Cancels a server using a certain adapter."""
    adapter = get_adapter(adapter_id)
    if adapter:
        if adapter.do_verify(request.headers):
            result = adapter.do_server_cancel(request.headers, request.json)
            if result.error:
                return output.failure(result.error, result.status)
            return output.success(result.data, result.status)
        return output.failure("Credential verification failed. Please check your credentials and try again.", 401)
    return output.failure("That adapter doesn't (yet) exist. Please check the adapter name and try again.", 501)

@app.route('/<adapter_id>/servers/<server_id>/reboot', methods=['PATCH'])
def server_reboot(adapter_id):
    """Reboots a server using a certain adapter, if that adapter supports rebooting."""
    adapter = get_adapter(adapter_id)
    if adapter:
        if adapter.can_reboot():
            if adapter.do_verify(request.headers):
                result = adapter.do_server_reboot(request.headers, request.json)
                if result.error:
                    return output.failure(result.error, result.status)
                return output.success(result.data, result.status)
            return output.failure("Credential verification failed. Please check your credentials and try again.", 401)
        return output.failure("This adapter doesn't support rebooting servers.", 501)
    return output.failure("That adapter doesn't (yet) exist. Please check the adapter name and try again.", 501)

@app.route('/<adapter_id>/servers/<server_id>/rename', methods=['PATCH'])
def server_rename(adapter_id):
    """Renames a server using a certain adapter, if that adapter supports renaming."""
    adapter = get_adapter(adapter_id)
    if adapter:
        if adapter.can_rename():
            if adapter.do_verify(request.headers):
                result = adapter.do_server_rename(request.headers, request.json)
                if result.error:
                    return output.failure(result.error, result.status)
                return output.success(result.data, result.status)
            return output.failure("Credential verification failed. Please check your credentials and try again.", 401)
        return output.failure("This adapter doesn't support renaming servers.", 501)
    return output.failure("That adapter doesn't (yet) exist. Please check the adapter name and try again.", 501)
