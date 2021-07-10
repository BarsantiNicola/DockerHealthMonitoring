from antagonist import antagonist
from rabbit import rabbit_client
from icmplib import ping
from time import sleep
import coloredlogs
import threading
import logging
import socket
import docker
import json
import sys

"""
    Class to manage the containers installed into the local docker host. The class will execute periodically 
    a verification to all the containers present locally and not setted as ignored. With the verification the monitor
    identifies if the container is running and in the case the measures the current packet loss of the container. 
    The class has the following functionalities:
        - verifies for each container its status and its current packet loss
        - notifies asynchronously the updates that happens to the containers
        - restart a container when the packet loss is higher than a configured threshold
        - permits to change the threshold parameter
"""

class docker_manager:
    
    def __init__(self):
        
        self._logger = None            # logger for class output
        self._configuration = None     # data obtained from configuration file
        self._docker_env = None        # client for docker interaction
        self._containers_env = None    # client for docker interaction
        self._alive_time = 10          # seconds between two heartbeat update message
        self._container_time = 0.2     # seconds between two containers monitor operations
        self._exit = True              # used to close all the threads used by the application
        self._manager_ip = socket.gethostbyname(socket.gethostname())   # ip address of the local machine
        self._rabbit = None                      # instance of rabbitMQ management class
        
        self._ignore_list = list()               # list of ignored containers
        self._ignore_lock = threading.Lock()     # semaphore for mutual exclusion on ignore_list
        
        self._restarted_list = list()            # list of containers under restart(to prevent chains of restart)
        self._restart_lock = threading.Lock()    # semaphore for mutual exclusion on restart_list
        
        self._threshold = 60                     # packet loss threshold
        self._threshold_lock = threading.Lock()  # semaphore for mutual exclusion on threshold
        
        self._monitor_log = list()               # last obtained description of all the local containers
        self._monitor_lock = threading.Lock()    # semaphore for mutual exclusion on monitor_log
        
        # exposed interface for rabbitMQ modules interaction
        self._interface = {
                'container_ignore': self.ignore_container,     # removes a container from the service management
                'container_add': self.add_container,           # add a container previously ignored to the service management
                'container_threshold': self.set_threshold,     # change the threshold used by the manager
                'give_content': self.get_containers_info       # give back the monitor_log
        }
        
        
        self._initialize_logger()   # initialization of the logger
        
        # loading of the configuration from the file system
        if self._load_conf() is False:
            self._logger.error("Error during the configuration load")
            raise Exception("Error, unable to load the configuration")
        
        # loading the ignored_list
        self._load_ignored()
        self._load_threshold()
        
        # connecting to the docker environment
        if self._connect_docker() is False:
            self._logger.error("Error during the connection with the docker service")
            raise Exception("Error, unable to connect to the docker host")
        
        # initialization of the rabbitMQ clients
        if self._init_rabbit() is False:
            self._logger.error("Error during the connection with the rabbit broker")
            raise Exception("Error, unable to connect to the rabbitMQ broker")
        
        # starting thread for container monitor
        threading.Thread(target=self._start_manager).start()
        
        # starting a thread for heartbeat
        threading.Thread(target=self._heartbeat).start()
        
        self._logger.info("Health Monitoring System ON")
        
        # each manager contains a temporary class for testing the system
        self._antagonist = antagonist(self._configuration, self)
        
    """ UTILITY FUNCTIONS """
        
    """ configures the logger behaviour """
    def _initialize_logger(self):
        self._logger = logging.getLogger(__name__)
        
        # prevent to allocate more handlers into a previous used logger
        if not self._logger.hasHandlers():
            self._logger.setLevel(logging.DEBUG)    
            handler = logging.StreamHandler(sys.stdout)
            file_handler = logging.FileHandler('/var/log/health_monitor_manager.log')
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
            # connect the client to the rabbitMQ broker 
            self._logger.debug("Connecting to the rabbitMQ broker..")
            self._rabbit = rabbit_client(self._configuration['address'],'manager',self._interface)
            self._logger.info("Manager correctly connected to the broker")
            return True
        
        except KeyError:
            self._logger.error('Error, address field not found')
            
        return False 

    
    """ loads from the file system the configuration file which maintains the rabbitMQ location """    
    def _load_conf(self) -> bool:
        
        self._logger.debug("Starting loading of the configuration")
        try:
            # file is putted inside the same folder of the script
            with open('configuration','r') as reader:
                # the content is organized as a json file
                self._configuration = json.load(reader)
                self._logger.info("Configuration correctly loaded")
                return True
            
        except ValueError:
            self._logger.error("Error, invalid configuration file")
            return False
        except FileNotFoundError:
            self._logger.error("Error, configuration file not found")
            return False
        
    """ saves the ignored list to give persistance to the user configuration """
    def _save_ignored(self):
        self._logger.debug("Saving service updates... ")        
        with open('ignored','wb') as writer:
            try:
                # the data is stored as an array of json objects each containing data about a docker manager
                writer.write(bytes(json.dumps(self._ignored_list),'utf-8'))
                self._logger.info('Ignore list correctly saved')
                return True
            
            except ValueError:
                self._logger.error("Error while saving the data. Invalid data structure")
                return False 
    
    """ loads from the file system the containers to be ignored """    
    def _load_ignored(self) -> bool:
        
        self._logger.debug("Starting loading of the ignored list")
        try:
            # file is putted inside the same folder of the script
            with open('ignored','rb') as reader:
                # the content is organized as a json file
                self._ignored_list = json.load(reader)
                self._logger.info("Ignore list correctly loaded")
                return True
            
        except ValueError:
            self._logger.warning("Error, invalid ignored list file. Use empty list")
            self._ignored_list = list()
            return False
        
        except FileNotFoundError:
            self._logger.warning("Error, ignored list file not found. Use empty list")
            self._ignored_list = list()
            return False

    """ saves the threshold to give persistance to the user configuration """        
    def _save_threshold(self):
        self._logger.debug("Saving service updates... ")        
        with open('threshold','wb') as writer:
            try:
                # the data is stored as an array of json objects each containing data about a docker manager
                writer.write(bytes(json.dumps(self._threshold),'utf-8'))
                self._logger.info('Updates correctly saved')
                return True
            
            except ValueError:
                self._logger.error("Error while saving the data. Invalid data structure")
                return False 
    
    """ loads from the file system the configuration file which maintains the rabbitMQ location """     
    def _load_threshold(self) -> bool:
        
        self._logger.debug("Starting loading of the ignored list")
        try:
            # file is putted inside the same folder of the script
            with open('threshold','rb') as reader:
                # the content is organized as a json file
                self._threshold = json.load(reader)
                self._logger.info("Configuration correctly loaded")
                return True
            
        except ValueError:
            self._logger.warning("Error, invalid threshold file. Using default 60")
            return False
        except FileNotFoundError:
            self._logger.warning("Error, threshold file not found. Using default 60")
            return False   
        
    """ creates a connection to the local docker host to manage the containers """
    def _connect_docker(self) -> bool:
       try:
            self._docker_env = docker.APIClient(base_url='unix://var/run/docker.sock')
            self._containers_env = docker.from_env() # get Docker Host information
            self._logger.info("Connected to the local docker service")
            return True
       except:
            self._logger.error("Unable to connect to the docker service")
            return False
                
    """ MUTUAL EXCLUSION DATA MANAGEMENT """
    
    """ we have three variables into the manager that could be accessed cuncurrently by different threads and
        requires mutual exclusion """
        
    """ verifies if a container is excluded from the service management """
    def _is_ignored(self, containerID) -> bool:
        with self._ignore_lock:
            return containerID in self._ignore_list
        
    """ excludes a container from the service management """       
    def _add_ignored(self, containerID):
        if self._is_ignored(containerID) is False:
            with self._ignore_lock:
                self._ignore_list.append(containerID)
                self._logger.info("Added a new container to the ignore list " + str(containerID))
                self._save_ignored()
    
    """ removes a container from the excluded by the service management """
    def _remove_ignored(self, containerID):
        if self._is_ignored(containerID) is True:
            with self._ignore_lock:
                self._ignore_list.remove(containerID)
                self._logger.info("Container " + str(containerID) + " removed from the ignored list")
                self._save_ignored()
            
    """ verifies if a container is previusly restarted from the service management.
        This is to prevent that a service try to start an offline container that is currently under restarting"""       
    def _is_restarted(self, containerID) -> bool:
        with self._restart_lock:
            return containerID in self._restarted_list
        
    """ sets a container in restarting mode(prevents actions on the container)"""    
    def _add_restarted(self, containerID) -> bool:
        if self._is_restarted(containerID) is False:
            with self._restart_lock:
                self._restarted_list.append(containerID)
                self._logger.debug("Container " + str(containerID) + " added to the restart list")
            return True
        else:
            self._logger.warning("Container " + str(containerID) + " already added to the restart list")
            return False
    
    """ undos the restart operation by resetting the container into the normal mode""" 
    def _remove_restarted(self, containerID):
        if self._is_restarted(containerID) is True:
            with self._restart_lock:
                self._logger.debug("Container " + str(containerID) + " removed from the restart list")
                self._restarted_list.remove(containerID)
    
    """ gives back the threshold used by the manager respecting the mutual exclusion on the variable """
    def _get_threshold(self):
        with self._threshold_lock:
            return self._threshold
    
    """ changes the threshold used by the manager respecting the mutual exclusion on the variable """
    def _change_threshold(self, threshold):
        with self._threshold_lock:
            self._threshold = threshold
            self._logger.debug("Threshold updated to " + str(threshold))
            self._save_threshold()
            
    """ DOCKER MANAGEMENT """
    
    """ returns the containers present into the local docker host"""
    def _get_all_containers(self) -> list:
        return self._containers_env.containers.list(all=True)
    
    """ used by the antagonist to shutdown a container"""
    def _shutdown_container(self,targetID) -> bool:
        try:
            containers = self._get_all_containers()
            for container in containers:
                if container.short_id == targetID:
                    container.stop()
                    return True
        except:
            pass
        return False
    
    """ used by the antagonist the get the ip address of a container """
    def _get_ip_addr(self, targetID):
        try:
            return self._docker_env.inspect_container(targetID)['NetworkSettings']['Networks']['bridge']['IPAddress']
        except:
            return ''
              
    """ Periodic containers analysis """
    def _execute_monitor(self):
        
        # get all containers
        containers = self._get_all_containers()
        current_log = {} # start a new log
        container_desc = {}
        update = False # clear update flag
        
        self._logger.debug("Starting analysis of the local docker host containers status""")
        # scroll all the present containers
        for container in containers:
            
            if not self._is_ignored(container.short_id): # checks only the containers that are NOT on the ignored list
                
                if container.status == "running" :  # container is RUNNING
                    # a restarted container is now running so we can remove from the restarted_list 
                    if self._is_restarted(container.short_id):  
                        self._logger.debug("Container " + str(container.short_id) + " change state from update to running")
                        self._remove_restarted(container.short_id)
                        update = True    # a change into the containers status has occurred
                        
                    try:
                        # getting the ip address of the container
                        ip_ctr = self._docker_env.inspect_container(container.short_id)['NetworkSettings']['Networks']['bridge']['IPAddress'] # get container IP    
                        self._logger.debug("Evaluating packet loss for container " + str(container.short_id))
                        
                        # evaluating the packet loss
                        host = ping(ip_ctr, count=20, interval=0.01, timeout=0.1) # ping the container
                        self._logger.debug("Measured packet loss for container " + str(container.short_id)+": " +str(100*(host.packet_loss))+'%')
                        
                        # generation of the description file
                        container_desc = {
                                'address': ip_ctr, 
                                'packet_loss': str(100*(host.packet_loss))+'%', 
                                'container_state':'running',
                                'service_state':'enable'
                        }
                        
                        # 
                        if host.packet_loss > self._get_threshold()/100: # if packet loss exceeds the threshold we restart the container
                            
                            self._logger.info("Container " + str(container.short_id) + " packet loss too high. Restart executed")
                            try:
                                container_desc['details'] = 'Packet loss threshold exceeded, container restarted'
                                if self._add_restarted(container.short_id) is True:
                                    container.restart() 
                                    update = True
                                    container_desc['container_state'] ='restart'
                                else: 
                                    self._logger.warning("Container " + str(container.short_id) + " already restarted. Abort operation")
                                    container_desc['container_state'] ='offline'
                                    container_desc['details'] = 'Container offline. Trying to restart it'
                            except:
                                self._logger.warning("Error during the restart of "+ container.short_id)
                                container_desc['container_state'] ='offline'
                                container_desc['details'] = 'Container offline. Trying to restart it'
                                
                    except KeyError:           
                            container_desc = {'address': 'unknown', 'packet_loss': 'unknown', 'container_state':'running', 'service_state':'enable', 'details': 'Network error occurred during the management'}                
                # container was shut down but not for a restart        
                elif container.status == "exited": 
                    container_desc = {'container_state':'exited', 'service_state':'enable', 'details': 'Container offline. Trying to restart it'}                
                    if not self._is_restarted(container.short_id):
                        try:
                            container.start()    
                            update = True
                            self._add_restarted(container.short_id)
                        except:
                            self._logger.warning("Error during the restart of "+ container.short_id)
                            
            else:       
                self._logger.debug("Container ignored")
                container_desc = { 'container_state':'disabled','details': 'Container not managed by the service'}     

            current_log[container.short_id] = container_desc # add the container description to the log
        
        self._logger.debug("Verification of pending updates..")
        
        # if something is done on the containers
        if update is True:
            self._logger.debug("Pending updates found. Advertising the controller")
            with self._monitor_lock:
                self._monitor_log = current_log
            self._rabbit.send_controller_async(alive=False)  # send an update to the controller
            return
        
        with self._monitor_lock:
            prev_log = self._monitor_log
            
        # verification that the previous container description is different(more/less containers) 
        
        if len(prev_log) != len(current_log):
            self._logger.debug("Pending updates found. Advertising the controller")
            with self._monitor_lock:
                self._monitor_log = current_log
            self._rabbit.send_controller_async(alive=False) # send an update to the controller
            return
        
        # verification that something is changed from the previous containers description
        if json.dumps(current_log) != json.dumps(prev_log):
            self._logger.debug("Pending updates found. Advertising the controller")
            with self._monitor_lock:
                self._monitor_log = current_log
            self._rabbit.send_controller_async(alive=False) # send an update to the controller
            return
        
    """ SERVICE THREADS """
    
    """ executes periodically the verification of the containers """
    def _start_manager(self):
        while self._exit:
            self._execute_monitor()
            sleep(self._container_time)    

    """ executes periodically an heartbeat message to the controller """
    def _heartbeat(self):
        while True:
            self._rabbit.send_controller_async()
            sleep(self._alive_time)
            
    """ COMMUNICATION MANAGEMENT """
    
    """ excludes a container from the service management. The message must contains a containerID field """
    def ignore_container(self, message):
        # check if message contains the containerID field
        try:
            container_id = message["containerID"]
        except KeyError:
            self._logger.debug("Error, containerID field needed")
            return {'command': 'error', 'type':'INVALID_PARAM','description':'Error, invalid parameters'}
        
        # check if the contaner is already removed
        if self._is_ignored(container_id):
            return {'command': 'error', 'type': 'INVALID_REQUEST', 'description': 'Container ' + container_id + ' already ignored'}
        
        # check if the container is present on the docker host
        containers = self._get_all_containers()
        for container in containers:
            if container.short_id == container_id: # if docker is present we can disable it from the management
                self._add_ignored(container_id)
                self._logger.debug("IGNORED: " + json.dumps(self._ignore_list))
                return {'command': 'ok', 'description': 'Container ' + container_id + ' removed from the service'} 
            
        return {'command': 'error', 'type':'invalid_param','description':'Error, containerID not present'}
    
    
    """ enable a previously excluded container from the service management. The message must contains a containerID field """    
    def add_container(self, message):
        # check if message contains the containerID field
        try:
            container_id = message["containerID"]
        except KeyError:
            self._logger.debug("Error, containerID field needed")
            return {'command': 'error', 'type':'invalid_param','description':'Error, invalid parameters'}
        
        # check if the contaner is already removed
        if not self._is_ignored(container_id):
            return {'command': 'error', 'type': 'INVALID_REQUEST', 'description': 'Container ' + container_id + ' not removed from the service'}
        
        # check if the container is present on the docker host
        containers = self._get_all_containers()
        for container in containers:
            if container.short_id == container_id: # if docker is present we can disable it from the management
                self._remove_ignored(container_id)
                return {'command': 'ok', 'description': 'Container ' + container_id + ' added to the service management'} 
            
        return {'command': 'error', 'type':'INVALID_PARAM','description':'Error, containerID not present'}
    
    """ changes the threshold setted into the manager. The message must contains a threshold field """
    def set_threshold(self, message):
        # check if message contains the containerID field
        try:
            threshold = message["threshold"]
        except KeyError:
            self._logger.debug("Error, threshold field needed")
            return {'command': 'error', 'type':'invalid_param','description':'Error, required a threshold field'}

        if threshold > -1 and threshold < 101 : 
            with self._threshold_lock:
                self._threshold = threshold
            self._logger.debug("Set Pkt Loss threshold to ", threshold)
            return {'command': 'ok', 'address': socket.gethostbyname(socket.gethostname()), 'description': 'Threshold changed to ' + str(threshold)}
        else:
            self._logger.debug("Error, invalid threshold: ", threshold)
            return {'command': 'error', 'type': 'invalid_param', 'address': socket.gethostbyname(socket.gethostname()),  'description': 'Invalid threshold. Threshold must be between 0 and 100'}
    
    """ gives back the containers list """
    def get_containers_info(self, message):
        with self._monitor_lock:
            return {'command': 'ok', 'address': self._manager_ip, 'content': self._monitor_log}
     
    """ closes all the threads and system functionalities """
    def close_all(self):
        self._exit = False
        self._antagonist.close_all()
        self._rabbit.close_all()


""" SERVICE """

manager = docker_manager()
try:
    while True:
        pass
except:
    manager.close_all()