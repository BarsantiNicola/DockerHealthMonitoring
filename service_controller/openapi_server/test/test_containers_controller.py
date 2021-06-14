# coding: utf-8

from __future__ import absolute_import
import unittest

from flask import json
from six import BytesIO

from openapi_server.models.inline_response200 import InlineResponse200  # noqa: E501
from openapi_server.models.inline_response2001 import InlineResponse2001  # noqa: E501
from openapi_server.models.inline_response2002 import InlineResponse2002  # noqa: E501
from openapi_server.test import BaseTestCase


class TestContainersController(BaseTestCase):
    """ContainersController integration test stubs"""

    def test_add_container(self):
        """Test case for add_container

        Add a new Docker container
        """
        headers = { 
        }
        response = self.client.open(
            '/healthmonitor/containers/{hostname}/{container_id}'.format(container_id='container_id_example', hostname='hostname_example'),
            method='PUT',
            headers=headers)
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))

    @unittest.skip("Connexion does not support multiple consummes. See https://github.com/zalando/connexion/pull/760")
    def test_add_host(self):
        """Test case for add_host

        Add a new Docker host
        """
        headers = { 
            'Content-Type': 'application/x-www-form-urlencoded',
        }
        data = dict(address='address_example',
                    username='username_example',
                    password='password_example')
        response = self.client.open(
            '/healthmonitor/containers/{hostname}'.format(hostname='hostname_example'),
            method='PUT',
            headers=headers,
            data=data,
            content_type='application/x-www-form-urlencoded')
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))

    @unittest.skip("Connexion does not support multiple consummes. See https://github.com/zalando/connexion/pull/760")
    def test_change_all_threshold(self):
        """Test case for change_all_threshold

        Update the threshold of all the docker managers
        """
        body = 3.4
        headers = { 
            'Content-Type': 'application/x-www-form-urlencoded',
        }
        response = self.client.open(
            '/healthmonitor/containers',
            method='POST',
            headers=headers,
            data=json.dumps(body),
            content_type='application/x-www-form-urlencoded')
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))

    @unittest.skip("Connexion does not support multiple consummes. See https://github.com/zalando/connexion/pull/760")
    def test_change_threshold(self):
        """Test case for change_threshold

        Update the threshold of the selected docker manager
        """
        body = 3.4
        headers = { 
            'Content-Type': 'application/x-www-form-urlencoded',
        }
        response = self.client.open(
            '/healthmonitor/containers/{hostname}'.format(hostname='hostname_example'),
            method='POST',
            headers=headers,
            data=json.dumps(body),
            content_type='application/x-www-form-urlencoded')
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))

    def test_get_all_containers(self):
        """Test case for get_all_containers

        Get a container
        """
        headers = { 
            'Accept': 'application/json',
        }
        response = self.client.open(
            '/healthmonitor/containers',
            method='GET',
            headers=headers)
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))

    def test_get_container(self):
        """Test case for get_container

        Get a container
        """
        headers = { 
            'Accept': 'application/json',
        }
        response = self.client.open(
            '/healthmonitor/containers/{hostname}/{container_id}'.format(container_id='container_id_example', hostname='hostname_example'),
            method='GET',
            headers=headers)
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))

    def test_get_host_containers(self):
        """Test case for get_host_containers

        Get all the containers
        """
        headers = { 
            'Accept': 'application/json',
        }
        response = self.client.open(
            '/healthmonitor/containers/{hostname}'.format(hostname='hostname_example'),
            method='GET',
            headers=headers)
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))

    def test_remove_container(self):
        """Test case for remove_container

        Remove a container
        """
        headers = { 
        }
        response = self.client.open(
            '/healthmonitor/containers/{hostname}/{container_id}'.format(container_id='container_id_example', hostname='hostname_example'),
            method='DELETE',
            headers=headers)
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))

    @unittest.skip("Connexion does not support multiple consummes. See https://github.com/zalando/connexion/pull/760")
    def test_remove_host(self):
        """Test case for remove_host

        Remove a Docker host
        """
        headers = { 
            'Content-Type': 'application/x-www-form-urlencoded',
        }
        data = dict(password='password_example')
        response = self.client.open(
            '/healthmonitor/containers/{hostname}'.format(hostname='hostname_example'),
            method='DELETE',
            headers=headers,
            data=data,
            content_type='application/x-www-form-urlencoded')
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))


if __name__ == '__main__':
    unittest.main()
