from nanobox_libcloud import celery
from nanobox_libcloud import adapters
from time import sleep
import logging
import libcloud
from libcloud.compute.base import Node
from libcloud.compute.types import NodeState
from requests.exceptions import ReadTimeout


@celery.task
def azure_create_classic(headers, data):
    logger = logging.getLogger(__name__)
    self = adapters.azure.AzureClassic()
    driver = self._get_user_driver(**self._get_request_credentials(headers))

    logger.info('Creating server and dependencies...')
    node = None
    while node is None:
        try:
            node = driver.create_node(**self._get_create_args(data))
        except (AttributeError, libcloud.common.types.LibcloudError):
            sleep(2)

    logger.info('Waiting for server to start...')
    while node is None or node.state != NodeState.RUNNING:
        try:
            node = self._find_server(driver, data['name'])
        except (AttributeError, libcloud.common.types.LibcloudError):
            sleep(2)

    logger.info('Adding Nanobox ports...')
    while True:
        try:
            driver.ex_set_instance_endpoints(node, [
                {"name": 'SSH', "protocol": 'TCP', "port": 22, "local_port": 22},
                {"name": 'HTTP', "protocol": 'TCP', "port": 80, "local_port": 80},
                {"name": 'HTTPS', "protocol": 'TCP', "port": 443, "local_port": 443},
                {"name": 'NanoAgent SSH', "protocol": 'TCP', "port": 1289, "local_port": 1289},
                {"name": 'Mist', "protocol": 'TCP', "port": 1446, "local_port": 1446},
                {"name": 'Slurp API', "protocol": 'TCP', "port": 1566, "local_port": 1566},
                {"name": 'Slurp SSH', "protocol": 'TCP', "port": 1567, "local_port": 1567},
                {"name": 'Pulse', "protocol": 'TCP', "port": 5531, "local_port": 5531},
                {"name": 'Logvac', "protocol": 'TCP', "port": 6361, "local_port": 6361},
                {"name": 'Hoarder', "protocol": 'TCP', "port": 7410, "local_port": 7410},
                {"name": 'Portal', "protocol": 'TCP', "port": 8443, "local_port": 8443},
                {"name": 'Red Daemon', "protocol": 'UDP', "port": 8472, "local_port": 8472},
                {"name": 'NanoAgent API', "protocol": 'TCP', "port": 8570, "local_port": 8570},
            ], 'production')
        except AttributeError:
            pass
        except libcloud.common.types.LibcloudError as e:
            logger.info(repr(e))
        else:
            break

    # for low in range(32768, 61000, 1024):
    #     logger.info('Adding ports %d through %d...' % (low, min(low + 1023, 61000)))
    #
    #     node = None
    #     while node is None or 'instance_endpoints' not in node.extra:
    #         try:
    #             node = self._find_server(driver, data['name'])
    #         except (AttributeError, libcloud.common.types.LibcloudError):
    #             sleep(2)
    #
    #     while True:
    #         try:
    #             driver.ex_add_instance_endpoints(node, [
    #                 {"name": 'Ephemeral TCP Port %d' % (port), "protocol": 'TCP', "port": port, "local_port": port}
    #                     for port in range(low, min(low + 1023, 61000) + 1)
    #             ] + [
    #                 {"name": 'Ephemeral UDP Port %d' % (port), "protocol": 'UDP', "port": port, "local_port": port}
    #                     for port in range(low, min(low + 1023, 61000) + 1)
    #             ], 'production')
    #         except AttributeError:
    #             pass
    #         except libcloud.common.types.LibcloudError as e:
    #             if 'currently performing an operation' not in repr(e):
    #                 logger.info(repr(e))
    #         else:
    #             break

@celery.task
def azure_destroy_classic(creds, name):
    logger = logging.getLogger(__name__)
    self = azure.AzureClassic()
    driver = self._get_user_driver(**creds)

    logger.info('Waiting for server to be destroyed...')
    while self._find_server(driver, name) is not None:
        sleep(0.5)

    logger.info('Removing cloud service...')
    driver.ex_destroy_cloud_service(name)

    if len([cloud for cloud in driver.ex_list_cloud_services()
            if cloud.service_name.startswith(name.rsplit('-', 1)[0])]) < 1:
        logger.info('Removing storage service...')
        while True:
            try:
                driver.ex_destroy_storage_service(name.rsplit('-', 1)[0].replace('-', ''))
            except (libcloud.common.types.LibcloudError, ReadTimeout) as e:
                if 'has some active image(s)' not in repr(e):
                    logger.info(repr(e))
            except AttributeError:
                # Generally caused by "Too Many Requests" response not being parsed
                sleep(2)
            else:
                break
            finally:
                sleep(0.5)
