import connexion
import six
import socket
import json

from swagger_server import util
from swagger_server.rabbit import rabbit_client

client = rabbit_client('172.16.3.167','interface',{})

def add_container(container_id, address):  # noqa: E501
    """Add a new Docker container

    It adds a new docker container from the available Docker containers to be managed by our Health monitoring system # noqa: E501

    :param container_id: the ID associated with the container the user want to add to the service
    :type container_id: str
    :param address: the address of the machine which maintains the container
    :type address: str

    :rtype: None
    """
    message = {
            'command' : 'add_container',
            'address' : address,
            'containerID' : container_id }
    return json.dumps(client.send_controller_sync(message, '172.16.3.167'))
    print("RESULT GETTED: ")


def add_host(address, password):  # noqa: E501
    """Add a new Docker host

    It adds a new docker host in which our service will be deployed # noqa: E501

    :param address: the address of the machine in which put a new manager
    :type address: str
    :param password: The password used from the root user of the destination machine
    :type password: str

    :rtype: None
    """
    message = {
            'command' : 'add_host',
            'address' : address,
            'password' : password }
    return json.dumps(client.send_controller_sync(message, '172.16.3.167'))

def change_all_threshold(threshold):  # noqa: E501
    """Update the threshold of all the docker managers

    It changes the thresholds used by all the docker managers to evaluate the Health of the containers # noqa: E501

    :param threshold: 
    :type threshold: float

    :rtype: None
    """
    message = {
            'command' : 'change_all_threshold',
            'address' : socket.gethostbyname(socket.gethostname()),
            'threshold' : threshold }
    return json.dumps(client.send_controller_sync(message, '172.16.3.167'))


def change_threshold(address, threshold):  # noqa: E501
    """Update the threshold of the selected docker manager

    It changes the threshold used by the selected docker manager to evaluate the Health of the containers # noqa: E501

    :param address: the address of the machine which maintains the manager
    :type address: str
    :param threshold: the address of the machine which maintains the manager
    :type threshold: float

    :rtype: None
    """
    message = {
            'command' : 'change_threshold',
            'address' : address,
            'threshold' : threshold }
    return json.dumps(client.send_controller_sync(message, '172.16.3.167'))


def get_all_containers():  # noqa: E501
    """Get all managed containers

    It gives a list of all the Docker hosts with all the allocated containers # noqa: E501


    :rtype: None
    """
    message = {
            'command' : 'get_all_containers',
            'address' : socket.gethostbyname(socket.gethostname()),
    }
    return json.dumps(client.send_controller_sync(message, '172.16.3.167'))


def get_container(container_id,address):  # noqa: E501
    """Get a container

    Returns the information about a container identified by the ip address of the target machine and the containerID # noqa: E501

    :param container_id: the ID associated with the container the user want to get from the service
    :type container_id: str
    :param address: the address of the machine which maintains the container
    :type address: str

    :rtype: None
    """
    message = {
            'command' : 'get_container',
            'address' : address,
            'containerID' : container_id }
    return json.dumps(client.send_controller_sync(message, '172.16.3.167'))


def get_host_containers(address):  # noqa: E501
    """Get all the containers

    It gives all the containers maintained by the specified host # noqa: E501

    :param address: the address of the machine which maintains the containers
    :type address: str

    :rtype: None
    """
    message = {
            'command' : 'get_host_containers',
            'address' : address,
    }
    return json.dumps(client.send_controller_sync(message, '172.16.3.167'))


def remove_container(container_id, address):  # noqa: E501
    """Remove a container from the service

    It removes from the service management the container specified by the given ID and located into the given address. After the service removal the container will be leaved on the machine in its current status # noqa: E501

    :param container_id: the ID associated with the container the user want to remove from the service
    :type container_id: str
    :param address: the address of the machine which maintains the container
    :type address: str

    :rtype: None
    """
    message = {
            'command' : 'remove_container',
            'address' : address,
            'containerID' : container_id }
    return json.dumps(client.send_controller_sync(message, '172.16.3.167'))


def remove_host(address, password):  # noqa: E501
    """Remove a Docker host

    It removes from the service management the container specified by the given ID. The docker host and its containers will be leaved on the machine in theirs current status # noqa: E501

    :param address: the address of the machine which maintains the manager
    :type address: str
    :param password: The password used from the root user of the destination machine
    :type password: str

    :rtype: None
    """
    message = {
            'command' : 'remove_host',
            'address' : address,
            'password' : password }
    return json.dumps(client.send_controller_sync(message, '172.16.3.167'))
