#!/bin/bash

echo "deb http://www.rabbitmq.com/debian/ testing main" >> /etc/apt/sources.list
apt-get update
apt-get install -y rabbitmq-server

apt-get install -y python3.7 pip
update-alternatives  --set python /usr/bin/python3.7
pip install --no-cache-dir -r /root/health_manager/health_service/requirements.txt

chmod 0777 /root/health_service/docker-health-controller.service
mv /root/health_service/docker-health-controller.service /etc/systemd/system

cd /root
docker build -t health-monitor-interface rest_interface

systemctl daemon-reload
service rabbitmq-server start
service docker-health-controller start
docker run health-monitor-interface 

iptables -t nat -A PREROUTING -p tcp -i eth0 --dport 8080 -j DNAT --to-destination 172.17.0.3:8080
# todo enable rabbitmq on localhost
