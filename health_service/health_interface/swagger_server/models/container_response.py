# coding: utf-8

from __future__ import absolute_import
from datetime import date, datetime  # noqa: F401

from typing import List, Dict  # noqa: F401

from swagger_server.models.base_model_ import Model
from swagger_server.models.all_containers_response_description import AllContainersResponseDescription  # noqa: F401,E501
from swagger_server import util


class ContainerResponse(Model):
    """NOTE: This class is auto generated by the swagger code generator program.

    Do not edit the class manually.
    """
    def __init__(self, command: str=None, description: AllContainersResponseDescription=None):  # noqa: E501
        """ContainerResponse - a model defined in Swagger

        :param command: The command of this ContainerResponse.  # noqa: E501
        :type command: str
        :param description: The description of this ContainerResponse.  # noqa: E501
        :type description: AllContainersResponseDescription
        """
        self.swagger_types = {
            'command': str,
            'description': AllContainersResponseDescription
        }

        self.attribute_map = {
            'command': 'command',
            'description': 'description'
        }
        self._command = command
        self._description = description

    @classmethod
    def from_dict(cls, dikt) -> 'ContainerResponse':
        """Returns the dict as a model

        :param dikt: A dict.
        :type: dict
        :return: The ContainerResponse of this ContainerResponse.  # noqa: E501
        :rtype: ContainerResponse
        """
        return util.deserialize_model(dikt, cls)

    @property
    def command(self) -> str:
        """Gets the command of this ContainerResponse.

        type of results: ok or error  # noqa: E501

        :return: The command of this ContainerResponse.
        :rtype: str
        """
        return self._command

    @command.setter
    def command(self, command: str):
        """Sets the command of this ContainerResponse.

        type of results: ok or error  # noqa: E501

        :param command: The command of this ContainerResponse.
        :type command: str
        """

        self._command = command

    @property
    def description(self) -> AllContainersResponseDescription:
        """Gets the description of this ContainerResponse.


        :return: The description of this ContainerResponse.
        :rtype: AllContainersResponseDescription
        """
        return self._description

    @description.setter
    def description(self, description: AllContainersResponseDescription):
        """Sets the description of this ContainerResponse.


        :param description: The description of this ContainerResponse.
        :type description: AllContainersResponseDescription
        """

        self._description = description