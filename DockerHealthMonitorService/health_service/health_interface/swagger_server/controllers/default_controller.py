import connexion
import six
import json
import logging
import sys
import coloredlogs

from swagger_server.models.all_containers_response import AllContainersResponse  # noqa: E501
from swagger_server.models.all_containers_response_description import AllContainersResponseDescription  # noqa: E501
from swagger_server.models.bad_response import BadResponse  # noqa: E501
from swagger_server.models.correct_multi_response import CorrectMultiResponse  # noqa: E501
from swagger_server.models.container_response import ContainerResponse  # noqa: E501
from swagger_server.models.containers_address_body import ContainersAddressBody  # noqa: E501
from swagger_server.models.containers_address_body1 import ContainersAddressBody1  # noqa: E501
from swagger_server.models.containers_body import ContainersBody  # noqa: E501
from swagger_server.models.correct_response import CorrectResponse  # noqa: E501
from swagger_server.models.test_address_body import TestAddressBody  # noqa: E501
from swagger_server.models.test_body import TestBody  # noqa: E501
from swagger_server import util
from swagger_server.rabbit import rabbit_client

configuration = None
logger = None

""" configure the logger behaviour """            
def initialize_logger():
    global logger
    logger = logging.getLogger(__name__)
        
    # prevent to allocate more handlers into a previous used logger
    if not logger.hasHandlers():
        handler = logging.StreamHandler(sys.stdout)
        file_handler = logging.FileHandler('/var/log/health_monitor_interface.log')
        formatter = coloredlogs.ColoredFormatter("%(asctime)s %(name)s"
                                                 " %(levelname)s %(message)s",
                                                 "%Y-%m-%d %H:%M:%S")
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.addHandler(file_handler)
        logger.setLevel(logging.DEBUG)   # logger threshold  

            
def load_conf() -> str:
    global configuration
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
    
initialize_logger()
client = rabbit_client(load_conf(),'interface',{})  
 
def add_container(address, container_id):  # noqa: E501
    """Add a container to the service

    Add a previously ignored container to the service. By default all the containers are added to the service # noqa: E501

    :param address: 
    :type address: str
    :param container_id: 
    :type container_id: str

    :rtype: CorrectResponse
    """
    global configuration
    try:
        result = client.send_controller_sync({
            'command':'add_container',
            'address': address,
            'containerID': container_id}, configuration['address'])
        if result['command'] == 'ok':
            return CorrectResponse(result['command'],result['description'])
        else:
            return BadResponse(result['command'],result['type'],result['description'])
    except:
        return BadResponse('error','INTERNAL_ERROR','Internal error during the management of the request')



def add_docker_manager(body, address):  # noqa: E501
    """Add a new docker host into the service

    Install a new manager into the the selected machine. The operations requires the root password of the destination machine and that a ssh connection is present on the default port 23 # noqa: E501

    :param body: The operation requires the password of the root user of the destination machine
    :type body: dict | bytes
    :param address: 
    :type address: str

    :rtype: CorrectResponse
    """
    global configuration
    if connexion.request.is_json:
        body = ContainersAddressBody.from_dict(connexion.request.get_json())  # noqa: E501
        try:
            result = client.send_controller_sync({
                    'command':'add_host',
                    'password': body._password,
                    'address': address}, configuration['address'])
            if result['command'] == 'ok':
                return CorrectResponse(result['command'],result['description'])
            else:
                return BadResponse(result['command'],result['type'],result['description'])
        except KeyError:
            return BadResponse('error','INTERNAL_ERROR','Internal error during the management of the request')


