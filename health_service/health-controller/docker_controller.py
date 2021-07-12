from rabbit import rabbit_client
import json
import os
import paramiko
import threading
import logging
import coloredlogs
import sys
import time
from datetime import datetime
from datetime import timedelta
import socket
from time import sleep
from pandas import DataFrame

"""

    Class to generate a controller for the docker health monitor service. The controller is the element in contact with both
    the users(by the rest interface) and the managers(one per docker host) hiding the complexity of the service presenting 
    one endpoint which will handle the requests and performs the required operations giving back the results.
    
    The controller has the following duties:
        - install/uninstall managers into remote machines
        - send request to all the managers in a multicast or unicast way
        - aggregate the results for presenting them to the users
        - send request too al the antagonists in a multicast or unicast way
        - maintain and manage the containers information given by the managers using an asynchronous communication

    The last point of its functionalities is important. The service will work with lots of machines which requires some
    time to gives theirs results. To improve the performance of the service where is possible(the management of the containers
    information) is important to implement an asynchronous management. The module will maintains locally a list of all
    the containers in all the machines, everytime a manager has an update it will send a flag to controller to inform it 
    that it has to request its information. Then the module basing on an aggregation time periodically will request the 
    pending updates. In this way with a certain availability which strict depends on the aggregation time a request to the 
    containers information could be resolved without any interaction with the managers
    
"""
        
