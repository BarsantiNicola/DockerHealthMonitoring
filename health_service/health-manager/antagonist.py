import socket
import docker
import os
import random
import numpy
from rabbit import rabbit_client
from numpy.random import default_rng
from time import sleep

shut_down_rate = int()
pkt_loss_rate = int()
freq_param = float()
duration_param = float()
system_active_flag = int()

rng = default_rng()

def start_attack():
    global shut_down_rate
    global pkt_loss_rate
    global duration_param
    print ("attack in progress:",str(shut_down_rate),str(pkt_loss_rate), str(duration_param))
    cmd = "tc qdisc change dev docker0 root netem loss "+str(pkt_loss_rate)+"%"
    os.system(cmd)
    client = docker.from_env()
    containers = client.containers.list() # list Active containers
    for i in range(3):    
        for target in containers:
            if (random.gauss(10,3) > shut_down_rate) :
                target.stop()
                sleep(numpy.random.exponential(duration_param)) # duration of the attack (3 loops of shut down attack + pkt drop)
        
    os.system("tc qdisc change dev docker0 root netem loss 0.00001%") # remove pkt drop
    

def start_antagonist():    
    global shut_down_rate
    global pkt_loss_rate
    global system_active_flag
    global freq_param
    
    #system_active_flag = 0
    while(1):
        if system_active_flag == 1 :
            attack_interval = numpy.random.exponential(freq_param)
            start_attack()
            print("attack interval:",str(attack_interval),"s")
            if attack_interval<200: 
                sleep(attack_interval) # hold for next attack (max of 200 seconds)
                
        sleep(1) 
    
    
def pause():
    global system_active_flag
    os.system("tc qdisc change dev docker0 root netem loss 0.00001%")
    system_active_flag = 0
    
def test1():
    global shut_down_rate
    global pkt_loss_rate
    global freq_param
    global duration_param
    global system_active_flag
    # test1 - LOW intensity and LOW frequency attack

    shut_down_rate = 15 # 4,8% probability of the target container is shut down (by the normal distribution)
    pkt_loss_rate = 2   # 2% of packets are dropped randomly
    duration_param = 2  # set the duration of the attack
    
    freq_param = 15     # set the interval between the attacks
    
    system_active_flag = 1
     
def test2():
    global shut_down_rate
    global pkt_loss_rate
    global freq_param
    global duration_param
    global system_active_flag
    # test2 - HIGH intensity and LOW frequency attack
    
    shut_down_rate = 12 # 25% probability of the target container is shut down (by the normal distribution)
    pkt_loss_rate = 8   # 8% of packets are dropped randomly
    duration_param = 3  # set the duration of the attack
    
    freq_param = 15      # set the interval between the attacks
    
    system_active_flag = 1
    
def test3():
    global shut_down_rate
    global pkt_loss_rate
    global freq_param
    global duration_param
    global system_active_flag
    # test3 - HIGH intensity and HIGH frequency attack
    
    shut_down_rate = 12 # 25% probability of the target container is shut down (by the normal distribution)
    pkt_loss_rate = 8   # 8% of packets are dropped randomly
    duration_param = 3  # set the duration of the attack
    
    freq_param = 8      # set the interval between the attacks
    
    system_active_flag = 1
    
def test4():
    global shut_down_rate
    global pkt_loss_rate
    global freq_param
    global duration_param
    global system_active_flag
    # test4 - LOW intensity and HIGH frequency attack

    shut_down_rate = 15 # 4,8% probability of the target container is shut down (by the normal distribution)
    pkt_loss_rate = 2   # 2% of packets are dropped randomly
    duration_param = 2  # set the duration of the attack
    
    freq_param = 8     # set the interval between the attacks
    
    system_active_flag = 1

comm_client = rabbit_client('172.17.0.2', 'antagonist',{'test1': test1,'test2': test2, 'test3': test3, 'test4': test4, 'pause': pause})
os.system('tc qdisc add dev docker0 root netem loss 0.00001%')
#test1()
start_antagonist()
