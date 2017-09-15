from nanobox_libcloud import celery
from nanobox_libcloud.adapters import azure
from time import sleep
import libcloud
from requests.exceptions import ReadTimeout


@celery.task
def azure_create(headers, data):
    self = azure.Azure()
    driver = self._get_user_driver(**self._get_request_credentials(headers))

    try:
        driver.create_node(**self._get_create_args(data))
    except libcloud.common.types.LibcloudError:
        sleep(2)
        azure_create.delay(headers, data)


@celery.task
def azure_destroy(creds, name):
    self = azure.Azure()
    driver = self._get_user_driver(**creds)

    while self._find_server(driver, name) is not None:
        sleep(0.5)

    driver.ex_destroy_cloud_service(name)

    while True:
        try:
            driver.ex_destroy_storage_service(name.replace('-', ''))
        except (libcloud.common.types.LibcloudError, ReadTimeout):
            pass
        except AttributeError:
            # Generally caused by "Too Many Requests" response not being parsed
            sleep(2)
        else:
            break
        finally:
            sleep(0.5)