def change_all_antagonists_conf(body):  # noqa: E501
    """Change all the antagonists configuration

    Change the configuration of all the antagonist. The configuration consists of five different parameters: - heavy: defines the probability that the attacker will choose to attack a container - balance: defines the probability that the attackers will perform a packet loss attack or a shutdown attack - loss: defines the mean packet loss value introduced during an attack(the value will be the mean of normal distribution) - duration: defines the duration of a packet loss attack to a container. The value will be the lambda of an exponential distribution - frequency: defines the interleaving time of each attacker between the possibility to perform an attack   # noqa: E501

    :param body: The request body can contain this fields: 
- heavy: defines the probability that the attacker will choose to attack a container. It&#x27;s a value between 0 and 100
- balance: defines the probability that the attackers will perform a packet loss attack or a shutdown attack. It&#x27;s a value between 0 and 100, the more the value tends to 100 the more the probability is to perform a shutdown attack
- loss: defines the mean packet loss value introduced during an attack(the value will be the mean of normal distribution). It&#x27;s a value between 0 and 100
- duration: defines the duration of a packet loss attack to a container. The value will be the lambda of an exponential distribution. The value is expressed in seconds
- frequency: defines the interleaving time of each attacker between the possibility to perform an attack . The value is expressed in seconds

If a field is missing simply it will not be changed, but no errors will be raised
    :type body: dict | bytes

    :rtype: CorrectResponse
    """
    global configuration
    if connexion.request.is_json:
        body = TestBody.from_dict(connexion.request.get_json())  # noqa: E501

        request = {
            'command' : 'change_antagonists_conf'}
    
        try:
            request['heavy'] = body._heavy
        except:
            pass
        try:
            request['balance'] = body._balance
        except:
            pass
        try:
            request['duration'] = body._duration
        except:
            pass
        try:
            request['frequency'] = body._frequency
        except:
            pass
        try:
            request['loss'] = body._loss
        except:
            pass
    
        try:
            result = client.send_controller_sync(request, configuration['address'])
            if result['command'] == 'ok':
                return CorrectMultiResponse('ok',result['description'])
            else:
                return BadResponse(result['command'],result['type'],result['description'])
        except:
            return BadResponse('error','INTERNAL_ERROR','Internal error during the management of the request')


def change_all_thresholds(body):  # noqa: E501
    """Change the threshold configured into each manager. 

    Change the threshold configured into the docker managers. Each manager have a personal threshold used to identify if the packet loss percentage is too high and the container needs to be restarted. # noqa: E501

    :param body: The request requires the threshold value to be set into the managers. The value is a percentage so it needs to be between 0 and 100 to be accepted.
    :type body: dict | bytes

    :rtype: CorrectResponse
    """
    global configuration
    global logger
    if connexion.request.is_json:
        body = ContainersBody.from_dict(connexion.request.get_json())  # noqa: E501
        try:
            
            result = client.send_controller_sync({
                    'command':'change_all_threshold',
                    'address': configuration['address'],
                    'threshold': body._threshold}, configuration['address'])
            if result['command'] == 'ok':
                logger.debug("RESPONSE: " + json.dumps(result))
                return CorrectMultiResponse('ok',result['description'])
            else:
                return BadResponse(result['command'],result['type'],result['description'])
        except ValueError:
            print("Error during the request manegement!")
            return BadResponse('error','INTERNAL_ERROR','Internal error during the management of the request')


def change_antagonist_conf(body, address):  # noqa: E501
    """Change an antagonist configuration

    Change the configuration of the selected antagonist. The configuration consists of five different parameters: - heavy: defines the probability that the attacker will choose to attack a container - balance: defines the probability that the attackers will perform a packet loss attack or a shutdown attack - loss: defines the mean packet loss value introduced during an attack(the value will be the mean of normal distribution) - duration: defines the duration of a packet loss attack to a container. The value will be the lambda of an exponential distribution - frequency: defines the interleaving time of each attacker between the possibility to perform an attack   # noqa: E501

    :param body: The request body can contain this fields: 
- heavy: defines the probability that the attacker will choose to attack a container. It&#x27;s a value between 0 and 100
- balance: defines the probability that the attackers will perform a packet loss attack or a shutdown attack. It&#x27;s a value between 0 and 100, the more the value tends to 100 the more the probability is to perform a shutdown attack
- loss: defines the mean packet loss value introduced during an attack(the value will be the mean of normal distribution). It&#x27;s a value between 0 and 100
- duration: defines the duration of a packet loss attack to a container. The value will be the lambda of an exponential distribution. The value is expressed in seconds
- frequency: defines the interleaving time of each attacker between the possibility to perform an attack . The value is expressed in seconds

If a field is missing simply it will not be changed, but no errors will be raised
    :type body: dict | bytes
    :param address: 
    :type address: str

    :rtype: CorrectResponse
    """
    global configuration
    if connexion.request.is_json:
        body = TestAddressBody.from_dict(connexion.request.get_json())  # noqa: E501
        request = {
            'command' : 'change_host_antagonist_conf',
            'address' : address}
    
        try:
            request['heavy'] = body._heavy
        except:
            pass
        try:
            request['balance'] = body._balance
        except:
            pass
        try:
            request['duration'] = body._duration
        except:
            pass
        try:
            request['frequency'] = body._frequency
        except:
            pass
        try:
            request['loss'] = body._loss
        except:
            pass
    
        try:
            result = client.send_controller_sync(request, configuration['address'])
            if result['command'] == 'ok':
                return CorrectResponse(result['command'],result['description'])
            else:
                return BadResponse(result['command'],result['type'],result['description'])
        except:
            return BadResponse('error','INTERNAL_ERROR','Internal error during the management of the request')


