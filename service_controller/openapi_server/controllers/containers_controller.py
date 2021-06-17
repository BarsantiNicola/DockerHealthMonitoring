import connexion
import six
from docker_controller import controller
from openapi_server.models.inline_response200 import InlineResponse200  # noqa: E501
from openapi_server.models.inline_response2001 import InlineResponse2001  # noqa: E501
from openapi_server.models.inline_response2002 import InlineResponse2002  # noqa: E501
from openapi_server import util
import json

control = controller()

def add_container(container_id, hostname):  # noqa: E501
    """Add a new Docker container

    It adds a new docker container from the available Docker containers to be managed by our Health monitoring system # noqa: E501

    :param container_id: the ID associated with the container the user want to add to the service
    :type container_id: str
    :param hostname: the hostname of the machine which maintains the container
    :type hostname: str

    :rtype: None
    """
    # todo verification hostname exists
    control._rabbit.send_manager_unicast(json.dumps(
            {
                    'command' : 'container_add',
                    'containerID' : container_id
            }), hostname)
    return InlineResponse200


def add_host(hostname, address, username=None, password=None):  # noqa: E501
    """Add a new Docker host

    It adds a new docker host in which our service must be deployed # noqa: E501

    :param hostname: the hostname of the machine
    :type hostname: str
    :param address: the IPv4 address of a machine
    :type address: str
    :param username: the username to be used to access the machine. If missing the service will use root
    :type username: str
    :param password: the password to be used to access the machine. If missing the service will assume that no password is setted
    :type password: str

    :rtype: None
    """
    
    if control.load_docker_manager(address, password) is True:
        return InlineResponse200
    else:
        return InlineResponse2001


def change_all_threshold(body):  # noqa: E501
    """Update the threshold of all the docker managers

    It changes the threshold used by all the docker managers to evaluate the Health of the containers # noqa: E501

    :param body: 
    :type body: 

    :rtype: None
    """
    return control._rabbit.send_manager_multicast(json.dumps({
                'command' : 'container_threshold',
                	'threshold': body['threshold']
    }))
    return InlineResponse200


def change_threshold(hostname, body):  # noqa: E501
    """Update the threshold of the selected docker manager

    It changes the threshold used by the selected docker manager to evaluate the Health of the containers # noqa: E501

    :param hostname: the hostname of the machine
    :type hostname: str
    :param body: 
    :type body: 

    :rtype: None
    """
    return control._rabbit.send_manager_unicast(json.dumps({
                'command' : 'container_threshold',
                	'threshold': body['threshold']
    }),hostname)
    return InlineResponse200


def get_all_containers():  # noqa: E501
    """Get a container

    It gives a list of all the Docker hosts with all the allocated containers # noqa: E501


    :rtype: List[InlineResponse2002]
    """
    return control.get_containers_content()


def get_container(container_id, hostname):  # noqa: E501
    """Get a container

    It gives the container specified by its ID # noqa: E501

    :param container_id: the ID associated with the container the user want to add to the service
    :type container_id: str
    :param hostname: the hostname of the machine which maintains the container
    :type hostname: str

    :rtype: InlineResponse200
    """
    return 'do some magic!'


def get_host_containers(hostname):  # noqa: E501
    """Get all the containers

    It gives all the containers maintaines by the specified host # noqa: E501

    :param hostname: the hostname of the machine which maintains the containers
    :type hostname: str

    :rtype: InlineResponse2001
    """
    return control.get_container_content(hostname)


def remove_container(container_id, hostname):  # noqa: E501
    """Remove a container

    It removes from the service management the container specified by the given ID. The container will be leaved on the machine in its current status # noqa: E501

    :param container_id: the ID associated with the container the user want to add to the service
    :type container_id: str
    :param hostname: the hostname of the machine which maintains the container
    :type hostname: str

    :rtype: None
    """
    
        # todo verification hostname exists
    control._rabbit.send_manager_unicast(json.dumps(
            {
                    'command' : 'container_ignore',
                    'containerID' : container_id
            }), hostname)
    return InlineResponse200


def remove_host(hostname, password=None):  # noqa: E501
    """Remove a Docker host

    It removes from the service management the container specified by the given ID. The container will be leaved on the machine in its current status # noqa: E501

    :param hostname: the hostname of the machine which maintains the container
    :type hostname: str
    :param password: The password used on the selected host. It&#39;s used to ensure that the user has the permission to perform the task
    :type password: str

    :rtype: None
    """
    if control.remove_docker_manager(hostname) is False:
        return InlineResponse2001
    return InlineResponse200
