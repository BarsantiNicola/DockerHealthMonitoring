# coding: utf-8

from __future__ import absolute_import
from datetime import date, datetime  # noqa: F401

from typing import List, Dict  # noqa: F401

from swagger_server.models.base_model_ import Model
from swagger_server import util


class ContainersAddressBody(Model):
    """NOTE: This class is auto generated by the swagger code generator program.

    Do not edit the class manually.
    """
    def __init__(self, password: str=None):  # noqa: E501
        """ContainersAddressBody - a model defined in Swagger

        :param password: The password of this ContainersAddressBody.  # noqa: E501
        :type password: str
        """
        self.swagger_types = {
            'password': str
        }

        self.attribute_map = {
            'password': 'password'
        }
        self._password = password

    @classmethod
    def from_dict(cls, dikt) -> 'ContainersAddressBody':
        """Returns the dict as a model

        :param dikt: A dict.
        :type: dict
        :return: The containers_address_body of this ContainersAddressBody.  # noqa: E501
        :rtype: ContainersAddressBody
        """
        return util.deserialize_model(dikt, cls)

    @property
    def password(self) -> str:
        """Gets the password of this ContainersAddressBody.


        :return: The password of this ContainersAddressBody.
        :rtype: str
        """
        return self._password

    @password.setter
    def password(self, password: str):
        """Sets the password of this ContainersAddressBody.


        :param password: The password of this ContainersAddressBody.
        :type password: str
        """

        self._password = password