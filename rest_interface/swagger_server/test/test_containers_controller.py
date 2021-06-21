# coding: utf-8

from __future__ import absolute_import

from flask import json
from six import BytesIO

from swagger_server.test import BaseTestCase


class TestContainersController(BaseTestCase):
    """ContainersController integration test stubs"""

    def test_add_container(self):
        """Test case for add_container

        Add a new Docker container
        """
        response = self.client.open(
            '/healthmonitor/containers/{address}/{containerID}'.format(container_id='container_id_example', address='address_example'),
            method='PUT')
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))

    def test_add_host(self):
        """Test case for add_host

        Add a new Docker host
        """
        query_string = [('password', 'password_example')]
        response = self.client.open(
            '/healthmonitor/containers/{address}'.format(address='address_example'),
            method='PUT',
            query_string=query_string)
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))

    def test_change_all_threshold(self):
        """Test case for change_all_threshold

        Update the threshold of all the docker managers
        """
        query_string = [('threshold', 1.2)]
        response = self.client.open(
            '/healthmonitor/containers',
            method='POST',
            query_string=query_string)
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))

    def test_change_threshold(self):
        """Test case for change_threshold

        Update the threshold of the selected docker manager
        """
        query_string = [('threshold', 1.2)]
        response = self.client.open(
            '/healthmonitor/containers/{address}'.format(address='address_example'),
            method='POST',
            query_string=query_string)
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))

    def test_get_all_containers(self):
        """Test case for get_all_containers

        Get all managed containers
        """
        response = self.client.open(
            '/healthmonitor/containers',
            method='GET')
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))

    def test_get_container(self):
        """Test case for get_container

        Get a container
        """
        response = self.client.open(
            '/healthmonitor/containers/{address}/{containerID}'.format(container_id='container_id_example', address='address_example'),
            method='GET')
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))

    def test_get_host_containers(self):
        """Test case for get_host_containers

        Get all the containers
        """
        response = self.client.open(
            '/healthmonitor/containers/{address}'.format(address='address_example'),
            method='GET')
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))

    def test_remove_container(self):
        """Test case for remove_container

        Remove a container from the service
        """
        response = self.client.open(
            '/healthmonitor/containers/{address}/{containerID}'.format(container_id='container_id_example', address='address_example'),
            method='DELETE')
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))

    def test_remove_host(self):
        """Test case for remove_host

        Remove a Docker host
        """
        query_string = [('password', 'password_example')]
        response = self.client.open(
            '/healthmonitor/containers/{address}'.format(address='address_example'),
            method='DELETE',
            query_string=query_string)
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))


if __name__ == '__main__':
    import unittest
    unittest.main()
