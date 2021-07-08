# coding: utf-8

from __future__ import absolute_import
from datetime import date, datetime  # noqa: F401

from typing import List, Dict  # noqa: F401

from swagger_server.models.base_model_ import Model
from swagger_server import util


class TestBody(Model):
    """NOTE: This class is auto generated by the swagger code generator program.

    Do not edit the class manually.
    """
    def __init__(self, heavy: int=None, balance: int=None, loss: int=None, duration: int=None, frequency: int=None):  # noqa: E501
        """TestBody - a model defined in Swagger

        :param heavy: The heavy of this TestBody.  # noqa: E501
        :type heavy: int
        :param balance: The balance of this TestBody.  # noqa: E501
        :type balance: int
        :param loss: The loss of this TestBody.  # noqa: E501
        :type loss: int
        :param duration: The duration of this TestBody.  # noqa: E501
        :type duration: int
        :param frequency: The frequency of this TestBody.  # noqa: E501
        :type frequency: int
        """
        self.swagger_types = {
            'heavy': int,
            'balance': int,
            'loss': int,
            'duration': int,
            'frequency': int
        }

        self.attribute_map = {
            'heavy': 'heavy',
            'balance': 'balance',
            'loss': 'loss',
            'duration': 'duration',
            'frequency': 'frequency'
        }
        self._heavy = heavy
        self._balance = balance
        self._loss = loss
        self._duration = duration
        self._frequency = frequency

    @classmethod
    def from_dict(cls, dikt) -> 'TestBody':
        """Returns the dict as a model

        :param dikt: A dict.
        :type: dict
        :return: The test_body of this TestBody.  # noqa: E501
        :rtype: TestBody
        """
        return util.deserialize_model(dikt, cls)

    @property
    def heavy(self) -> int:
        """Gets the heavy of this TestBody.

        Probability between 0 and 100 that an attacker perform an attack  # noqa: E501

        :return: The heavy of this TestBody.
        :rtype: int
        """
        return self._heavy

    @heavy.setter
    def heavy(self, heavy: int):
        """Sets the heavy of this TestBody.

        Probability between 0 and 100 that an attacker perform an attack  # noqa: E501

        :param heavy: The heavy of this TestBody.
        :type heavy: int
        """

        self._heavy = heavy

    @property
    def balance(self) -> int:
        """Gets the balance of this TestBody.

        Probability between 0 and 100 that an attacker perform a shutdown attack  # noqa: E501

        :return: The balance of this TestBody.
        :rtype: int
        """
        return self._balance

    @balance.setter
    def balance(self, balance: int):
        """Sets the balance of this TestBody.

        Probability between 0 and 100 that an attacker perform a shutdown attack  # noqa: E501

        :param balance: The balance of this TestBody.
        :type balance: int
        """

        self._balance = balance

    @property
    def loss(self) -> int:
        """Gets the loss of this TestBody.

        Percentage of packet loss  # noqa: E501

        :return: The loss of this TestBody.
        :rtype: int
        """
        return self._loss

    @loss.setter
    def loss(self, loss: int):
        """Sets the loss of this TestBody.

        Percentage of packet loss  # noqa: E501

        :param loss: The loss of this TestBody.
        :type loss: int
        """

        self._loss = loss

    @property
    def duration(self) -> int:
        """Gets the duration of this TestBody.

        Seconds of packet loss attack duration  # noqa: E501

        :return: The duration of this TestBody.
        :rtype: int
        """
        return self._duration

    @duration.setter
    def duration(self, duration: int):
        """Sets the duration of this TestBody.

        Seconds of packet loss attack duration  # noqa: E501

        :param duration: The duration of this TestBody.
        :type duration: int
        """

        self._duration = duration

    @property
    def frequency(self) -> int:
        """Gets the frequency of this TestBody.

        Seconds between two consecutives attack to the same container  # noqa: E501

        :return: The frequency of this TestBody.
        :rtype: int
        """
        return self._frequency

    @frequency.setter
    def frequency(self, frequency: int):
        """Sets the frequency of this TestBody.

        Seconds between two consecutives attack to the same container  # noqa: E501

        :param frequency: The frequency of this TestBody.
        :type frequency: int
        """

        self._frequency = frequency