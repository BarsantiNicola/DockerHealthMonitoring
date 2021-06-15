import socket
import docker
import os
import random
from time import sleep

def start_antagonist():    
     os.system('tc qdisc add dev docker0 root netem loss 0.01%') # create the virtual net environment
     while(1):
        var = 0.01
        pkt_loss = str(var) + "%"
        print("Pkt Loss inserted ", pkt_loss)
        cmd = "tc qdisc change dev docker0 root netem loss "+pkt_loss # Insert Zero Packet loss on Docker network
        os.system(cmd)
        sleep(10)
        for i in range(2):
            var = random.randint(1,10)
            pkt_loss = str(var) + "%"
            print("Pkt Loss inserted ", pkt_loss)
            cmd = "tc qdisc change dev docker0 root netem loss "+pkt_loss # insert Random Packet Loss value (1% up to 10%)
            os.system(cmd)
            var = random.randint(1,8)
            sleep(var)
            client = docker.from_env()
            containers = client.containers.list() # list Active containers
            var = random.randint(0,len(containers)-1)
            target = containers[var] # choose one container at Random 
            print(target.short_id, "ATTACKED")
            target.stop()            # shut down the target container

start_antagonist()
