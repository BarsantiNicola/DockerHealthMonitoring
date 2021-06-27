import docker
import os
import random
import numpy
from rabbit import rabbit_client
from numpy.random import default_rng
from time import sleep
import logging
import sys
import coloredlogs

class antagonist:
    
    def __init__(self, manager):
        self._logger = None
        
        self._shut_down_rate = int()
        self._pkt_loss_rate = int()
        
        self._freq_param = float()
        self._duration_param = float()
        self._system_active_flag = int()
        self._docker_client = None
        self._manager = manager
        self._exit = True
        
        self._rng = default_rng()
        self._initialize_logger()
        
        if self._initialize_docker_client() is False:
            return
        
    """ configure the logger behaviour """
    def _initialize_logger(self):
        self._logger = logging.getLogger(__name__)
    
        # prevent to allocate more handlers into a previous used logger
        if not self._logger.hasHandlers():
            handler = logging.StreamHandler(sys.stdout)
            formatter = coloredlogs.ColoredFormatter("%(asctime)s %(name)s"
                                                 " %(levelname)s %(message)s",
                                                 "%Y-%m-%d %H:%M:%S")
            handler.setFormatter(formatter)

            self._logger.addHandler(handler)
            self._logger.setLevel(logging.DEBUG)   # logger threshold  

    def _initialize_docker_client(self) -> bool:
        try:
            self._docker_client = docker.from_env()
        except:
            self._logger.error("Error during connection with the local docker")
            return False
      
    def container_shutdown_attack(self, target):

        while not self._attack:
            pass
        self._logger.debug ("Shutdown attack in progress:",str(self._shut_down_rate),str(self._pkt_loss_rate), str(self._duration_param))

        ignored_containers = self._manager._ignore_list
        if target.short_id in ignored_containers:
            return
            
        while self._attack:   
            value = random.uniform(0,1)
            if (value < self._shut_down_rate) :
                target.stop()
            elif value < self._shut_down_rate + self._pkt_loss_rate:
                # insert into thread
                self._packet_loss_attack(self._manager._docker_env.inspect_container(target.short_id)['NetworkSettings']['Networks']['bridge']['IPAddress'])
            sleep(numpy.random.exponential(self._freq_param)) 
            
    def set_packet_loss_attack(self):
        os.system("tc qdisc del dev docker0 parent 1:1")
        os.system("tc qdisc add dev docker0 root handle 1: prio priomap 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0")
        os.system("tc qdisc add dev docker0 parent 1:1 handle 10: netem loss " + str(self._pkt_loss_rate)+"%")

        
    def exec_packet_loss_attack(self, address):
        self._logger.debug("Packet loss attack on " + address + ". Packet loss: " + self._pkt_loss_rate + " Duration: " + self._duration_param)
        os.system("tc filter add dev docker0 parent 1:0 protocol ip prio 1 u32 match ip dst "+ address +" flowid 1:1")
        sleep(abs(numpy.random.exponential(self._duration_param)))
        os.system("tc filter add dev docker0 parent 1:0 protocol ip prio 1 u32 match ip dst "+ address +" flowid 1:0")

        #self._logger.debug ("Packet loss attack in progress:",str(self._shut_down_rate),str(self._pkt_loss_rate), str(self._duration_param))
        #cmd = "tc qdisc change dev docker0 root netem loss "+str(self._pkt_loss_rate)+"%"
        #os.system(cmd)
        #while self._attack:
        #    pass
        #os.system("tc qdisc change dev docker0 root netem loss 0.00001%") # remove pkt drop
    
    def _enable_antagonist(self, message):
        return {'command':'ok'}
    
    def _disable_antagonist(self, message):
        return {'command':'ok'}
    
    def _conf_antagonist(self, message):
        return {'command':'ok'}
    
    
     
"""    
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
            logger.debug("attack interval:",str(attack_interval),"s")
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
start_antagonist()"""
