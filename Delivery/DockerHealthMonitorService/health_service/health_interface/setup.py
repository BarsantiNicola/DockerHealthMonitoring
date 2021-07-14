# coding: utf-8

import sys
from setuptools import setup, find_packages

NAME = "swagger_server"
VERSION = "1.0.0"
# To install the library, run the following
#
# python setup.py install
#
# prerequisite: setuptools
# http://pypi.python.org/pypi/setuptools

REQUIRES = ["connexion"]

setup(
    name=NAME,
    version=VERSION,
    description="API",
    author_email="",
    url="",
    keywords=["Swagger", "API"],
    install_requires=REQUIRES,
    packages=find_packages(),
    package_data={'': ['swagger/swagger.yaml']},
    include_package_data=True,
    entry_points={
        'console_scripts': ['swagger_server=swagger_server.__main__:main']},
    long_description="""\
    Interface for communicating with the Health-Monitor service. Its functionalities can be organized in the following set of operations:    - Operations for service management:  permits to add and remove docker hosts to the system and to uninstall it    - Operations for container management: permits to see the managed containers, their status and to change the container manager configuration    - Operations for testing purpose: permits to test the service with configurable attacks to the containers
    """
)