def change_manager_threshold(body, address):  # noqa: E501
    """Change the threshold configured into the selected manager. 

    Change the threshold configured into the selected docker manager. Each manager have a personal threshold used to identify if the packet loss percentage is too high and the container needs to be restarted. # noqa: E501

    :param body: The operation requires a threshold parameters to be set into the machine. The threshold must be between 0 and 100
    :type body: dict | bytes
    :param address: 
    :type address: str

    :rtype: CorrectResponse
    """
    global configuration
    if connexion.request.is_json:
        body = ContainersAddressBody1.from_dict(connexion.request.get_json())  # noqa: E501
        try:
            result = client.send_controller_sync({
                    'command':'change_threshold',
                    'address': address,
                    'threshold': body._threshold}, configuration['address'])
            if result['command'] == 'ok':
                return CorrectResponse(result['command'],result['description'])
            else:
                return BadResponse(result['command'],result['type'],result['description'])
        except:
            return BadResponse('error','INTERNAL_ERROR','Internal error during the management of the request')


def get_all_containers():  # noqa: E501
    """Gives all the managed containers by the service

    It doesn&#x27;t require any parameter and gives back a set of lists each one describing the containers inside a particular managed docker host. The response will contain for each docker host its status and a list of all the containers with information about their status and the current packet loss measured # noqa: E501


    :rtype: CorrectResponse
    """
    global configuration
    try:
        result = client.send_controller_sync({
            'command':'get_all_containers',
            'address': configuration['address']}, configuration['address'])
        if result['command'] == 'ok':
            content = list()
            for host in result['description']:
                content.append(AllContainersResponseDescription(host['address'], host['content']))
            return AllContainersResponse(result['command'],content)
        else:
            return BadResponse(result['command'],result['type'],result['description'])
    except:
        return BadResponse('error','INTERNAL_ERROR','Internal error during the management of the request')


def get_container_info(address, container_id):  # noqa: E501
    """Gives information about the selected container

    The request returns the status and the packet loss of the selected container # noqa: E501

    :param address: 
    :type address: str
    :param container_id: 
    :type container_id: str

    :rtype: CorrectResponse
    """
    global configuration
    try:
        result = client.send_controller_sync({
            'command':'get_container',
            'address': address,
            'containerID': container_id}, configuration['address'])
        if result['command'] == 'ok':
            return ContainerResponse('ok', AllContainersResponseDescription(address, result['description']))
        else:
            return BadResponse(result['command'],result['type'],result['description'])
    except:
        return BadResponse('error','INTERNAL_ERROR','Internal error during the management of the request')


def get_manager_containers(address):  # noqa: E501
    """Get the status of the selected docker host and a list of all the managed containers with their status and the current packet loss percentage measured

    It doesn&#x27;t require any parameter and gives back a set of lists each one describing the containers inside a particular managed docker host. The response will contain for each docker host its status and a list of all the containers with information about their status and the current packet loss measured # noqa: E501

    :param address: 
    :type address: str

    :rtype: CorrectResponse
    """
    global configuration
    try:
        result = client.send_controller_sync({
            'command':'get_host_containers',
            'address': address}, configuration['address'])
        if result['command'] == 'ok':
            return ContainerResponse('ok', AllContainersResponseDescription(address, result['description']))
        else:
            return BadResponse(result['command'],result['type'],result['description'])
    except:
        return BadResponse('error','INTERNAL_ERROR','Internal error during the management of the request')


