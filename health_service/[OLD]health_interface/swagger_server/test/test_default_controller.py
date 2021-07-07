# coding: utf-8

from __future__ import absolute_import

from flask import json
from six import BytesIO

from swagger_server.models.bad_response import BadResponse  # noqa: E501
from swagger_server.models.containers_address_body import ContainersAddressBody  # noqa: E501
from swagger_server.models.containers_address_body1 import ContainersAddressBody1  # noqa: E501
from swagger_server.models.containers_body import ContainersBody  # noqa: E501
from swagger_server.models.correct_response import CorrectResponse  # noqa: E501
from swagger_server.models.test_address_body import TestAddressBody  # noqa: E501
from swagger_server.models.test_body import TestBody  # noqa: E501
from swagger_server.test import BaseTestCase


class TestDefaultController(BaseTestCase):
    """DefaultController integration test stubs"""

    def test_add_container(self):
        """Test case for add_container

        Add a container to the service
        """
        response = self.client.open(
            '/healthmonitor/containers/{address}/{containerID}'.format(address='address_example', container_id='container_id_example'),
            method='PUT')
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))

    def test_add_docker_manager(self):
        """Test case for add_docker_manager

        Add a new docker host into the service
        """
        body = ContainersAddressBody()
        response = self.client.open(
            '/healthmonitor/containers/{address}'.format(address='address_example'),
            method='PUT',
            data=json.dumps(body),
            content_type='application/json')
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))

    def test_change_all_antagonists_conf(self):
        """Test case for change_all_antagonists_conf

        Change all the antagonists configuration
        """
        body = TestBody()
        response = self.client.open(
            '/healthmonitor/test',
            method='POST',
            data=json.dumps(body),
            content_type='application/json')
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))

    def test_change_all_thresholds(self):
        """Test case for change_all_thresholds

        Change the threshold configured into each manager. 
        """
        body = ContainersBody()
        response = self.client.open(
            '/healthmonitor/containers',
            method='POST',
            data=json.dumps(body),
            content_type='application/json')
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))

    def test_change_antagonist_conf(self):
        """Test case for change_antagonist_conf

        Change an antagonist configuration
        """
        body = TestAddressBody()
        response = self.client.open(
            '/healthmonitor/test/{address}'.format(address='address_example'),
            method='POST',
            data=json.dumps(body),
            content_type='application/json')
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))

    def test_change_manager_threshold(self):
        """Test case for change_manager_threshold

        Change the threshold configured into the selected manager. 
        """
        body = ContainersAddressBody1()
        response = self.client.open(
            '/healthmonitor/containers/{address}'.format(address='address_example'),
            method='POST',
            data=json.dumps(body),
            content_type='application/json')
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))

    def test_get_all_containers(self):
        """Test case for get_all_containers

        Gives all the managed containers by the service
        """
        response = self.client.open(
            '/healthmonitor/containers',
            method='GET')
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))

    def test_get_container_info(self):
        """Test case for get_container_info

        Gives information about the selected container
        """
        response = self.client.open(
            '/healthmonitor/containers/{address}/{containerID}'.format(address='address_example', container_id='container_id_example'),
            method='GET')
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))

    def test_get_manager_containers(self):
        """Test case for get_manager_containers

        Get the status of the selected docker host and a list of all the managed containers with their status and the current packet loss percentage measured
        """
        response = self.client.open(
            '/healthmonitor/containers/{address}'.format(address='address_example'),
            method='GET')
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))

    def test_ignore_container(self):
        """Test case for ignore_container

        Remove a container from the service
        """
        response = self.client.open(
            '/healthmonitor/containers/{address}/{containerID}'.format(address='address_example', container_id='container_id_example'),
            method='DELETE')
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))

    def test_remove_docker_manager(self):
        """Test case for remove_docker_manager

        Remove a registered docker host into the service
        """
        response = self.client.open(
            '/healthmonitor/containers/{address}'.format(address='address_example'),
            method='DELETE')
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))

    def test_start_all_antagonists(self):
        """Test case for start_all_antagonists

        Starts all the antagonists
        """
        response = self.client.open(
            '/healthmonitor/test',
            method='PUT')
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))

    def test_start_antagonist(self):
        """Test case for start_antagonist

        Start an antagonist
        """
        response = self.client.open(
            '/healthmonitor/test/{address}'.format(address='address_example'),
            method='PUT')
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))

    def test_stop_all_antagonist(self):
        """Test case for stop_all_antagonist

        Stop all the antagonists
        """
        response = self.client.open(
            '/healthmonitor/test',
            method='DELETE')
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))

    def test_stop_antagonist(self):
        """Test case for stop_antagonist

        Stop an antagonist
        """
        response = self.client.open(
            '/healthmonitor/test/{address}'.format(address='address_example'),
            method='DELETE')
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))


if __name__ == '__main__':
    import unittest
    unittest.main()
