import socket
import docker
import threading
from icmplib import ping
from time import sleep
from rabbit import rabbit_client
import logging
import coloredlogs
import sys
import json
from antagonist import antagonist

class docker_manager:
    

    def __init__(self):
        self._logger = None
        self._configuration = None
        self._ignore_list = list()
        self._restarted_list = list()
        self._threshold = 80
        self._monitor_log = list()
        self._manager_ip = socket.gethostbyname(socket.gethostname())
        self._docker_env = None
        self._containers_env = None
        self._alive_time = 10
        self._container_time = 2
        self._antagonist = antagonist(self)
        
        self._interface = {
                'container_ignore': self.ignore_container, 
                'container_add': self.add_container, 
                'container_threshold': self.set_threshold, 
                'give_content': self.get_containers_info,
                'start_antagonist' : self._antagonist._enable_antagonist,
                'stop_antagonist' : self._antagonist._disable_antagonist,
                'conf_antagonist' : self._antagonist._conf_antagonist
        }
        
        self._initialize_logger()
        if self._load_conf() is False:
            self._logger.error("Error during the configuration load")
            return
        
        if self._connect_docker() is False:
            self._logger.error("Error during the connection with the docker service")
            return
        
        if self._init_rabbit() is False:
            self._logger.error("Error during the connection with the rabbit broker")
            return
        threading.Thread(target=self._start_manager).start()
        threading.Thread(target=self._heartbeat).start()
        
        self._logger.debug("Health Monitoring System ON")

        
    """ UTILITY FUNCTIONS """
    
    """ load from the file system the configuration file which maintains the rabbitMQ location """    
    def _load_conf(self) -> bool:
        
        self._logger.debug("Starting loading of the configuration")
        try:
            # file is putted inside the same folder of the script
            with open('configuration','r') as reader:
                # the content is organized as a json file
                self._configuration = json.load(reader)
                self._logger.debug("Configuration correctly loaded")
                return True
            
        except ValueError:
            self._logger.error("Error, invalid configuration file")
            return False
        except FileNotFoundError:
            self._logger.error("Error, configuration file not found")
            return False
        
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
            # connect the client to the rabbitMQ broker 
            self._logger.debug("Connecting to the rabbitMQ broker..")
            self._rabbit = rabbit_client(self._configuration['address'],'manager',self._interface)
            self._logger.debug("Correctly connected to the broker")
            return True
        
        except KeyError:
            self._logger.error('Error, address field not found')
            
        return False 

    """ creates a connection to the local docker host to manage the containers """
    def _connect_docker(self) -> bool:
       # try:
            self._docker_env = docker.APIClient(base_url='unix://var/run/docker.sock')
            self._containers_env = docker.from_env() # get Docker Host information
            self._logger.debug("Connected to the local docker service")
            return True
        #except:
         #   self._logger.debug("Unable to connect to the docker service")
          #  return False
    
    """ DOCKER MANAGEMENT """
    
    def _get_all_containers(self) -> list:
        return self._containers_env.containers.list(all=True)
    
    def _execute_monitor(self):

        containers = self._get_all_containers()
        current_log = [] # start a new log
        update = False # clear update flag
        for container in containers: # list all deployed containers  
            if not container.short_id in self._ignore_list: # check containers that are NOT on the ignored list
                if  container.status == "running" :
                    
                    if container.short_id in self._restarted_list:  # a restarted container is now running
                        self._restarted_list.remove(container.short_id)
                        update = True
                        
                    try:
                        ip_ctr = self._docker_env.inspect_container(container.short_id)['NetworkSettings']['Networks']['bridge']['IPAddress'] # get container IP    
                        host = ping(ip_ctr, count=20, interval=0.01, timeout=0.1) # ping the container
                        container_desc = "<"+container.short_id+"> <"+str(container.image)+"> RUNNING"+" ["+ip_ctr + "]"+" [Pkt Loss ="+str(100*(host.packet_loss))+"%] "
                        if host.packet_loss < self._threshold: # check Packet Loss
                            container_desc += "[HMS: ACTIVE]" 
                            
                        else : # Exceeded threshold value
                            try:
                                container.restart()    
                                update = True
                                self._restarted_list.append(container.short_id)
                                container_desc += "[Threshold Exceeded] [HMS: RESTART]"
                            except:
                                self._loggin.warning("Error during the restart of "+ container.short_id)
                                container_desc += "[Threshold Exceeded] [HMS: OFFLINE]"
                    except KeyError:
                        
                        try:
                            container.restart()    
                            update = True
                            self._restarted_list.append(container.short_id)
                            container_desc = "<"+container.short_id+"> <"+str(container.image)+"> RUNNING"+" [Network error] [HMS: RESTART]"
                        except:
                            self._loggin.warning("Error during the restart of "+ container.short_id)
                            container_desc = "<"+container.short_id+"> <"+str(container.image)+"> RUNNING"+" [Network error] [HMS: OFFLINE]"
                
                # container was shut down but not for a restart        
                elif container.status == "exited": 
                    container_desc = "<"+container.short_id+"> <"+str(container.image)+"> EXITED"+" [HMS: RESTART]"
                    if not container.short_id in self._restarted_list:
                        try:
                            container.restart()    
                            update = True
                            self._restarted_list.append(container.short_id)
                        except:
                            self._logger.warning("Error during the restart of "+ container.short_id)
                            
            else:       
                self._logger.debug("Container ignored")
                container_desc = "<"+container.short_id+"> <"+str(container.image)+">"+" [HMS: IGNORED]"

            current_log.append(container_desc) # add the container description to the log
        
        self._logger.debug("Verification of pending updates..")
        # if something is done on the containers
        if update == True:
            self._logger.debug("Pending updates found. Advertising the controller")
            self._monitor_log = current_log
            self._rabbit.send_controller_async(alive=False)  # send an update to the controller
            return
        
        self._logger.debug("Verification of changes into the container list")
        # if the previous container description is different(more/less containers, a restart to run container)
        
        if len(self._monitor_log) != len(current_log):
            self._monitor_log = current_log
            self._rabbit.send_controller_async(alive=False) # send an update to the controller
            return
        
        for prev_container in self._monitor_log:
            internal_update = False
            for curr_container in current_log:
                if curr_container == prev_container:
                    self._logger.debug("Container match. Not to be updated" )
                    internal_update = True
                    pass
            if internal_update is False:
                self._logger.debug("Updates into the container status present")
                self._monitor_log = current_log
                self._rabbit.send_controller_async(alive=False) # send an update to the controller
                return
                
        self._monitor_log = current_log # update the monitor log

    def _start_manager(self):
        n = 0
        while True:
            n+=1
            self._logger.debug("Starting new monitoration of containers monitoring: " + str(n))
            self._execute_monitor()
            sleep(self._container_time)    

    def _heartbeat(self):
        while True:
            self._rabbit.send_controller_async()
            sleep(self._alive_time)
            
    """ COMMUNICATION MANAGEMENT """
    
    def ignore_container(self, message):
        # check if message contains the containerID field
        try:
            container_id = message["containerID"]
        except KeyError:
            self._logger.debug("Error, containerID field needed")
            return {'command': 'error', 'type':'invalid_param','description':'Error, invalid parameters'}
        
        # check if the contaner is already removed
        if container_id in self._ignore_list:
            return {'command': 'error', 'description': 'Container ' + container_id + ' already ignored'}
        
        # check if the container is present on the docker host
        containers = self._get_all_containers()
        for container in containers:
            if container.short_id == container_id: # if docker is present we can disable it from the management
                self._ignore_list.append(container_id)
                return {'command': 'ok', 'description': 'Container ' + container_id + ' removed from the service'} 
            
        return {'command': 'error', 'type':'invalid_param','description':'Error, containerID not present'}
    
        
    def add_container(self, message):
        # check if message contains the containerID field
        try:
            container_id = message["containerID"]
        except KeyError:
            self._logger.debug("Error, containerID field needed")
            return {'command': 'error', 'type':'invalid_param','description':'Error, invalid parameters'}
        
        # check if the contaner is already removed
        if not container_id in self._ignore_list:
            return {'command': 'error', 'description': 'Container ' + container_id + ' not removed from the service'}
        
        # check if the container is present on the docker host
        containers = self._get_all_containers()
        for container in containers:
            if container.short_id == container_id: # if docker is present we can disable it from the management
                self._ignore_list.remove(container_id)
                return {'command': 'ok', 'description': 'Container ' + container_id + ' added to the service management'} 
            
        return {'command': 'error', 'type':'invalid_param','description':'Error, containerID not present'}
    
    def set_threshold(self, message):
        # check if message contains the containerID field
        try:
            threshold = message["threshold"]
        except KeyError:
            self._logger.debug("Error, containerID field needed")
            return {'command': 'error', 'type':'invalid_param','description':'Error, required a threshold field'}

        if threshold > 0 and threshold < 1 :    
            self._threshold = threshold
            self._logger.debug("Set Pkt Loss threshold to ", threshold)
            return {'command': 'ok', 'description': '[' + socket.gethostbyname(socket.gethostname()) +'] Threshold changed to ' + str(threshold)}
        else:
            self._logger.debug("Error, invalid threshold: ", threshold)
            return {'command': 'error', 'type': 'invalid_param', 'description': '[' + socket.gethostbyname(socket.gethostname()) +']Invalid threshold. Threshold must be between 0 and 1'}
        
    def get_containers_info(self, message):
        return {'command': 'ok', 'address': self._manager_ip, 'description': self._monitor_log}
        
docker_manager()



