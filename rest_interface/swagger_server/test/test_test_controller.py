# coding: utf-8

from __future__ import absolute_import

from flask import json
from six import BytesIO

from swagger_server.test import BaseTestCase


class TestTestController(BaseTestCase):
    """TestController integration test stubs"""

    def test_add_antagonists(self):
        """Test case for add_antagonists

        Add all the antagonists
        """
        response = self.client.open(
            '/healthmonitor/test',
            method='PUT')
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))

    def test_add_host_antagonist(self):
        """Test case for add_host_antagonist

        Add an antagonist
        """
        query_string = [('aggressivity', 1.2),
                        ('behaviour', 1.2)]
        response = self.client.open(
            '/healthmonitor/test/{address}'.format(address='address_example'),
            method='PUT',
            query_string=query_string)
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))

    def test_change_antagonists_config(self):
        """Test case for change_antagonists_config

        Update the configuration used by all the antagonists
        """
        query_string = [('heavy', 'heavy_example'),
                        ('balance', 1.2)]
        response = self.client.open(
            '/healthmonitor/test',
            method='POST',
            query_string=query_string)
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))

    def test_change_host_antagonist_config(self):
        """Test case for change_host_antagonist_config

        Update the configuration used by an antagonist
        """
        query_string = [('heavy', 1.2),
                        ('balance', 1.2)]
        response = self.client.open(
            '/healthmonitor/test/{address}'.format(address='address_example'),
            method='POST',
            query_string=query_string)
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))

    def test_remove_antagonists(self):
        """Test case for remove_antagonists

        Remove all the antagonists
        """
        response = self.client.open(
            '/healthmonitor/test',
            method='DELETE')
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))

    def test_remove_host_antagonist(self):
        """Test case for remove_host_antagonist

        Remove an antagonist from a docker host
        """
        response = self.client.open(
            '/healthmonitor/test/{address}'.format(address='address_example'),
            method='DELETE')
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))


if __name__ == '__main__':
    import unittest
    unittest.main()
