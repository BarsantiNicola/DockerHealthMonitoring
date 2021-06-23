#!/bin/bash

echo -n Insert the IPv4 address of the destination machine:
read IP

scp -r health_service rest_interface root@$IP:/root
ssh root@$IP 'bash -s' < remote_commands.sh
 

