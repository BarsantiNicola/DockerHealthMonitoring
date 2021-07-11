from rabbit import rabbit_client
from time import sleep
import coloredlogs
import threading
import logging
import random
import socket
import numpy
import sys
import os


"""
    Class to generate an antagonist used for attack the containers and test the service functionalities. 
    An antagonist will be deployed on each machine to attack the containers maintained by the local docker host
    The antagonist has the following functionalities:
        - perform a shutdown attack on the local docker host' containers
        - perform a packet loss attack on the local docker host' containers
        - perform an update of the configuration used by the attacker
        
    The configuration of an attack is defined by five different parameters:
        - heavy(0-100): defines the probability to perform an attack
        - balance(0-100): defines the probability of perform a shutdown attack(balance) and the probability of
                          perform a packet loss attack(100-balance)
        - loss(0-100): defines the mean value of the packet loss applied to the containers. The value is used as mean
                       of a gaussian distribution
        - duration(>0): defines the mean time in seconds that a packet loss attack is performed. The value is used as mean
                      of an exponential distribution
        - frequency(>0): defines the mean time in seconds between two attacks. The value is used as a mean of an exponential
                         distribution
"""

class antagonist:
    
    def __init__(self, config, manager):
              
        self._manager = manager            # docker manager used to operate on the dockers
        self._configuration = config       # configuration that contains the ip address of the rabbitMQ message  broker
        self._attack = False               # when True is performing an attack. Pass to false will close all the attack threads
        self._rabbit = None                # rabbitMQ client instance
        self._logger = None                # logger instance
        
        self._balance = 50                           # balance between attacks. Default 50% shutdown 50% packet loss
        self._balance_lock = threading.Lock()        # mutual exclusion on balance variable
        self._heavy_rate = 60                        # probability of attack. Default 60%
        self._heavy_rate_lock = threading.Lock()     # mutual exclusion on heavy variable 
        self._pkt_loss_rate = 80                     # mean value of packet loss
        self._pkt_loss_rate_lock = threading.Lock()  # mutual exclusion on packet loss variable
        self._freq_param = 5                         # frequency of attack. Default 5s
        self._freq_param_lock = threading.Lock()     # mutual exclusion on frequency variable
        self._duration_param = 2                     # duration of a packet loss attack. Default 2s
        self._duration_param_lock = threading.Lock() # mutual exclusion on duration variable

        # showed rabbitMQ module interface
        self._interface = {
                'start_antagonist' : self._enable_antagonist,   # start the antagonist attacks
                'stop_antagonist' : self._disable_antagonist,   # stop the antagonist attacks
                'conf_antagonist' : self._conf_antagonist       # change the antagonist parameters
        }
        
        self._initialize_logger()                 # logger initialization
        if self._init_rabbit() is False:          # rabbitMQ client initialization
            raise Exception("Error, unable to connect to the rabbitMQ broker")
        
        self._logger.info("Antagonist ready")
        
    """ configures the logger behaviour """
    def _initialize_logger(self):
        self._logger = logging.getLogger(__name__)
        
        # prevent to allocate more handlers into a previous used logger
        if not self._logger.hasHandlers():
            
            self._logger.setLevel(logging.DEBUG)    
            
            handler = logging.StreamHandler(sys.stdout)
            file_handler = logging.FileHandler('/var/log/health_monitor_antagonist.log')
            formatter = coloredlogs.ColoredFormatter("%(asctime)s %(name)s"
                                                 " %(levelname)s %(message)s",
                                                 "%Y-%m-%d %H:%M:%S")
            handler.setFormatter(formatter)
            file_handler.setFormatter(formatter)
            
            file_handler.setLevel(logging.DEBUG)
            handler.setLevel(logging.INFO)
            
            self._logger.addHandler(handler)
            self._logger.addHandler(file_handler)

      
    """  initializes the rabbitMQ client to be used by the controller class """    
    def _init_rabbit(self) -> bool:
        
        try:
            self._logger.debug("Connecting to the rabbitMQ broker.." + self._configuration['address'])
            # connect the client to the rabbitMQ broker and set the communication interface
            self._logger.debug("Connecting to the rabbitMQ broker..")
            self._rabbit = rabbit_client(self._configuration['address'],'antagonist',self._interface)
            self._logger.info("Antagonist correctly connected to the broker")
            return True
        
        except KeyError:
            self._logger.error('Error, address field not found')
            
        return False 

    
    """ MUTUAL EXCLUSION DATA MANAGEMENT """
    
    """ we have five variables into the antagonist that could be accessed concurrently by different threads and so
        requires mutual exclusion """
    
    """ gets the balance value respecting mutual exclusion """
    def _get_balance(self):
        with self._balance_lock:
            return self._balance
        
    """ sets the balance value respecting mutual exclusion """    
    def _set_balance(self, balance):
        with self._balance_lock:
            self._logger.debug("Balance parameter updated from " + str(self._balance) + " to " + str(balance))
            self._balance = balance

    """ gets the heavy value respecting mutual exclusion """
    def _get_heavy(self):
        with self._heavy_rate_lock:
            return self._heavy_rate
        
    """ sets the heavy value respecting mutual exclusion """    
    def _set_heavy(self, heavy):
        with self._heavy_rate_lock:
            self._logger.debug("Heavy parameter updated from " + str(self._heavy_rate) + " to " + str(heavy))
            self._heavy_rate = heavy
            
    """ gets the packet loss rate value respecting mutual exclusion """
    def _get_packet_loss(self ):
        with self._pkt_loss_rate_lock:
            return self._pkt_loss_rate
        
    """ sets the packet loss rate value respecting mutual exclusion """    
    def _set_packet_loss(self, packet_loss):
        with self._pkt_loss_rate_lock:
            self._logger.debug("Packet loss parameter updated from " + str(self._pkt_loss_rate) + " to " + str(packet_loss))
            self._pkt_loss_rate = packet_loss

    """ gets the frequency value respecting mutual exclusion """
    def _get_frequency(self):
        with self._freq_param_lock:
            return self._freq_param
        
    """ sets the frequency value respecting mutual exclusion """    
    def _set_frequency(self, frequency):
        with self._freq_param_lock:
            self._logger.debug("Frequency parameter updated from " + str(self._freq_param) + " to " + str(frequency))
            self._freq_param = frequency

    """ gets the duration value respecting mutual exclusion """
    def _get_duration(self):
        with self._duration_param_lock:
            return self._duration_param
        
    """ sets the duration value respecting mutual exclusion """    
    def _set_duration(self, duration):
        with self._duration_param_lock:
            self._logger.debug("Duration parameter updated from " + str(self._duration_param) + " to " + str(duration))
            self._duration_param = duration
         
    """ ANTAGONIST ATTACKS """
    
    """ when an attack is performed the antagonist will generate a thread for each possible target. 
    Each thread will attack its own target in a indipendet way"""
    def _attack_containers(self, targetShortID, targetID):

        self._logger.info("Thread " + str(threading.get_ident()) + " for " + str(targetShortID) + " started")

        while self._attack is True:
            try:
                # we apply the attacks only on the not ignored containers
                if self._manager._is_ignored(targetShortID) is False:
                    # heavy defines the probability to perform an attack
                    if random.uniform(0,1)<self._get_heavy()/100:
                        # we evaluate the balance between the attack types
                        if random.uniform(0,1) < self._get_balance()/100:
                            self._logger.debug("Shutdown container " + str(targetShortID))
                            self._manager._shutdown_container(targetShortID)
                        else:
                            self._logger.debug("Packet loss attack on container " + str(targetShortID))
                            self._exec_packet_loss_attack(self._manager._get_ip_addr(targetID))
                            self._logger.debug("Packet loss attack on container " + str(targetShortID) + " completed")
            except:
                self._logger.warning("An exception has occurred during the attack")
            sleep(numpy.random.exponential(self._freq_param)) 
        self._logger.info("Thread " + str(threading.get_ident()) + " for " + str(targetShortID) + " stopped")
            
    """ prepares the channels for generating the packet loss behaviour """
    def _set_packet_loss_attack(self):
        # default channel
        os.system("tc qdisc add dev docker0 root handle 1: prio priomap 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0")
        # channel 1:1 without packetloss
        os.system("tc qdisc add dev docker0 parent 1:1 handle 10: netem")
        # channel 1:2 with packet loss
        os.system("tc qdisc del dev docker0 parent 1:2 handle 11: netem loss " + str(self._get_packet_loss())+"%")
        os.system("tc qdisc add dev docker0 parent 1:2 handle 11: netem loss " + str(self._get_packet_loss())+"%")
        self._logger.info("Setting the tc channels completed")

    """ executes a packet loss attack on the target container """
    def _exec_packet_loss_attack(self, target_address):
        
        if target_address == '':
            return
        self._logger.debug("Starting attack on " + target_address)
        # change the channel for the docker ip to the one with the packet loss
        os.system("tc filter del dev docker0 parent 1:0 protocol ip prio 1 u32 match ip dst "+ target_address +" flowid 1:1")
        os.system("tc filter add dev docker0 parent 1:0 protocol ip prio 1 u32 match ip dst "+ target_address +" flowid 1:2")
        sleep(abs(numpy.random.exponential(self._duration_param))) # wait the configured time
        # change the channel for the docker ip to the one without packet loss
        os.system("tc filter del dev docker0 parent 1:0 protocol ip prio 1 u32 match ip dst "+ target_address +" flowid 1:2")
        os.system("tc filter add dev docker0 parent 1:0 protocol ip prio 1 u32 match ip dst "+ target_address +" flowid 1:1")
        self._logger.debug("Terminated attack on " + target_address)
    
    """ thread for launch an attack to all the containers """
    def _attack_launcher(self):
        self._logger.info("Start antagonist attack")
        containers = self._manager._get_all_containers()
        self._set_packet_loss_attack()   # generating the channel with the current packet loss parameter
        self._attack = True   # enable the attack
        numpy.random.seed(123)   # for testability of the results
        for container in containers:
            if not self._manager._is_ignored(container.short_id):  # attack will be performed only to the not ignored containers
                self._logger.info("Launching attack thread for " + str(container.short_id))
                threading.Thread(target=self._attack_containers, args=(container.short_id, container.id,)).start()
        
        while self._attack:
            pass
    """ COMMUNICATION MANAGEMENT """
    
    """ starts the antagonist attack """
    def _enable_antagonist(self, message):
        if self._attack is False:
            threading.Thread(target=self._attack_launcher).start()
        return {'command':'ok','address': socket.gethostbyname(socket.gethostname()), 'description': 'Antagonist started'}
    
    """ stops the antagonist attack """
    def _disable_antagonist(self, message):
        self._attack = False  # disable the attack(force to close all the threads)
        self._logger.info("Antagonist attack stopped")
        return {'command':'ok', 'address': socket.gethostbyname(socket.gethostname()), 'description' : 'Antagonist stopped' }
    
    """ changes the configuration of the antagonist """
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
    
    """ closes the application """
    def close_all(self):
        self._logger.info("Closing the antagonist")
        self._attack = False
        self._rabbit.close_all()
     
