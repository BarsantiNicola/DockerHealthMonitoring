import connexion
import six

from openapi_server.models.inline_response2003 import InlineResponse2003  # noqa: E501
from openapi_server.models.unknownbasetype import UNKNOWN_BASE_TYPE  # noqa: E501
from openapi_server import util


def add_antagonists(aggressivity, behaviour):  # noqa: E501
    """Add an antagonist

    It adds a new antagonist on all the docker host # noqa: E501

    :param aggressivity: the probability(0-100%) that the antagonist will attack the containers
    :type aggressivity: int
    :param behaviour: the probability(0-100%) that the antagonist will shut down a container insted of applying a packet loss(packet loss is the remaining probability)
    :type behaviour: int

    :rtype: None
    """
    return 'do some magic!'


def add_host_antagonist(hostname, aggressivity, behaviour):  # noqa: E501
    """Add an antagonist

    It adds a new antagonist on the selected docker host # noqa: E501

    :param hostname: the hostname of the machine
    :type hostname: str
    :param aggressivity: the probability(0-100%) that the antagonist will attack the containers
    :type aggressivity: int
    :param behaviour: the probability(0-100%) that the antagonist will shut down a container insted of applying a packet loss(packet loss is the remaining probability)
    :type behaviour: int

    :rtype: None
    """
    return 'do some magic!'


def change_antagonists_config(unknown_base_type=None):  # noqa: E501
    """Update the configuration used by an antagonist

    It changes the configuration used by an antagonist into the defined docker host # noqa: E501

    :param unknown_base_type: 
    :type unknown_base_type: dict | bytes

    :rtype: None
    """
    if connexion.request.is_json:
        unknown_base_type = UNKNOWN_BASE_TYPE.from_dict(connexion.request.get_json())  # noqa: E501
    return 'do some magic!'


def change_host_antagonist_config(hostname, unknown_base_type=None):  # noqa: E501
    """Update the configuration used by an antagonist

    It changes the configuration used by an antagonist into the defined docker host # noqa: E501

    :param hostname: the hostname of the machine
    :type hostname: str
    :param unknown_base_type: 
    :type unknown_base_type: dict | bytes

    :rtype: None
    """
    if connexion.request.is_json:
        unknown_base_type = UNKNOWN_BASE_TYPE.from_dict(connexion.request.get_json())  # noqa: E501
    return 'do some magic!'


def get_report():  # noqa: E501
    """Get the results

    It gives back the results of the last test # noqa: E501


    :rtype: InlineResponse2003
    """
    return 'do some magic!'


def remove_antagonists():  # noqa: E501
    """Remove all the antagonists

    It stops all the antagonist running on the service # noqa: E501


    :rtype: None
    """
    return 'do some magic!'


def remove_host_antagonist(hostname):  # noqa: E501
    """Remove an antagonist from a docker host

    It stops an antagonist running on the selected docker host # noqa: E501

    :param hostname: the hostname of the machine which maintains the antagonist
    :type hostname: str

    :rtype: None
    """
    return 'do some magic!'
