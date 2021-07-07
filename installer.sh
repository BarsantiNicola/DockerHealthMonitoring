#!/bin/bash

echo -n Insert the IPv4 address of the destination machine:
read IP

echo '{"address": "'$IP'"}' > health_service/health-controller/configuration
echo '{"address": "'$IP'"}' > health_service/health_interface/configuration

scp -r health_service root@$IP:/root
ssh root@$IP 'bash -s' < remote_commands.sh

 

