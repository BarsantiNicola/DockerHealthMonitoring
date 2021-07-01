import os
import random
import numpy
from rabbit import rabbit_client
from numpy.random import default_rng
from time import sleep
import logging
import sys
import coloredlogs
import threading
import socket

class antagonist:
    
    def __init__(self, config, manager):
        self._logger = None
        
        self._balance = 0.5
        self._heavy_rate = 0.5
        self._pkt_loss_rate = 20
        self._freq_param = 10
        self._duration_param = 5
        self._manager = manager
        self._exit = True
        self._attack = False
        self._rabbit = None
        self._configuration = config
        self._interface = {
                'start_antagonist' : self._enable_antagonist,
                'stop_antagonist' : self._disable_antagonist,
                'conf_antagonist' : self._conf_antagonist
        }
        self._rng = default_rng()
        self._initialize_logger()
        self._init_rabbit()
        self._logger.debug("Antagonist ready")
        
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

      
        """  initialize the rabbitMQ client to be used by the controller class """    
    def _init_rabbit(self) -> bool:
        
        try:
            self._logger.debug("Connecting to the rabbitMQ broker.." + self._configuration['address'])
            # connect the client to the rabbitMQ broker 
            self._logger.debug("Connecting to the rabbitMQ broker..")
            self._rabbit = rabbit_client(self._configuration['address'],'antagonist',self._interface)
            self._logger.debug("Correctly connected to the broker")
            return True
        
        except KeyError:
            self._logger.error('Error, address field not found')
            
        return False 
    
    def _attack_containers(self, target):

        self._logger.info("Thread " + str(threading.get_ident()) + " for " + target.short_id + " started")

        while self._attack:
            
            ignored_containers = self._manager._ignore_list
            if not target.short_id in ignored_containers:
                if random.uniform(0,1)>self._heavy_rate:
                    if random.uniform(0,1) < self._balance:
                        self._logger.info("Shutdown container " + target.short_id)
                        target.stop()
                    else:
                        self._logger.info("Packet loss attack on container " + target.short_id)
                        self._exec_packet_loss_attack(self._manager._docker_env.inspect_container(target.short_id)['NetworkSettings']['Networks']['bridge']['IPAddress'])
            sleep(numpy.random.exponential(self._freq_param)) 
            
    def _set_packet_loss_attack(self):
        os.system("tc qdisc del dev docker0 parent 1:1")
        os.system("tc qdisc add dev docker0 root handle 1: prio priomap 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0")
        os.system("tc qdisc add dev docker0 parent 1:1 handle 10: netem loss " + str(self._pkt_loss_rate)+"%")
        os.system("tc qdisc add dev docker0 parent 1:2 handle 11: netem")

        
    def _exec_packet_loss_attack(self, target_address):
        os.system("tc filter del dev docker0 parent 1:0 protocol ip prio 1 u32 match ip dst "+ target_address +" flowid 1:2")
        os.system("tc filter add dev docker0 parent 1:0 protocol ip prio 1 u32 match ip dst "+ target_address +" flowid 1:1")
        sleep(abs(numpy.random.exponential(self._duration_param)))
        os.system("tc filter del dev docker0 parent 1:0 protocol ip prio 1 u32 match ip dst "+ target_address +" flowid 1:1")
        os.system("tc filter add dev docker0 parent 1:0 protocol ip prio 1 u32 match ip dst "+ target_address +" flowid 1:2")
    
    def _enable_antagonist(self, message):
        self._logger.info("Start antagonist attack")
        containers = self._manager._get_all_containers()
        self._set_packet_loss_attack()
        self._attack = True
        numpy.random.seed(123)
        ignore_list = self._manager._ignore_list
        for container in containers:
            if not container.short_id in ignore_list:
                self._logger.debug("Launching attack thread for " + container.short_id)
                threading.Thread(target=self._attack_containers, args=(container,)).start()
                
        return {'command':'ok','description': 'Antagonist started'}
    
    def _disable_antagonist(self, message):
        self._attack = False
        self._logger.info("Antagonist attack stopped")
        return {'command':'ok', 'description' : 'Antagonist stopped' }
    
    def _conf_antagonist(self, message):
        
        if self._attack is True:
            return {'command':'error','address':socket.gethostbyname(socket.gethostname()), 'description': 'Configuration locked during a test' }
        
        try:
            self._balance = message['balance']
            self._logger.debug("Balance param updated to " + str(self._balance))
        except KeyError:
            pass
        
        try:
            self._heavy_rate = message['heavy']
            self._logger.debug("Heavy param updated to " + str(self._heavy_rate))
        except KeyError:
            pass
        
        try:
            self._freq_param = message['frequency']
            self._logger.debug("Frequecy param updated to " + str(self._freq_param))
        except KeyError:
            pass

        try:
            self._duration_param = message['duration']
            self._logger.debug("Duration param updated to " + str(self._duration_param))
        except KeyError:
            pass
        
        self._logger.info("Antagonist configuration changed")
        return {'command':'ok', 'address':socket.gethostbyname(socket.gethostname()), 'description': 'Configuration updated' }
    
    def close_all(self):
        self._logger.info("Closing the antagonist")
        self._attack = False
     
