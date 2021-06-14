# coding: utf-8

from __future__ import absolute_import
import unittest

from flask import json
from six import BytesIO

from openapi_server.models.inline_response2003 import InlineResponse2003  # noqa: E501
from openapi_server.models.unknownbasetype import UNKNOWN_BASE_TYPE  # noqa: E501
from openapi_server.test import BaseTestCase


class TestTestController(BaseTestCase):
    """TestController integration test stubs"""

    @unittest.skip("Connexion does not support multiple consummes. See https://github.com/zalando/connexion/pull/760")
    def test_add_antagonists(self):
        """Test case for add_antagonists

        Add an antagonist
        """
        headers = { 
            'Content-Type': 'application/x-www-form-urlencoded',
        }
        data = dict(aggressivity=56,
                    behaviour=56)
        response = self.client.open(
            '/healthmonitor/test',
            method='PUT',
            headers=headers,
            data=data,
            content_type='application/x-www-form-urlencoded')
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))

    @unittest.skip("Connexion does not support multiple consummes. See https://github.com/zalando/connexion/pull/760")
    def test_add_host_antagonist(self):
        """Test case for add_host_antagonist

        Add an antagonist
        """
        headers = { 
            'Content-Type': 'application/x-www-form-urlencoded',
        }
        data = dict(aggressivity=56,
                    behaviour=56)
        response = self.client.open(
            '/healthmonitor/test/{hostname}'.format(hostname='hostname_example'),
            method='PUT',
            headers=headers,
            data=data,
            content_type='application/x-www-form-urlencoded')
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))

    @unittest.skip("Connexion does not support multiple consummes. See https://github.com/zalando/connexion/pull/760")
    def test_change_antagonists_config(self):
        """Test case for change_antagonists_config

        Update the configuration used by an antagonist
        """
        unknown_base_type = openapi_server.UNKNOWN_BASE_TYPE()
        headers = { 
            'Content-Type': 'application/x-www-form-urlencoded',
        }
        response = self.client.open(
            '/healthmonitor/test',
            method='POST',
            headers=headers,
            data=json.dumps(unknown_base_type),
            content_type='application/x-www-form-urlencoded')
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))

    @unittest.skip("Connexion does not support multiple consummes. See https://github.com/zalando/connexion/pull/760")
    def test_change_host_antagonist_config(self):
        """Test case for change_host_antagonist_config

        Update the configuration used by an antagonist
        """
        unknown_base_type = openapi_server.UNKNOWN_BASE_TYPE()
        headers = { 
            'Content-Type': 'application/x-www-form-urlencoded',
        }
        response = self.client.open(
            '/healthmonitor/test/{hostname}'.format(hostname='hostname_example'),
            method='POST',
            headers=headers,
            data=json.dumps(unknown_base_type),
            content_type='application/x-www-form-urlencoded')
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))

    def test_get_report(self):
        """Test case for get_report

        Get the results
        """
        headers = { 
            'Accept': 'application/json',
        }
        response = self.client.open(
            '/healthmonitor/test',
            method='GET',
            headers=headers)
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))

    def test_remove_antagonists(self):
        """Test case for remove_antagonists

        Remove all the antagonists
        """
        headers = { 
        }
        response = self.client.open(
            '/healthmonitor/test',
            method='DELETE',
            headers=headers)
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))

    def test_remove_host_antagonist(self):
        """Test case for remove_host_antagonist

        Remove an antagonist from a docker host
        """
        headers = { 
        }
        response = self.client.open(
            '/healthmonitor/test/{hostname}'.format(hostname='hostname_example'),
            method='DELETE',
            headers=headers)
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))


if __name__ == '__main__':
    unittest.main()
