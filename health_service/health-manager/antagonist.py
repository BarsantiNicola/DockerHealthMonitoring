import socket
import docker
import os
import random
from time import sleep

comm_client = rabbit_client('172.17.0.2', 'antagonist',{'start': start_antagonist, 'soft_attack': soft,'medium_attack': medium, 'heavy_attack': heavy, 'pause': pause})
shut_down_rate = 1000

def start_antagonist():    
    global shut_down_rate
    os.system('tc qdisc add dev docker0 root netem loss 0.0001%') # create the virtual net environment
    client = docker.from_env()
    while(1):
        containers = client.containers.list() # list Active containers
        for target in containers
            if (random.gauss(10,3) > shut_down_rate) :
                target.stop()
        sleep(1)    
    
    
def pause():
    global shut_down_rate
    os.system("tc qdisc change dev docker0 root netem loss 0.0001%")
    shut_down_rate = 1000
    
    
def soft():
    global shut_down_rate
    os.system("tc qdisc change dev docker0 root netem loss 1%")
    shut_down_rate = 15
     
     
def medium():
    global shut_down_rate
    os.system("tc qdisc change dev docker0 root netem loss 2%")
    shut_down_rate = 13

    
def heavy():
    global shut_down_rate
    os.system("tc qdisc change dev docker0 root netem loss 7%")
    shut_down_rate = 12 

# start_antagonist()
