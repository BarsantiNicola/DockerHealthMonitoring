import connexion
import six

from swagger_server import util


def add_antagonists():  # noqa: E501
    """Add all the antagonists

    Execute the antagonist into each machine under control of the service # noqa: E501


    :rtype: None
    """
    return 'do some magic!'


def add_host_antagonist(address, aggressivity, behaviour):  # noqa: E501
    """Add an antagonist

    It adds a new antagonist on the selected docker host # noqa: E501

    :param address: the IPv4 address of the destination machine
    :type address: str
    :param aggressivity: the probability(0-100%) that the antagonist will attack the containers
    :type aggressivity: float
    :param behaviour: the probability(0-100%) that the antagonist will shut down a container insted of applying a packet loss(packet loss is the remaining probability)
    :type behaviour: float

    :rtype: None
    """
    return 'do some magic!'


def change_antagonists_config(heavy, balance):  # noqa: E501
    """Update the configuration used by all the antagonists

    It changes the configuration used by the antogonists deployed in each machine under the service control # noqa: E501

    :param heavy: Define the impact of the antagonist on the containers. Three possibile values: hard, medium, low
    :type heavy: str
    :param balance: Define the behavior of the antagonist with a percentage which define the probability of performing a shutdown attack. Otherwise it will perform packet loss attack
    :type balance: float

    :rtype: None
    """
    return 'do some magic!'


def change_host_antagonist_config(address, heavy, balance=None):  # noqa: E501
    """Update the configuration used by an antagonist

    It changes the configuration used by an antagonist into the defined docker host # noqa: E501

    :param address: the IPv4 address of the destination machine
    :type address: str
    :param heavy: Define the impact of the antagonist on the containers. Three possibile values: hard, medium, low
    :type heavy: float
    :param balance: Define the behavior of the antagonist with a percentage which define the probability of performing a shutdown attack. Otherwise it will perform packet loss attack
    :type balance: float

    :rtype: None
    """
    return 'do some magic!'


def remove_antagonists():  # noqa: E501
    """Remove all the antagonists

    Stops the running antagonists in each machine under the service control # noqa: E501


    :rtype: None
    """
    return 'do some magic!'


def remove_host_antagonist(address):  # noqa: E501
    """Remove an antagonist from a docker host

    It stops an antagonist running on the selected docker host # noqa: E501

    :param address: the IPv4 address of the destination machine
    :type address: str

    :rtype: None
    """
    return 'do some magic!'
