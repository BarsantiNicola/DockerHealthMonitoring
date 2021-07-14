#!/bin/sh

echo -n "Insert the IPv4 address of the installation machine: "
read IP

ssh root@$IP 'python3 /root/health_service/health-controller/uninstall.py'
