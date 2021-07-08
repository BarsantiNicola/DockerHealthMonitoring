import os
import random
import numpy
from rabbit import rabbit_client
from time import sleep
import logging
import sys
import coloredlogs
import threading
import socket
class antagonist:
    
    def __init__(self, config, manager):
              
        self._manager = manager
        self._configuration = config
        self._exit = True
        self._attack = False
        self._rabbit = None
        self._logger = None
        
        self._balance = 50
        self._balance_lock = threading.Lock()
        self._heavy_rate = 60
        self._heavy_rate_lock = threading.Lock()
        self._pkt_loss_rate = 80
        self._pkt_loss_rate_lock = threading.Lock()
        self._freq_param = 0.5
        self._freq_param_lock = threading.Lock()
        self._duration_param = 5
        self._duration_param_lock = threading.Lock()

        self._interface = {
                'start_antagonist' : self._enable_antagonist,
                'stop_antagonist' : self._disable_antagonist,
                'conf_antagonist' : self._conf_antagonist
        }
        
        self._initialize_logger()
        self._init_rabbit()
        self._logger.debug("Antagonist ready")
        
    """ configure the logger behaviour """
    def _initialize_logger(self):
        self._logger = logging.getLogger(__name__)
        
        # prevent to allocate more handlers into a previous used logger
        if not self._logger.hasHandlers():
            handler = logging.StreamHandler(sys.stdout)
            file_handler = logging.FileHandler('/var/log/health_monitor_antagonist.log')
            formatter = coloredlogs.ColoredFormatter("%(asctime)s %(name)s"
                                                 " %(levelname)s %(message)s",
                                                 "%Y-%m-%d %H:%M:%S")
            handler.setFormatter(formatter)
            file_handler.setFormatter(formatter)
            file_handler.setLevel(logging.DEBUG)
            handler.setLevel(logging.DEBUG)
            self._logger.addHandler(handler)
            self._logger.addHandler(file_handler)
            self._logger.setLevel(logging.DEBUG)
      
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

    
    """ MUTUAL EXCLUSION DATA MANAGEMENT """
    
    """ we have five variables into the antagonist that could be accessed cuncurrently by different threads and
        requires mutual exclusion """
    
    """ gets the balance value respecting mutual exclusion """
    def _get_balance(self):
        with self._balance_lock:
            return self._balance
        
    """ sets the balance value respecting mutual exclusion """    
    def _set_balance(self, balance):
        with self._balance_lock:
            self._balance = balance

    """ gets the heavy value respecting mutual exclusion """
    def _get_heavy(self):
        with self._heavy_rate_lock:
            return self._heavy_rate
        
    """ sets the heavy value respecting mutual exclusion """    
    def _set_heavy(self, heavy):
        with self._heavy_rate_lock:
            self._heavy_rate = heavy
            
    """ gets the packet loss rate value respecting mutual exclusion """
    def _get_packet_loss(self ):
        with self._pkt_loss_rate_lock:
            return self._pkt_loss_rate
        
    """ sets the packet loss rate value respecting mutual exclusion """    
    def _set_packet_loss(self, packet_loss):
        with self._pkt_loss_rate_lock:
            self._pkt_loss_rate = packet_loss

    """ gets the frequency value respecting mutual exclusion """
    def _get_frequency(self):
        with self._freq_param_lock:
            return self._freq_param
        
    """ sets the frequency value respecting mutual exclusion """    
    def _set_frequency(self, frequency):
        with self._freq_param_lock:
            self._freq_param = frequency

    """ gets the duration value respecting mutual exclusion """
    def _get_duration(self):
        with self._duration_param_lock:
            return self._duration_param
        
    """ sets the duration value respecting mutual exclusion """    
    def _set_duration(self, duration):
        with self._duration_param_lock:
            self._duration_param = duration
         
    """ ANTAGONIST ATTACKS """
    
    def _attack_containers(self, targetID):

        self._logger.info("Thread " + str(threading.get_ident()) + " for " + str(targetID) + " started")

        while self._attack is True:
            try:
                if self._manager._is_ignored(targetID) is False:
                    if random.uniform(0,1)<self._get_heavy()/100:
                        if random.uniform(0,1) < self._get_balance()/100:
                            self._logger.info("Shutdown container " + str(targetID))
                            self._manager._shutdown_container(targetID)
                        else:
                            self._logger.info("Packet loss attack on container " + str(targetID))
                            self._exec_packet_loss_attack(self._manager._get_ip_addr(targetID))
            except:
                self._logger.warning("An exception has occurred during the attack")
                pass
            sleep(numpy.random.exponential(self._freq_param)) 
        self._logger.info("Thread " + str(threading.get_ident()) + " for " + str(targetID) + " stopped")
            
    def _set_packet_loss_attack(self):
        os.system("tc qdisc add dev docker0 root handle 1: prio priomap 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0")
        os.system("tc qdisc add dev docker0 parent 1:1 handle 10: netem")
        os.system("tc qdisc del dev docker0 parent 1:2 handle 11: netem loss " + str(self._get_packet_loss())+"%")
        os.system("tc qdisc add dev docker0 parent 1:2 handle 11: netem loss " + str(self._get_packet_loss())+"%")

        
    def _exec_packet_loss_attack(self, target_address):
        self._logger.info("Starting attack on " + target_address)
        os.system("tc filter del dev docker0 parent 1:0 protocol ip prio 1 u32 match ip dst "+ target_address +" flowid 1:1")
        os.system("tc filter add dev docker0 parent 1:0 protocol ip prio 1 u32 match ip dst "+ target_address +" flowid 1:2")
        sleep(abs(numpy.random.exponential(self._duration_param)))
        os.system("tc filter del dev docker0 parent 1:0 protocol ip prio 1 u32 match ip dst "+ target_address +" flowid 1:2")
        os.system("tc filter add dev docker0 parent 1:0 protocol ip prio 1 u32 match ip dst "+ target_address +" flowid 1:1")
        self._logger.info("Terminated attack on " + target_address)
        
    def _enable_antagonist(self, message):
        self._logger.info("Start antagonist attack")
        containers = self._manager._get_all_containers()
        self._set_packet_loss_attack()
        self._attack = True
        numpy.random.seed(123)
        for container in containers:
            if not self._manager._is_ignored(container.short_id):
                self._logger.debug("Launching attack thread for " + str(container.short_id))
                threading.Thread(target=self._attack_containers, args=(container.short_id,)).start()
                
        return {'command':'ok','address': socket.gethostbyname(socket.gethostname()), 'description': 'Antagonist started'}
    
    def _disable_antagonist(self, message):
        self._attack = False
        self._logger.info("Antagonist attack stopped")
        return {'command':'ok', 'address': socket.gethostbyname(socket.gethostname()), 'description' : 'Antagonist stopped' }
    
    def _conf_antagonist(self, message):
        
        try:
            self._set_balance(message['balance'])
            self._logger.debug("Balance param updated to " + str(message['balance']))
        except KeyError:
            pass
        
        try:
            self._set_heavy(message['heavy'])
            self._logger.debug("Heavy param updated to " + str(message['heavy']))
        except KeyError:
            pass
        
        try:
            self._set_frequency(message['frequency'])
            self._logger.debug("Frequecy param updated to " + str(message['frequency']))
        except KeyError:
            pass

        try:
            self._set_duration(message['duration'])
            self._logger.debug("Duration param updated to " + str(message['duration']))
        except KeyError:
            pass
        self._logger.info("Antagonist configuration changed")
        return {'command':'ok', 'address':socket.gethostbyname(socket.gethostname()), 'description': 'Configuration updated' }
    
    def close_all(self):
        self._logger.info("Closing the antagonist")
        self._attack = False
        self._rabbit.close_all()
     
