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
    description="Health Monitor REST API",
    author_email="",
    url="",
    keywords=["Swagger", "Health Monitor REST API"],
    install_requires=REQUIRES,
    packages=find_packages(),
    package_data={'': ['swagger/swagger.yaml']},
    include_package_data=True,
    entry_points={
        'console_scripts': ['swagger_server=swagger_server.__main__:main']},
    long_description="""\
    REST API for remote control and management of the Docker Health System by users. Allow the display of containers maintained on systems, add and remove containers or new machines. Modify the operating parameters of the system and launch a testing application to verify the functionality of the system
    """
)