def ignore_container(address, container_id):  # noqa: E501
    """Remove a container from the service

    Ignore a container from the service management. By default all the containers are added to the service # noqa: E501

    :param address: 
    :type address: str
    :param container_id: 
    :type container_id: str

    :rtype: CorrectResponse
    """
    global configuration
    try:
        result = client.send_controller_sync({
            'command':'remove_container',
            'address': address,
            'containerID': container_id}, configuration['address'])
        if result['command'] == 'ok':
            return CorrectResponse(result['command'],result['description'])
        else:
            return BadResponse(result['command'],result['type'],result['description'])
    except:
        return BadResponse('error','INTERNAL_ERROR','Internal error during the management of the request')


def remove_docker_manager(address):  # noqa: E501
    """Remove a registered docker host into the service

    Uninstall the selected manager from the machine. The system has already stored the password but its required in order to secure the operation and prevent that users will disable the managers # noqa: E501

    :param address: 
    :type address: str

    :rtype: CorrectResponse
    """
    global configuration
    try:
        result = client.send_controller_sync({
            'command':'remove_host',
            'address': address}, configuration['address'])
        if result['command'] == 'ok':
            return CorrectResponse(result['command'],result['description'])
        else:
            return BadResponse(result['command'],result['type'],result['description'])
    except:
        return BadResponse('error','INTERNAL_ERROR','Internal error during the management of the request')


def start_all_antagonists():  # noqa: E501
    """Starts all the antagonists

    Into each docker manager is linked an antagonist able to attack all the container into the local docker host. Starting the antagonist will perform an attack on all the containers with the last configuration provided. If no configuration has been provided than a default configuration will be used. # noqa: E501


    :rtype: CorrectResponse
    """
    global configuration
    try:
        result = client.send_controller_sync({
            'command':'add_antagonists',
            'address': configuration['address']}, configuration['address'])
        if result['command'] == 'ok':
            return CorrectMultiResponse('ok',result['description'])
        else:
            return BadResponse(result['command'],result['type'],result['description'])
    except:
        return BadResponse('error','INTERNAL_ERROR','Internal error during the management of the request')


def start_antagonist(address):  # noqa: E501
    """Start an antagonist

    Into each docker manager is linked an antagonist able to attack all the container into the local docker host. Starting the antagonist will perform an attack on all the containers with the last configuration provided. If no configuration has been provided than a default configuration will be used. # noqa: E501

    :param address: 
    :type address: str

    :rtype: CorrectResponse
    """   
    global configuration
    try:
        result = client.send_controller_sync({
            'command':'add_host_antagonist',
            'address': address}, configuration['address'])
        if result['command'] == 'ok':
            return CorrectResponse(result['command'],result['description'])
        else:
            return BadResponse(result['command'],result['type'],result['description'])
    except:
        return BadResponse('error','INTERNAL_ERROR','Internal error during the management of the request')


def stop_all_antagonist():  # noqa: E501
    """Stop all the antagonists

    The function will stop all the attackers into all the docker host. A started attack needs to be stop otherwise it will continue forever. # noqa: E501


    :rtype: CorrectResponse
    """
    global configuration
    try:
        result = client.send_controller_sync({
            'command':'remove_antagonists',
            'address': configuration['address']}, configuration['address'])
        if result['command'] == 'ok':
            return CorrectMultiResponse('ok',result['description'])
        else:
            return BadResponse(result['command'],result['type'],result['description'])
    except:
        return BadResponse('error','INTERNAL_ERROR','Internal error during the management of the request')


def stop_antagonist(address):  # noqa: E501
    """Stop an antagonist

    The function will stop the selected antagonist to attack the local docker host. A started attack needs to be stop otherwise it will continue forever. # noqa: E501

    :param address: 
    :type address: str

    :rtype: CorrectResponse
    """
    global configuration
    try:
        result = client.send_controller_sync({
            'command':'remove_host_antagonist',
            'address': address}, configuration['address'])
        if result['command'] == 'ok':
            return CorrectResponse(result['command'],result['description'])
        else:
            return BadResponse(result['command'],result['type'],result['description'])
    except:
        return BadResponse('error','INTERNAL_ERROR','Internal error during the management of the request')
