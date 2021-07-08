from rabbit import rabbit_client
import json
import os
 
def get_rabbit_address() -> str:
    configuration = None
    try:
        # file is putted inside the same folder of the script
        with open('configuration','r') as reader:
            # the content is organized as a json file
            configuration = json.load(reader)
            return configuration['address']
            
    except ValueError:
        return ''
    except FileNotFoundError:
        return ''
    
address = get_rabbit_address()
client = rabbit_client(address,'uninstaller',{})

response = client.send_controller_sync({
        'command': 'uninstall',
        'address': address
}) 

response = {'command': 'ok'}
if response['command'] == 'ok':
    os.system('systemctl disable docker-health-controller.service')
    os.system('systemctl stop docker-health-controller.service')
    os.system('rm -r /root/health_service')
    os.system('rm /etc/systemd/system/docker-health-controller')
    os.system('rm /var/log/rabbit_*')
    os.system('rm /var/log/health_monitor_*')
    os.system('systemctl daemon-reload')
    print('__UNINSTALL RESPONSE OK__')
else:
    print('__UNINSTALL RESPONSE ERROR__')