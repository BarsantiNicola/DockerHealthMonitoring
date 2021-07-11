from rabbit import rabbit_client
import json
import os
import logging
import coloredlogs
import sys
from time import sleep
def initialize_logger():
    logger = logging.getLogger("uninstaller")
    
    # prevent to allocate more handlers into a previous used logger
    if not logger.hasHandlers():
        logger.setLevel(logging.DEBUG)
        handler = logging.StreamHandler(sys.stdout)
        formatter = coloredlogs.ColoredFormatter("%(asctime)s %(name)s"
                                                 " %(levelname)s %(message)s",
                                                 "%Y-%m-%d %H:%M:%S")
        handler.setFormatter(formatter)

        handler.setLevel(logging.DEBUG)
            
        logger.addHandler(handler)
        logger.debug("Configuration completed")
        return logger
    
def get_rabbit_address() -> str:
    configuration = None
    try:
        # file is putted inside the same folder of the script
        with open('/root/health_service/health-controller/configuration','r') as reader:
            # the content is organized as a json file
            configuration = json.load(reader)
            return configuration['address']
            
    except ValueError:
        return ''
    except FileNotFoundError:
        return ''
    
address = get_rabbit_address()
client = rabbit_client(address,'interface',{})
logger = initialize_logger()
sleep(5)
logger.debug("Sending request to remove the manager from all the hosts") 
response = client.send_controller_sync({
        'command': 'uninstall',
        'address': address
}, address) 
logger.debug("Request sent response: " + response['command']) 

if response['command'] == 'ok':
    logging.debug("Removing the local controller and rest interface components")
    os.system('systemctl disable docker-health-controller.service')
    os.system('systemctl stop docker-health-controller.service')
    os.system('systemctl disable docker-health-interface.service')
    os.system('systemctl stop docker-health-interface.service')
    os.system('rm -r /root/health_service')
    os.system('rm /etc/systemd/system/docker-health-controller.service')
    os.system('rm /etc/systemd/system/docker-health-interface.service')
    os.system('rm /var/log/rabbit_*')
    os.system('rm /var/log/health_monitor_*')
    os.system('systemctl daemon-reload')
    logging.debug("Uninstall completed")
else:
    logging.debug("Uninstall stopped, managers not removed")

exit()