class controller:
     
    def __init__(self):
        self._aggregation_time = 5            # time interval for the pending updates elaboration
        self._enable_test = False             # enable the collect of data for testing purpouse
        self._configuration = None            # configuration getted from the configuration file[contains rabbitMQ address]
        self._rabbit = None                   # instance of rabbitMQ management class
        self._dockers = []                    # maintains all the information about registered dockers
        self._containers_data = []            # maintains all the containers information given from the managers
        self._docker_lock = threading.Lock()  # lock for mutual exclusion on self.dockers operations
        self._info_lock = threading.Lock()    # lock for mutual exclusion on self.containers_data operations
        self._logger = None                   # class logger
        self._exit = True                     # used to close all the threads used by the application
        
        # test variables
        self._collect_data = False   # triggers the interface to collect data from the operations
        self._availability = DataFrame(columns=['availability'])    # dataframe for availability measurements
        self._bandwidth = DataFrame(columns=['threshold'])          # dataframe for bandwidth measurements
        self._data_lock = threading.Lock()  # lock for mutual exclusion of dataframes

        self._len_aggregation_counter = 0      # counter for bandwidth measurements
        self._counter_lock = threading.Lock()  # lock for mutual exclusion on len_aggregation_counter
        
        # interface shared with outside clients by rabbitMQ
        self._interface = {
           'live' : self._set_heartbeat,
           'update' : self._set_container_status_update_present,

           'add_host' : self._load_docker_manager,
           'remove_host' : self._remove_docker_manager,
           
           'get_all_containers' : self._get_all_managers_containers_content,
           'get_container' : self._get_container_content,
           'get_host_containers' : self._get_manager_containers_content,
           
           'add_container' : self.add_container,  
           'remove_container' : self.remove_container,
           
           'change_all_threshold' : self.change_all_threshold,
           'change_threshold' : self.change_threshold,

           'add_antagonists' : self.add_antagonists,
           'add_host_antagonist' : self.add_host_antagonist,
           'change_antagonists_conf' : self.change_antagonists_config,
           'change_host_antagonist_conf' : self.change_host_antagonist_config,
           'remove_antagonists' : self.remove_antagonists,
           'remove_host_antagonist' : self.remove_host_antagonist , 
           
           'uninstall': self._uninstall
        }
        
        self._initialize_logger() # initialization of the logger
        
        if self._load_conf() is False:   # load the configuration which contains the IP address of rabbitMQ
            self._logger.error("Error during the configuration load")
            raise Exception("Error, unable to load the configuration")
        
        # we don't have mutual exclusion on load_data so is important to be used before init_rabbit()
        self._load_data()     # load the stored data about the connected dockerManagers
        
        if self._init_rabbit() is False: # initialization of rabbitMQ, creation of the channels to receive and send messages
            self._logger.error("Error during the connection with the rabbit broker")
            raise Exception("Error, unable to connect to the rabbitMQ broker")
        
        # starting initial update of containers
        
        self._logger.debug("Started periodic service of pending management")
        threading.Thread(target=self._pending_manager).start()
        self._logger.debug("Service started")
        self._logger.debug("Started periodic service of heartbeat management")
        threading.Thread(target=self._heartbeat_manager).start()
        self._logger.debug("Service started")
        
        self._logger.info("Controller initialization completed at " + socket.gethostbyname(socket.gethostname()))    
  
    """ UTILITY FUNCTIONS """
    
    """ configures the logger behaviour """
    def _initialize_logger(self):
        self._logger = logging.getLogger(__name__)
        
        # prevent to allocate more handlers into a previous used logger
        if not self._logger.hasHandlers():
            self._logger.setLevel(logging.DEBUG)
            handler = logging.StreamHandler(sys.stdout)
            file_handler = logging.FileHandler('/var/log/health_monitor_controller.log')
            formatter = coloredlogs.ColoredFormatter("%(asctime)s %(name)s"
                                                 " %(levelname)s %(message)s",
                                                 "%Y-%m-%d %H:%M:%S")
            handler.setFormatter(formatter)
            file_handler.setFormatter(formatter)
            
            file_handler.setLevel(logging.DEBUG)
            handler.setLevel(logging.INFO)
            
            self._logger.addHandler(handler)
            self._logger.addHandler(file_handler)
       
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
        
    """  initializes the rabbitMQ client to be used by the controller class """    
    def _init_rabbit(self) -> bool:
        try:
            # connect the client to the rabbitMQ broker 
            self._logger.debug("Connecting to the rabbitMQ broker..")
            self._rabbit = rabbit_client(self._configuration['address'],'controller',self._interface)
            self._logger.debug("Correctly connected to the broker")
            return True
        
        except KeyError:
            self._logger.error('Error, address field not found')
            
        return False 
     
    """ secure way to close the service, closes all the threads and the loops """
    def close_all(self):
        self._exit = False
        self._rabbit.close_all()
        
    
    """ DOCKER MANAGERS MANAGEMENT """
            
    """ [ DATA STORING ] """
    
    """ loads from the file system the configured docker managers. Used in case of service restart """
    def _load_data(self):
        try:
            self._logger.debug("Loading connected docker manager data from the file system... ")
            with open('data','rb') as reader:
                # data is stored as an array of json objects each containing data about a docker manager
                self._dockers = json.load(reader)
                
            self._logger.debug("Data correctly loaded " + str(len(self._dockers)) + " docker manager/s found")
            self._logger.debug("Building the containers data table..")  
            # generating a basic containers structure for each docker manager. The status is setted
            # to wait_update because immidiately the system will spread a multicast request to all the managers
            for docker in self._dockers:
                self._containers_data.append({
                        'address' : docker['address'],    # to identify the manager which the data are referring to
                        'content' : 'NO CONTENT AVAILABLE',     
                        'manager_status' : 'offline',    # we don't know yet if the manager is correctly allocated
                        'last_alive' : datetime.now() + timedelta(minutes=5) })   # to know soon or later if the manager is active
            self._logger.info("Containers data table build")
            
        except FileNotFoundError:
            self._logger.warning("Data stored not found")
        except ValueError:
            self._logger.error("Error, invalid stored data. Data not loaded, service re-initialized")

    """ stores the configured docker managers permanently in case of service shutdown """        
    def _save_data(self) -> bool:
        
        self._logger.debug("Saving service updates... ")        
        with open('data','wb') as writer:
            try:
                # the data is stored as an array of json objects each containing data about a docker manager
                writer.write(bytes(json.dumps(self._dockers),'utf-8'))
                self._logger.debug('Updates correctly saved')
                return True
            
            except ValueError:
                self._logger.error("Error while saving the data. Invalid data structure")
                return False 
    
    """ verifies the presence of a docker manager identified by its IP address """        
    def _verify_docker_presence(self, address) -> bool:
        
        with self._docker_lock: # we need to garantee mutual exclusion
            self._logger.debug("Starting verification of docker manager presence for host: " + address)    
            for docker in self._dockers:
                if docker['address'] == address: # address is used as an identificator of a docker manager
                    self._logger.debug("Docker manager found")  
                    return True
                
        self._logger.debug("Docker manager not found")          
        return False

    """ removes a docker manager instance from the docker manager container """
    def _remove_docker(self, address):
        
        with self._docker_lock: # we need to garantee the mutual exclusion
            self._logger.debug("Searching the docker manager instance: " + address + " for docker manager removal")  
            for docker in self._dockers:
                if docker['address'] == address: # address is used as an identificator of a docker manager
                    self._logger.debug("Docker manager found")  
                    self._dockers.remove(docker)
                    self._logger.info("Docker manager removed")  
                    # in order to reduce the time in mutual exclusion and simplify the code the saving 
                    # of the updates is done on the caller function

        with self._info_lock:
            for docker in self._containers_data:
               if docker['address'] == address:
                   self._containers_data.remove(docker)
       

        
    """ used for the docker manager removal, get the password of the host from the ip address of the docker manager """
    def _get_docker_password(self, address) -> str:
        
        with self._docker_lock: # we need to garantee mutual exclusion
            self._logger.debug("Searching the docker manager instance: " + address + " for password retrival") 
            for docker in self._dockers:
                if docker['address'] == address: # address is used as an identificator of a docker manager
                    self._logger.debug("Docker manager found") 
                    return docker['password']
                
        self._logger.debug("Docker manager password not found")         
        return '' 
    
    """ [ MAIN FUNCTIONALITIES ] """
    
    """ generates the configuration file for the managers installation. The file will contain the address of the rabbitMQ broker """
    def _generate_configuration(self, address) -> None:
        # configuration file used by managers will be in the components folder
        self._logger.debug("Generation of configuration file..")
        with open('../health-manager/configuration','w') as writer:
            writer.write(json.dumps({'address': address}))
        self._logger.debug("Generation of configuration file completed")
        
    """ loads the docker manager and the antagonist into an host identified by its address and root password """
    def _load_docker_manager(self, message) -> dict:
        
        try:
            message['address']
            message['password']
        except:
            self._logger.error("Error, the function requires an address and password fields")
            return { 'command':'error', 'type': 'missing_par', 'description': 'Missing parameter address or password'}
        
        # verification that the docker manager isn't registered yet
        if self._verify_docker_presence(message['address']) is False:   
            try:
                self._logger.debug("Starting secure channel generation..")
                # generation of the configuration file the rabbitMQ broker ip address
                self._generate_configuration(socket.gethostbyname(socket.gethostname()))
                # generation of an ssh connection with the host
                ssh = paramiko.SSHClient() 
                ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                ssh.load_host_keys(os.path.expanduser(os.path.join("~", ".ssh", "known_hosts")))
                ssh.connect(message['address'], username='root', password=message['password'])
                self._logger.debug("Secure channel created")
                # generation of a secure ftp session for the data transfer
                self._logger.debug("Generation of a secure ftp communication over the ssh connection")
                sftp = ssh.open_sftp()
                self._logger.debug("Generation of sftp service completed. Controller ready to send data")
                try:
                    self._logger.debug("Starting transfer of needed data..")
                    # we have to manually generate the folder
                    sftp.mkdir('/root/health_manager')
                    
                except OSError:
                    self._logger.warning('Folder already present') # if the folder is already present. 
                self._logger.debug("Folder created. Starting data transfer")
                # inside the folder we put all the files present into the components subdirectory
                for item in os.listdir('/root/health_service/health-manager'):
                    if not os.path.isdir(item):
                        self._logger.debug("Starting transfer: /root/health_service/health-manager/"+item )
                        sftp.put('/root/health_service/health-manager/'+item,'/root/health_manager/'+item)
                        self._logger.debug("Transfered: /root/health_service/health-manager/"+item )

                # the manager/antagonist will run as a service on the remove machine. We need to put its definition
                sftp.put('../docker-health-monitor.service','/etc/systemd/system/docker-health-monitor.service')
                self._logger.debug("Data completely transfered to the machine " + message['address'])
                sftp.close()
                self._logger.debug("Sftp channel closed")
                self._logger.debug("Execution of final operation on the remove host..")
                # the service definition must be set as executable
                ssh.exec_command('apt-get install -y python3.7 pip3')
                ssh.exec_command('update-alternatives  --set python /usr/bin/python3.7')
                ssh.exec_command('pip3 install --no-cache-dir -r /root/health_manager/requirements.txt')
                time.sleep(5)
                ssh.exec_command('chmod 0777 /etc/systemd/system/docker-health-monitor.service')
                ssh.exec_command('systemctl daemon-reload')
                ssh.exec_command('systemctl enable docker-health-monitor.service')
                ssh.exec_command('systemctl start docker-health-monitor.service')
                ssh.close()
                self._logger.debug("Remote host configuration completed. Secure channel closed")
                
                # inserting the new docker inside its archive
                self._logger.debug("Updating managers information..")
                with self._docker_lock:
                    self._dockers.append(
                        {
                                'address': message['address'],
                                'password': message['password']
                        })
                self._logger.debug("Managers information upated")
                
                self._logger.debug("Building container information for the new manager")    
                # building a placeholder for the docker manager containers
                with self._info_lock: # we need to garantee mutual exclusion
                    self._containers_data.append({
                        'address' : message['address'],    # to identify the manager which the data are referring to
                        'content' : 'NO CONTENT AVAILABLE',     
                        'manager_status' : 'offline',    # we don't know yet if the manager is correctly running
                        'last_alive' : datetime.now() + timedelta(minutes=5) })   # to know soon or later if the manager is active
                self._logger.debug("Controller has complete the update")
                if self._save_data() is True:
                    self._logger.info("New docker host added to the service: " + message['address'])
                    return { 'command':'ok', 'description': 'Docker host added to the service'}
                else:
                    self._logger.error("New docker host added to the service: " + message['address'] + " but unable to save it")
                    return { 'command':'ok', 'description': 'Docker host added to the service but the service was not able to save the update'}
            except:
                self._logger.error('Error during the machine connection. Abort operation')
                return { 'command':'error', 'type': 'connection_error', 'description': 'An error has occured while contacting the destination'}

        return { 'command':'error', 'type': 'invalid_op', 'description': 'Manager already registered into the service'}
    

    """ removes a docker manager previusly registered inside the controller """     
    def _remove_docker_manager(self, message) -> dict:
        
        try:
            message['address']
        except KeyError:
            self._logger.error("Error, the function requires an address field")
            return { 'command':'error', 'type': 'missing_par', 'description': 'Missing parameter address or password'}
        # verification of docker manager presence
        if self._verify_docker_presence(message['address']) is True: 
            try:
                # generation of a secure channel
                self._logger.debug("Starting a secure channel generation to " + message['address'])
                ssh = paramiko.SSHClient() 
                ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                ssh.load_host_keys(os.path.expanduser(os.path.join("~", ".ssh", "known_hosts")))
                ssh.connect(message['address'], username='root', password=self._get_docker_password(message['address']))
                self._logger.debug("Secure channel created")
                # generation of a secure ftp session for the data transfer
                self._logger.debug("Manager service stopped")
                
                # removal of all the manager data
                ssh.exec_command('systemctl disable docker-health-monitor')
                ssh.exec_command('systemctl stop docker-health-monitor')
                ssh.exec_command('rm /etc/systemd/system/docker-health-monitor.service')
                ssh.exec_command('systemctl daemon-reload')
                ssh.exec_command('rm -R /root/health_manager')
                ssh.exec_command('rm -R /var/log/health_*.log')
                ssh.exec_command('rm -R /var/log/rabbit_*.log')
                ssh.close()
                
                self._logger.info("Data completely removed from the machine " + message['address'] + ". Secure channel closed")
                
                # removal of the manager information from the controller
                self._remove_docker(message['address'])
                # store permanently of the update
                if self._save_data() is True:
                    return { 'command':'ok', 'description': 'Host removed from the service'}
                else:
                    return { 'command': 'error', 'description': 'Error, host connected but an error has occurred during the saving of the updates. A shutdown will delete your operations'}
            except:
                self._logger.error('Error during the removal of the manager service')
        
        # docker not present into the service
        return { 'command':'error', 'type': 'invalid_op', 'description': 'The given host is not registered into the service'}
        
    """ CONTAINERS INFORMATION MANAGEMENT """
    
    """ [ DATA STORING ] """
    
    """ gives the container status. Possible statuses: offline, pending_update, wait_update, updated """
    def _get_container_status(self, address) -> str:
        
        with self._info_lock: # we need to garantee mutual exclusion
            self._logger.debug("Searching the container information for " + address)
            for docker in self._containers_data:
                if docker['address'] == address:
                    self._logger.debug("Container found")
                    return docker['manager_status']
                
        self._logger.debug("Container not found")        
        return ''
    
    """ sets the container status to update_present. The flag means that an update is available into the manager.
        If the controller is still waiting an update from the manager the flag isn't notified """
    def _set_container_status_update_present(self, message) -> bool:
        try:
            message['address']
        except KeyError:
            self._logger.error("Error, all the update messages must contain 'address' field")
            return False
        
        with self._info_lock: # we need to garantee mutual exclusion
            self._logger.debug("Searching the container information for " + message['address'])
            for docker in self._containers_data:
                if docker['address'] == message['address']:
                    self._logger.debug("Container found")
                    if docker['manager_status'] != 'wait_update': # if controller is already waiting the update no change needed
                        docker['manager_status'] = 'update_present'
                        docker['last_alive'] = datetime.now() + timedelta(minutes=5)
                        self._logger.info("Container " + message['address'] + " status set to 'update_present'")
                        return True
                    self._logger.debug("Container " + message['address'] + " already waiting the update. Operation aborted")
                    return False
        
        self._logger.debug("Container not found")          
        return False

    """ sets the container status to offline. The flag means that the manager isn't reachable """
    def _set_container_status_offline(self, address) -> bool:
        with self._info_lock: # we need to garantee mutual exclusion
            self._logger.debug("Searching the container information for " + address)
            for docker in self._containers_data:
                if docker['address'] == address:
                    self._logger.info("Container " + address + " found. Status set to 'offline'")
                    docker['manager_status'] = 'offline'
                    return True 
        self._logger.debug("Container not found")          
        return False
            
    """ sets the container content. The content is the list of the containers with their status"""
    def _set_container_content(self, address, content) ->bool:
        with self._info_lock: # we need to garantee mutual exclusion
            self._logger.debug("Searching the container information for " + address)
            for docker in self._containers_data:
                if docker['address'] == address:
                    docker['content'] = content
                    docker['last_alive'] = datetime.now() + timedelta(minutes=5)
                    docker['manager_status'] = 'updated'
                    self._logger.debug("Container found")
                    return True
        
        self._logger.debug("Container not found")
        return False  

    """ sets the last received heartbeat for the manager activity management """
    def _set_heartbeat(self, message) -> bool:
        
        with self._info_lock:
            try:
                self._logger.debug("Searching manager of " + message['address'] +" for heartbeat update")
                for docker in self._containers_data:
                    if docker['address'] == message['address']:
                        self._logger.debug("Container found")
                        docker['last_alive'] = datetime.now() + timedelta(minutes=5)
                        if docker['manager_status'] == 'offline':
                            docker['manager_status'] = 'update_present'
                            self._logger.debug("Changed manager status from offline to update_present")
                        return True
            except KeyError:
                self._logger.error("Error, alive messages must contain 'address' field")
                return False
            
        self._logger.debug("Container not found")
        return False
           
    """ [ MAIN FUNCTIONALITIES ] """

    """ thread for periodic evaluation of pending updates """
    def _pending_manager(self) -> None:
        while self._exit: # used to close all the threads when needed
            self._logger.debug("Executing pending updates verification")
            docker_request = list() # we collect separately the request to release quickly the mutual exclusion
            with self._info_lock:
                for docker in self._containers_data:
                    if docker['manager_status'] == 'update_present':
                        docker_request.append(docker['address'])
            
            # for each docker we control if an update flag is present
            for docker in docker_request:
                self._logger.debug("Found a pending update. Start synchronization for manager at " + docker)
                with self._counter_lock: # used for testing purpouse(measure the bandwidth)
                    self._len_aggregation_counter +=45 # 45 is more or less the size of a give_content request
                result = self._rabbit.send_manager_unicast({
                            "command" : "give_content"
                }, docker)
                with self._counter_lock: # used for testing purpouse(measure the bandwidth)
                    self._len_aggregation_counter += len( json.dumps(result))
                
                # set the update and removes the update_present flag
                try:
                    self._set_container_content(docker, result['content'])
                except:
                    self._logger.warning("Empty updated. Undo operation")
            # operation repeated periodicly after _aggregation time
            time.sleep(self._aggregation_time)
        self._logger.debug("Closing pending manager thread")   
        
    """ thread for verification of heartbeat expiration on docker host(last_alive timestamp expired) """
    def _heartbeat_manager(self) -> None:
        while self._exit:
            self._logger.debug("Executing hearbeat verification")
            with self._info_lock:
                for docker in self._containers_data:
                    if docker['last_alive'] < datetime.now():
                        docker['manager_status'] = 'offline'
            
            time.sleep(60)
        self._logger.debug("Closing heartbeat thread")
            
    """ REST INTERFACE COMMUNICATION MANAGEMENT """

    """ TO MANAGER """

    """ gets the content for a specific docker manager container identified by its address and containerID """
    def _get_manager_container_content(self, message ) -> dict:
        
        # verification of the presence of the needed message fields
        try:
            message['address']
            message['containerID']
        except KeyError:
            self._logger.error("Error, the function requires an address field")
            return { 'command':'error', 'type': 'missing_par', 'description': 'Missing parameter address or containerID'}


        with self._info_lock: # we need to garantee mutual exclusion
            self._logger.debug( "Searching the content for manager " + message['address'])
            dock = None
            for docker in self._containers_data:
                if docker['address'] == message['address']:
                    self._logger.debug( "Container found")
                    dock = docker
                    
        if dock is None: 
            self._logger.warning("Manager not found. Not registered into the controller")
            return { 'command':'error', 'type': 'invalid_op', 'description': 'Selected host is not present into the service'}
                
        if dock['manager_status'] == 'update_present':
            self._logger.debug( "Status of the manager: update_present. Sending a content request")
            result = self._rabbit.send_manager_unicast(json.dumps({
                    "command" : "give_content",
                    'address' : dock['address']
            }), dock['address'])
            
            try:
                if result['command'] == 'error' and result['type'] == 'unreachable':
                    self._logger.warning("Error, the manager isn't reachable")
                    self._set_container_status_offline(message['address'])
                else:
                    self._logger.debug("Updating the information of manager."+message['address'])
                    self._set_container_content(message['address'], result['content'])
                    
            except KeyError:
                self._logger.error("An error has occured. Missing mandatory fields")
                return { 'command':'error', 'type': 'missing_par', 'description': 'Internal server error'}
                
        with self._info_lock: # we need to garantee mutual exclusion
            self._logger.debug( "Searching the content for manager " + message['address'])
            dock = None
            for docker in self._containers_data:
                if docker['address'] == message['address']:
                    self._logger.debug( "Container found")
                    dock = docker.copy()
                    
        if dock is None: 
            self._logger.warning("Manager not found. Not registered into the controller")
            return { 'command':'error', 'type': 'invalid_op', 'description': 'Selected host is not present into the service'}
    
        self._logger.debug( "Information ready. Generating the result")
        return {'command' : 'ok', 'description': dock}  # to be changed with container searching
    
    """ gets the content for a specific docker manager identified by its address [GET /containers/IP_ADDRESS]"""
    def _get_manager_containers_content(self, message ) -> dict:
        
        # verification of the presence of the needed message fields
        try:
            message['address']
        except KeyError:
            self._logger.error("Error, the function requires an address field")
            return { 'command':'error', 'type': 'missing_par', 'description': 'Missing parameter address'}

            
        with self._info_lock: # we need to garantee mutual exclusion
            self._logger.debug( "Searching the content for manager " + message['address'])
            dock = None
            for docker in self._containers_data:
                if docker['address'] == message['address']:
                    self._logger.debug( "Container found")
                    dock = docker
                    
        if dock is None: 
            self._logger.warning("Manager not found. Not registered into the controller")
            return { 'command':'error', 'type': 'invalid_op', 'description': 'Selected host is not present into the service'}
                
        if dock['manager_status'] == 'update_present':
            self._logger.debug( "Status of the manager: update_present. Sending a content request")
            result = self._rabbit.send_manager_unicast({
                    "command" : "give_content"
            }, dock['address'])
            
            try:
                if (result['command'] == 'error') and (result['type'] == 'unreachable'):
                    self._logger.warning("Error, the manager isn't reachable")
                    self._set_container_status_offline(message['address'])
                else:
                    self._logger.debug("Updating the information of manager."+message['address'])
                    self._set_container_content(message['address'], result['content'])
                    
            except KeyError:
                self._logger.error("An error has occured. Missing mandatory fields")
                return { 'command':'error', 'type': 'missing_par', 'description': 'Internal server error'}
        
        self._logger.debug( "Information ready. Generating the result")
        response = dock.copy()
        response['last_alive'] = response['last_alive'].strftime("%m/%d/%Y %H:%M:%S")
        return {'command' : 'ok', 'description': response}
    
    """ gets the content for a specific container specified by an IP address and its container short ID 
        [GET /containers/IP_ADDRESS/containerID]"""
    def _get_container_content(self, message ) -> dict:
        
        # verification of the presence of the needed message fields
        try:
            message['address']
            message['containerID']
        except KeyError:
            self._logger.error("Error, the function requires an address and a containerID fields")
            return { 'command':'error', 'type': 'missing_par', 'description': 'Missing parameter address or containerID'}

            
        with self._info_lock: # we need to garantee mutual exclusion
            self._logger.debug( "Searching the content for manager " + message['address'])
            dock = None
            for docker in self._containers_data:
                if docker['address'] == message['address']:
                    self._logger.debug( "Container found")
                    dock = docker
                    
        if dock is None: 
            self._logger.warning("Manager not found. Not registered into the controller")
            return { 'command':'error', 'type': 'invalid_op', 'description': 'Selected host is not present into the service'}
                
        if dock['manager_status'] == 'update_present':
            self._logger.debug( "Status of the manager: update_present. Sending a content request")
            result = self._rabbit.send_manager_unicast({
                    "command" : "give_content"
            }, dock['address'])
            
            try:
                if (result['command'] == 'error') and (result['type'] == 'unreachable'):
                    self._logger.warning("Error, the manager isn't reachable")
                    self._set_container_status_offline(message['address'])
                else:
                    self._logger.debug("Updating the information of manager."+message['address'])
                    self._set_container_content(message['address'], result['content'])
              
            except KeyError:
                self._logger.error("An error has occured. Missing mandatory fields")
                return { 'command':'error', 'type': 'missing_par', 'description': 'Internal server error'}
        
        self._logger.debug( "Information ready. Generating the result")
        
        with self._info_lock: # we need to garantee mutual exclusion
            self._logger.debug( "Searching the content for manager " + message['address'])
            dock = None
            for docker in self._containers_data:
                if docker['address'] == message['address']:
                    self._logger.debug( "Container found")
                    dock = docker.copy()
                
        if dock is None: 
            self._logger.warning("Manager not found. Not registered into the controller")
            return { 'command':'error', 'type': 'invalid_op', 'description': 'Selected host is not present into the service'}
                            
        try:
            return {'command':'ok', 'description': dock['content'][message['containerID']]}
        except KeyError:
            return { 'command':'error', 'type': 'CONTAINER_NOT_PRESENT', 'description': 'Specified containerID not present'}
        
    """ gets the content from all the docker managers [GET /containers]"""
    def _get_all_managers_containers_content(self, message) -> list:

        updates_required = []
        with self._info_lock: # we need to guarantee mutual exclusion
            for docker in self._containers_data:
                if docker['manager_status'] == 'update_present':
                    self._logger.debug( "Manager of " + docker['address'] +" needs to be updated")
                    updates_required.append(docker['address'])
            
        for address in updates_required:    
            result = self._rabbit.send_manager_unicast({
                'command' : 'give_content',
                'address' :  socket.gethostbyname(socket.gethostname())
            }, address)
            try:
                if result['command'] == 'error' and result['type'] == 'unreachable':
                    self._logger.warning("Error, the manager isn't reachable")
                    self._set_container_status_offline(address)
                else:
                    self._logger.debug("Updating the information of manager."+address)
                    self._set_container_content(address, result['content'])
                    
            except KeyError:
                self._logger.error("An error has occured. Missing mandatory fields")
                return { 'command':'error', 'type': 'missing_par', 'description': 'Internal server error'}

            
        self._logger.debug( "Starting aggregation of the results")
        # we generate an array with all the formatted responses
        response = list() # we need to make a copy to not change the original dictionary
        with self._info_lock: # we need to guarantee mutual exclusion
            for container in self._containers_data:
                val = container.copy()
                # datatime is not jsonable. We need to transform into a string manually
                val['last_alive']  = container['last_alive'].strftime("%m/%d/%Y %H:%M:%S")
                response.append(val)
        
        return {'command': 'ok','description': response}
    
    """ adds a container previously removed from the service[PUT /containers/IP_ADDRESS/DOCKERID] """
    def add_container(self, message) -> dict:
        # verification of the presence of the needed message fields
        try:
            message['address']   # address of the host maintaining the container
            message['containerID']  # short_id of the container
        except KeyError:
            self._logger.error("Error, the function requires an address field")
            return { 'command':'error', 'type': 'missing_par', 'description': 'Missing parameter address or containerID'}
        
        self._logger.debug("Received request to add a container " + message['containerID'] + " to " + message['address'])       
        return self._rabbit.send_manager_unicast({
                'command' : 'container_add',
                'address' : message['address'],
                'containerID' : message['containerID']
        }, message['address'])
  
    """ removes a container from the service, the container will not be managed by the service [DELETE /containers/IP_ADDRESS/DOCKERID] """
    def remove_container(self, message) -> dict:
        # verification of the presence of the needed message fields
        try:
            message['address'] # address of the host maintaining the container
            message['containerID'] # short_id of the container
        except KeyError:
            self._logger.error("Error, the function requires an address field")
            return { 'command':'error', 'type': 'missing_par', 'description': 'Missing parameter address or containerID'}
        
        self._logger.debug("Received request to remove a container " + message['containerID'] + " to " + message['address'])       
        return self._rabbit.send_manager_unicast({
                'command' : 'container_ignore',
                'address' : message['address'],
                'containerID' : message['containerID']
        }, message['address'])
         
    
    """ changes the threshold used by all the managers [POST /containers]"""
    def change_all_threshold(self, message) -> dict:
        # verification of the presence of the needed message fields
        try:
            message['threshold']  # threshold to be set. It must be a value between 0 and 100
        except KeyError:
            self._logger.error("Error, the function requires an address field")
            return { 'command':'error', 'type': 'missing_par', 'description': 'Missing parameter threshold'}
        
        responses = list()
        for docker in self._containers_data:
            if docker['manager_status'] != 'offline':
                responses.append(self.change_threshold({'address': docker['address'], 'threshold': message['threshold']}))

        return {'command': "ok", 'description': responses}

    """ changes the threshold used by the selected manager [POST /containers/IP_ADDRESS]"""
    def change_threshold(self, message) -> dict:
        # verification of the presence of the needed message fields
        try:
            message['address']   # address of the selected manager
            message['threshold'] # threshold to be set. It must be a value between 0 and 100
        except KeyError:
            self._logger.error("Error, the function requires an address and a threshold field")
            return { 'command':'error', 'type': 'missing_par', 'description': 'Missing parameter address and/or a threshold fields'}
        
        self._logger.debug("Received request to set the threshold to " + str(message['threshold']) + " to " + message['address'])       
        return self._rabbit.send_manager_unicast({
                'command' : 'container_threshold',
                'address' : message['address'],
                'threshold' : message['threshold']
        }, message['address'])
          
    """ TO ANTAGONIST """
    
    """ starts the anagonist on all the registered service host [PUT /test]"""
    def add_antagonists(self, message) -> dict:
        
        responses = []
        for docker in self._containers_data:
            if docker['manager_status'] != 'offline':
                responses.append(self.add_host_antagonist({'address': docker['address']}))
        return {'command': "ok", 'description': responses}
    
    """ starts the antagonist on the selected host [PUT /test/IP_ADDRESS]"""
    def add_host_antagonist(self, message) -> dict:
        # verification of the presence of the needed message fields
        try:
            message['address'] # the address of the selected host
        except KeyError:
            self._logger.error("Error, the function requires an address field")
            return { 'command':'error', 'type': 'missing_par', 'description': 'Missing parameter address'}
 
        return self._rabbit.send_antagonist_unicast({
                'command' : 'start_antagonist',
                'address' : message['address']
        }, message['address'])
            
    """ stops the anagonist on all the registered service host [DELETE /test]"""
    def remove_antagonists(self, message) -> dict:
        responses = []
        for docker in self._containers_data:
            if docker['manager_status'] != 'offline':
                responses.append(self.remove_host_antagonist({'address': docker['address']}))
        return {'command': "ok", 'description': responses}

    """ stops the antagonist on the selected host [DELETE /test/IP_ADDRESS]"""       
    def remove_host_antagonist(self, message) -> dict:
        # verification of the presence of the needed message fields
        try:
            message['address']
        except KeyError:
            self._logger.error("Error, the function requires an address field")
            return { 'command':'error', 'type': 'missing_par', 'description': 'Missing parameter address'}
 
        return self._rabbit.send_antagonist_unicast({
                'command' : 'stop_antagonist',
                'address' : message['address']
        }, message['address'])

    """ changes the anagonist configuration on all the registered service host [POST /test]"""    
    def change_antagonists_config(self, message) -> dict:
        # verification of the presence of the needed message fields
        try:
            message['heavy'],
            message['balance'],
            message['loss'],
            message['frequency']
            message['duration']
            
        except KeyError:
            self._logger.error("Error, the function requires an address field")
            return { 'command':'error', 'type': 'missing_par', 'description': 'Missing parameter address or heavy or balance'}
 
        responses = []
        for docker in self._containers_data:
            if docker['manager_status'] != 'offline':
                responses.append(self.change_host_antagonist_config({
                        'heavy' : message['heavy'],
                        'balance' : message['balance'],
                        'frequency' : message['frequency'],
                        'loss' : message['loss'],
                        'duration' : message['duration'],
                        'address' : docker['address']
                }))
        return {'command': "ok", 'description': responses}

    """ changes the antagonist configuration on the selected host [POST /test/IP_ADDRESS]"""                   
    def change_host_antagonist_config(self, message) -> dict:
        # verification of the presence of the needed message fields
        try:
            message['address'],
            message['heavy'],
            message['balance'],
            message['loss'],
            message['frequency']
            message['duration']
            
        except KeyError:
            self._logger.error("Error, the function requires an address field")
            return { 'command':'error', 'type': 'missing_par', 'description': 'Missing parameter address or heavy or balance'}
 
        return self._rabbit.send_antagonist_unicast({
                        'command' : 'conf_antagonist',
                        'heavy' : message['heavy'],
                        'balance' : message['balance'],
                        'frequency' : message['frequency'],
                        'loss' : message['loss'],
                        'duration' : message['duration']
                }, message['address'])
    
    """ uninstalls the service on all the platform. For security reasons the function is not available from the REST interface """
    def _uninstall(self, message) -> dict:
        dockers = []
        try:
            with self._docker_lock: # we need to garantee mutual exclusion 
                for docker in self._dockers:
                    dockers.append(docker['address'])

            for docker in dockers:
                self._logger.info("Removing the docker manager at " + docker)
                self._remove_docker_manager({'address':docker})

            return { 'command' : 'ok', 'description' : 'All the service removed. Service down after this message' }
        except:
            return { 'command' : 'error' , 'type' : 'INTERNAL_ERROR', 'description' : 'An error has occurred during the request management' }

    """ STRESS TEST """
    
    """ thread to collect availability samples """
    def test_availability(self):
        
        # more precise start of the test. The system allocate all the services, then starts them simultaneusly
        while self._collect_data is False:
            pass
        
        # when the stress test is completed _collect_data will be set to False
        while self._collect_data is True:
            update = False
            with self._info_lock: # verification of update presence
                for docker in self._containers_data:
                    if docker['manager_status'] == 'update_present':
                        update = True
            # if an update is present, then the controller is not available(it doesn't have all the information)
            if update is True:
                self._availability.loc[datetime.now()] = [0] # NOT AVAILABLE
            else:
                self._availability.loc[datetime.now()] = [1] # AVAILABLE
            sleep(0.25) # the availability is measured 4 times per second
    
    """ thread to aggregate bandwidth samples """
    def test_bandwidth(self):
        
        # more precise start of the test. The system allocate all the services, then starts them simultaneusly
        while self._collect_data is False:
            pass
        
        # when the stress test is completed _collect_data will be set to False
        while self._collect_data is True:
            with self._counter_lock and self._data_lock: # mutual exclusion on bandwidth counter and test data storage
                self._bandwidth.loc[datetime.now()] = [self._len_aggregation_counter] # add a new bandwidth measure
                self._len_aggregation_counter = 0 # reset the counter
            sleep(1) # the bandwidth is measure each second to obtain a measure in byte per second(to obtain bps multiply it by 8)
       
    """ stress test, measures the availability and the bandwidth used for the container information update with various attacker
        behaviour. This test is important to identify the better aggregation time value in order to get high availability in critical
        conditions without have a big impact on the bandwidth consumed by the managers communications """         
    def _start_test( self):
        
        if self._collect_data is True:
            return

        # prestart the threads for collecting the test samples
        threading.Thread(target=self.test_availability).start()
        threading.Thread(target=self.test_bandwidth).start()
        
        tests = [ {    # low attack low frequency
                  'name'      : 'test_low_low',
                  'command'   : 'conf_antagonist',
                  'loss'      : 80,
                  'balance'   : 70,
                  'heavy'     : 25,
                  'frequency' : 1,
                  'duration'  : 5
        },{    # low attack high frequency
                  'name'      : 'test_low_high',
                  'command'   : 'conf_antagonist',
                  'loss'      : 80,
                  'balance'   : 70,
                  'heavy'     : 25,
                  'frequency' : 0.1,
                  'duration'  : 5
        },{    # heavy attack low frequency
                  'name'      : 'test_high_low',
                  'command'   : 'conf_antagonist',
                  'loss'      : 80,
                  'balance'   : 70,
                  'heavy'     : 90,
                  'frequency' : 1,
                  'duration'  : 20
        },{    # heavy attack high frequency
                  'name'      : 'test_high_high',
                  'command'   : 'conf_antagonist',
                  'loss'      : 80,
                  'balance'   : 70,
                  'heavy'     : 90,
                  'frequency' : 0.1,
                  'duration'  : 20
        }]
          
        # with this attacker configuration having greater waiting times is useless. The test will lose is stochastic behaviour
        # because a new update will be generated in less then 1s, so we have always an update after an aggregation time  
        waiting_time = [0.1,1,2.5]
        
        # starting all the antagonists
        
        self._logger.info("Starting testing phase")
        for test in tests: 
            self._logger.info("Starting test: " + test['name'])
            # apply the configuration on all the antagonists
            self.change_antagonists_config(test)
            self.add_antagonists({})
            sleep(5) # wait for the system to be in stable state
            # starting collecting of data(here because more precise, otherwise we collect many samples without 
            # having changed the configuration of the antagonists)
            self._collect_data = True
            for waiting in waiting_time:
                self._aggregation_time = waiting
                for a in range(0,30):  # 30 repetition per test in order to compute the confidence with CLT
                    with self._data_lock:
                        self._availability = DataFrame(columns=['availability'])
                        self._bandwidth = DataFrame(columns=['size'])
                    sleep(300) # for time problems, each test will be runned for 5m(30h total test time)
                    with self._data_lock:
                        self._availability.to_csv('/root/data/availability/availability_'+test['name']+'_'+str(waiting)+'_'+str(datetime.now())+'_'+str(a)+'.csv')
                        self._bandwidth.to_csv('/root/data/bandwidth/bandwidth_'+test['name']+'_'+str(waiting)+'_'+str(datetime.now())+'_'+str(a)+'.csv')
            self._collect_data = False
            self.remove_antagonists({})
            self._logger.info("Test " + test['name'] + " completed")
            
""" SERVICE """
control = controller()

try:
    while True:
        pass
except:
    control.close_all()