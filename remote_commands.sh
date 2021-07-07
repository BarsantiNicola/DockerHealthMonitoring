#!/bin/bash

echo "deb http://www.rabbitmq.com/debian/ testing main" >> /etc/apt/sources.list
#apt-get update

echo "Installing rabbitmq on the destination machine.."
apt-get install -y rabbitmq-server &> /dev/null

echo "Adding user health-monitor to the destination machine.."
rabbitmqctl add_user 'health-monitor' '2a55f70a841f18b97c3a7db939b7adc9e34a0f1b' &> /dev/null
rabbitmqctl set_permissions -p "/" "health-monitor" ".*" ".*" ".*" &> /dev/null

echo "Installing python environment.."
apt-get install -y python3.7 &> /dev/null
update-alternatives  --set python /usr/bin/python3.7 &> /dev/null
apt-get upgrade -y python3 &> /dev/null
apt-get upgrade -y python &> /dev/null
pip3 install --upgrade pip

echo "Installing python libraries.."
pip3 install -r /root/health_service/requirements.txt 
pip3 install --upgrade jsonschema &> /dev/null

echo "Generation of application folders on the destination machine.."
mkdir /root/data/availability &> /dev/null
mkdir /root/data/bandwidth &> /dev/null

echo "Generation of application services on the destination machine.."
chmod 0777 /root/health_service/docker-health-controller.service &> /dev/null
chmod 0777 /root/health_service/docker-health-interface.service &> /dev/null
mv /root/health_service/docker-health-controller.service /etc/systemd/system &> /dev/null
mv /root/health_service/docker-health-interface.service /etc/systemd/system &> /dev/null
cd /root &> /dev/null

echo "Starting services on the destination machine.."
systemctl daemon-reload &> /dev/null
systemctl enable rabbitmq-server &> /dev/null
systemctl start rabbitmq-server &> /dev/null

systemctl enable docker-health-controller &> /dev/null
systemctl enable docker-health-interface &> /dev/null

systemctl start docker-health-controller &> /dev/null
systemctl start docker-health-interface &> /dev/null

echo "Application correctly installed"


