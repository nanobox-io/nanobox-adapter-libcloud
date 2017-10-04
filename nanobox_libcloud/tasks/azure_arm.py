from nanobox_libcloud import celery
from nanobox_libcloud import adapters
from time import sleep
import logging


@celery.task
def azure_destroy_arm(creds, name):
    logger = logging.getLogger(__name__)
    self = adapters.azure_arm.AzureARM()
    driver = self._get_user_driver(**creds)

    logger.info('Destroying server, NIC, public IP, and VHD...')
    if driver.destroy_node(self._find_server(driver, name), ex_destroy_ip=True):
        logger.info('Ensuring server was destroyed...')
        while self._find_server(driver, name) is not None:
            sleep(0.5)

        app = name.rsplit('-', 1)[0]

        if len(driver.list_nodes(app)) < 1:
            logger.info('Destroying virtual network...')
            net = self._find_network(driver, app)
            while True:
                try:
                    driver.ex_delete_network(net.id)
                except BaseHTTPError as h:
                    if h.code == 202:
                        break
                    logging.info('%d: %s' % (h.code, h.message))
                    inuse = "is in use" in h.message
                    if h.code == 400 and inuse:
                        time.sleep(10)
                break
            while self._find_network(driver, app):
                sleep(0.5)

            logger.info('Destroying resource group...')
            group = self._find_resource_group(driver, app)
            while True:
                try:
                    driver.ex_delete_resource_group(group.id)
                except BaseHTTPError as h:
                    if h.code == 202:
                        break
                    logging.info('%d: %s' % (h.code, h.message))
                    inuse = "InUse" in h.message
                    if h.code == 400 and inuse:
                        time.sleep(10)
                break
            while self._find_resource_group(driver, app):
                sleep(0.5)
