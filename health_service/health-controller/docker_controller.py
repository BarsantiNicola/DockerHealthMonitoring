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

    Class to generate a controller for the docker health monitor service. The controller has the following duties:
        - allocate/remove the managers from an host
        - verifing the managers status by an heartbeat system
        - maitaining and manage the containers information given by the managers using an asynchronous communication

"""
        
class controller:
     
    def __init__(self):
        self._aggregation_time = 30  # time interval for the pending updates elaboration
        self._enable_test = False    # enable the collect of data for testing purpouse
        self._configuration = None   # configuration getted from the configuration file[contains rabbitMQ address]
        self._rabbit = None          # instance of rabbitMQ management class
        self._dockers = []           # maintains all the information about registered dockers
        self._containers_data = []   # maintains all the containers information given from the managers
        self._docker_lock = threading.Lock()     # lock for mutual exclusion on self.dockers operations
        self._info_lock = threading.Lock()       # lock for mutual exclusion on self.containers_data operations
        self._logger = None          # class logger
        self._exit = True
        
        # test variables
        self._collect_data = False   # triggers the interface to collect data from the operations
        self._availability = None    # dataframe for availability measurements
        self._bandwidth = None       # dataframe for bandwidth measurements
        self._data_lock = threading.Lock()  # lock for mutual exclusion of dataframes

        self._len_aggregation_counter = 0  # counter for bandwidth measurements
        self._counter_lock = threading.Lock()  # lock for mutual exclusion on len_aggregation_counter
        
        # interface shared with outside clients by rabbitMQ
        self._interface = {
           'live' : self._set_heartbeat,
           'update' : self._set_container_status_update_present,

           'add_host' : self._load_docker_manager,
           'remove_host' : self._remove_docker_manager,
           
           'get_all_containers' : self._get_all_managers_containers_content,
           'get_container' : self._get_manager_container_content,
           'get_host_containers' : self._get_manager_containers_content,
           
           'add_container' : self.add_container,  
           'remove_container' : self.remove_container,
           
           'change_all_threshold' : self.change_all_threshold,
           'change_threshold' : self.change_threshold,

           'add_antagonists' : self.add_antagonists,
           'add_host_antagonist' : self.add_host_antagonist,
           'change_antagonists_config' : self.change_antagonists_config,
           'change_host_antagonist_config' : self.change_host_antagonist_config,
           'remove_antagonists' : self.remove_antagonists,
           'remove_host_antagonist' : self.remove_host_antagonist , 
           
           'uninstall': self._uninstall,
           'test' : self._test
        }
        
        self._initialize_logger()
        if self._load_conf() is False:   # load the configuration which contains the IP address of rabbitMQ
            return
        
        # we don't have mutual exclusion on load_data so is important to be used before init_rabbit()
        self._load_data()     # load the stored data about the connected dockerManagers
        
        if self._init_rabbit() is False: # initialization of rabbitMQ, creation of the channels to receive and send messages
            return
        
        # starting initial update of containers
        #self._initialize_all_containers()
        
        self._logger.debug("Started periodic service of pending management")
        threading.Thread(target=self._pending_manager).start()
        self._logger.debug("Service started")
        self._logger.debug("Started periodic service of heartbeat management")
        threading.Thread(target=self._heartbeat_manager).start()
        self._logger.debug("Service started")
        self._logger.info("Controller initialization completed at " + socket.gethostbyname(socket.gethostname()))    
            
    """ UTILITY FUNCTIONS """
    
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
        
    """  initialize the rabbitMQ client to be used by the controller class """    
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
     
    def close_all(self):
        self._exit = False
        self._rabbit.close_all()
        
    
    """ DOCKER MANAGERS MANAGEMENT """
            
    """ [ DATA STORING ] """
    
    """ load from the file system the configured docker managers. Used in case of service restart """
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
                        'status' : 'offline',    # we don't know yet if the manager is correctly allocated
                        'last_alive' : datetime.now() + timedelta(minutes=5) })   # to know soon or later if the manager is active
            self._logger.debug("Containers data table build")
            
        except FileNotFoundError:
            self._logger.warning("Data stored not found")
        except ValueError:
            self._logger.error("Error, invalid stored data. Data not loaded, service re-initialized")

    """ store the configured docker managers inside the file system in case of service shutdown """        
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
    
    """ verify the presence of a docker manager identified by its IP address into the controller """        
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
    def _remove_docker(self, address) -> bool:
        
        with self._docker_lock: # we need to garantee the mutual exclusion
            self._logger.debug("Searching the docker manager instance: " + address + " for docker manager removal")  
            for docker in self._dockers:
                if docker['address'] == address: # address is used as an identificator of a docker manager
                    self._logger.debug("Docker manager found")  
                    self._dockers.remove(docker)
                    self._logger.debug("Docker manager removed")  
                    # in order to reduce the time in mutual exclusion and simplify the code the saving 
                    # of the updates is done on the caller function
                    return True
                
        self._logger.debug("Docker manager not found")          
        return False
        
    """ used for the docker manager removal, get the password of the host from the ip address of the docker manager """
    def _get_docker_password(self, address) -> str:
        
        with self._docker_lock: # we need to garantee mutual exclusion
            self._logger.debug("Searching the docker manager instance: " + address + " for password retrival") 
            for docker in self._dockers:
                if docker['address'] == address: # address is used as an identificator of a docker manager
                    self._logger.debug("Docker manager found") 
                    return docker['password']
                
        self._logger.debug("Docker manager not found")         
        return '' 
    
    """ [ MAIN FUNCTIONALITIES ] """
    
    """ generates the configuration file for the managers. The file will contain the address of the rabbitMQ broker """
    def _generate_configuration(self, address) -> None:
        # configuration file used by managers will be in the components folder
        self._logger.debug("Generation of configuration file..")
        with open('../health-manager/configuration','w') as writer:
            writer.write(json.dumps({'address': address}))
        self._logger.debug("Generation of configuration file completed")
        
    """ load the docker manager and the antagonist into an host identified by its address and root password """
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
                # inside the folder we put all the files present into the components subdirectory
                for item in os.listdir('/root/health_service/health-manager'):
                    sftp.put('/root/health_service/health-manager/'+item,'/root/health_manager/'+item)
                # the manager/antagonist will run as a service on the remove machine. We need to put its definition
                sftp.put('../docker-health-monitor.service','/etc/systemd/system/docker-health-monitor.service')
                self._logger.debug("Data completely transfered to the machine " + message['address'])
                sftp.close()
                self._logger.debug("Sftp channel closed")
                self._logger.debug("Execution of final operation on the remove host..")
                # the service definition must be set as executable
                ssh.exec_command('apt-get install -y python3.7 pip')
                ssh.exec_command('update-alternatives  --set python /usr/bin/python3.7')
                ssh.exec_command('pip install --no-cache-dir -r /root/health_service/requirements.txt')
                ssh.exec_command('chmod 0777 /etc/systemd/system/docker-health-monitor.service')
                ssh.exec_command('systemctl daemon-reload')
                ssh.exec_command('service docker-health-monitor start')
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
                        'status' : 'offline',    # we don't know yet if the manager is correctly running
                        'last_alive' : datetime.now() + timedelta(minutes=5) })   # to know soon or later if the manager is active
                self._logger.debug("Controller has complete the update")
                if self._save_data() is True:
                    return { 'command':'ok', 'description': 'New Docker host added to the service'}
                else:
                    return { 'command':'ok', 'description': 'New Docker host added to the service but the service was not able to save the update'}
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

                ssh.exec_command('service docker-health-monitor stop')
                ssh.exec_command('rm /etc/systemd/system/docker-health-monitor.service')
                ssh.exec_command('rm -R /root/health_manager')
                ssh.exec_command('systemctl daemon-reload')
                ssh.close()
                self._logger.debug("Data completely removed from the machine " + message['address'] + ". Secure channel closed")
                self._remove_docker(message['address'])
                if self._save_data() is True:
                    return { 'command':'ok', 'description': 'Host removed from the service'}
                else:
                    return { 'command': 'error', 'description': 'Error, host connected but an error has occurred during the saving of the updates. A shutdown will delete your operations'}
            except:
                self._logger.error('Error during the removal of the manager service')
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
                    return docker['status']
                
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
                    if docker['status'] != 'wait_update': # if controller is already waiting the update no change needed
                        docker['status'] = 'update_present'
                        docker['last_alive'] = datetime.now() + timedelta(minutes=5)
                        self._logger.debug("Container " + message['address'] + " status set to 'update_present'")
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
                    self._logger.debug("Container " + address + " found. Status set to 'offline'")
                    docker['status'] = 'offline'
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
                    docker['status'] = 'updated'
                    self._logger.debug("Container found")
                    return True
        
        self._logger.debug("Container not found")
        return False  
    
    """ stringifies a docker manager content to be showed to the user """
    def _generate_content(self, containers) -> str:
        content = ''
        if containers['status'] == 'offline':
            return "Docker Manager: "+ containers['address'] + " Status: OFFLINE"+os.linesep + "Content:  NO CONTENT AVAILABLE"
        
        for container_content in containers['content']:
            content += '\t\t' + container_content + os.linesep
            
        if containers['status'] == 'update_present':
            return "Docker Manager: "+ containers['address'] + " Status: NOT UPDATED" + os.linesep + "Content: " + os.linesep + content
        if containers['status'] == 'updated':
            return "Docker Manager: "+ containers['address'] + " Status: UPDATED"+os.linesep+"Content: "+ os.linesep + content
        return ''
    
    """ gets the content for a specific docker manager container identified by its address and containerID """
    def _get_manager_container_content(self, message ) -> dict:
        
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
                
        if dock['status'] == 'update_present':
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
        
        self._logger.debug( "Information ready. Generating the result")
        return {'command' : 'ok', 'description': self.generate_content(dock)}  # to be changed with container searching
    
    """ gets the content for a specific docker manager identified by its address """
    def _get_manager_containers_content(self, message ) -> dict:
        
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
                
        if dock['status'] == 'update_present':
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
        return {'command' : 'ok', 'description': self._generate_content(dock)}
    
    """ gets the content from all the docker managers """
    def _get_all_managers_containers_content(self, message) -> list:

        updates_required = []
        with self._info_lock: # we need to garantee mutual exclusion
            for docker in self._containers_data:
                if docker['status'] == 'update_present':
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
        with self._info_lock:
            return {'command' : 'ok', 'description': [self._generate_content(docker) for docker in self._containers_data]}

    """ sets the last received heartbeat for the manager activity management """
    def _set_heartbeat(self, message) -> bool:
        
        with self._info_lock:
            try:
                self._logger.debug("Searching manager of " + message['address'] +" for heartbeat update")
                for docker in self._containers_data:
                    if docker['address'] == message['address']:
                        self._logger.debug("Container found")
                        docker['last_alive'] = datetime.now() + timedelta(minutes=5)
                        if docker['status'] == 'offline':
                            docker['status'] = 'update_present'
                            self._logger.debug("Changed manager status from offline to update_present")
                        return True
            except KeyError:
                self._logger.error("Error, alive messages must contain 'address' field")
                return False
            
        self._logger.debug("Container not found")
        return False
           
    """ [ MAIN FUNCTIONALITIES ] """
             
    def _pending_manager(self) -> None:
        while self._exit:
            self._logger.debug("Executing pending updates verification")
            docker_request = list()
            with self._info_lock:
                for docker in self._containers_data:
                    if docker['status'] == 'update_present':
                        docker_request.append(docker['address'])
            for docker in docker_request:
                self._logger.debug("Found a pending update. Start synchronization for manager at " + docker)
                with self._counter_lock:
                    self._len_aggregation_counter +=45
                result = self._rabbit.send_manager_unicast({
                            "command" : "give_content"
                }, docker)
                with self._counter_lock:
                    self._len_aggregation_counter += len( json.dumps(result))
                try:
                    self._set_container_content(docker, result['content'])
                except:
                    self._logger.warning("Empty updated. Undo operation")
            time.sleep(self._aggregation_time)
        self._logger.debug("Closing pending manager thread")   
        
    def _heartbeat_manager(self) -> None:
        while self._exit:
            self._logger.debug("Executing hearbeat verification")
            with self._info_lock:
                for docker in self._containers_data:
                    if docker['last_alive'] < datetime.now():
                        docker['status'] = 'offline'
            
            time.sleep(60)
        self._logger.debug("Closing heartbeat thread")
            
    """ REST INTERFACE COMMUNICATION MANAGEMENT """

    """ TO MANAGER """
    
    """ add a new controller identified by an ip address and a containerID to the service """
    def add_container(self, message) -> dict:
        try:
            message['address']
            message['containerID']
        except KeyError:
            self._logger.error("Error, the function requires an address field")
            return { 'command':'error', 'type': 'missing_par', 'description': 'Missing parameter address or containerID'}
        
        self._logger.debug("Received request to add a container " + message['containerID'] + " to " + message['address'])       
        return self._rabbit.send_manager_unicast({
                'command' : 'container_add',
                'address' : message['address'],
                'containerID' : message['containerID']
        }, message['address'])
  
    def remove_container(self, message):
        try:
            message['address']
            message['containerID']
        except KeyError:
            self._logger.error("Error, the function requires an address field")
            return { 'command':'error', 'type': 'missing_par', 'description': 'Missing parameter address or containerID'}
        
        self._logger.debug("Received request to remove a container " + message['containerID'] + " to " + message['address'])       
        return self._rabbit.send_manager_unicast({
                'command' : 'container_ignore',
                'address' : message['address'],
                'containerID' : message['containerID']
        }, message['address'])
            
    def change_all_threshold(self, message) -> dict:
        try:
            message['address']
        except KeyError:
            self._logger.error("Error, the function requires an address field")
            return { 'command':'error', 'type': 'missing_par', 'description': 'Missing parameter address'}
        
        responses = list()
        for docker in self._containers_data:
            if docker['status'] != 'offline':
                responses.append(self.change_threshold({'address': docker['address'], 'threshold': message['threshold']}))

        return {'command': "ok", 'message': 'Responses received: ' + json.dumps(responses)}

    def change_threshold(self, message) -> dict:
        try:
            message['address']
            message['threshold']
        except KeyError:
            self._logger.error("Error, the function requires an address and a threshold field")
            return { 'command':'error', 'type': 'missing_par', 'description': 'Missing parameter address and a threshold fields'}
        
        self._logger.debug("Received request to set the threshold to " + str(message['threshold']) + " to " + message['address'])       
        return self._rabbit.send_manager_unicast({
                'command' : 'container_threshold',
                'address' : message['address'],
                'threshold' : message['threshold']
        }, message['address'])
          
    """ TO ANTAGONIST """
    def add_antagonists(self, message):
        
        responses = []
        for docker in self._containers_data:
            if docker['status'] != 'offline':
                responses.append(self.add_host_antagonist({'address': docker['address']}))
        return {'command': "ok", 'message': 'Responses received: ' + json.dumps(responses)}
    
    def add_host_antagonist(self, message):
        try:
            message['address']
        except KeyError:
            self._logger.error("Error, the function requires an address field")
            return { 'command':'error', 'type': 'missing_par', 'description': 'Missing parameter address'}
 
        return self._rabbit.send_antagonist_unicast({
                'command' : 'start_antagonist',
                'address' : message['address']
        }, message['address'])
            
    def remove_antagonists(self, message):
        responses = []
        for docker in self._containers_data:
            if docker['status'] != 'offline':
                responses.append(self.remove_host_antagonist({'address': docker['address']}))
        return {'command': "ok", 'message': 'Responses received: ' + json.dumps(responses)}

            
    def remove_host_antagonist(self, message):
        try:
            message['address']
        except KeyError:
            self._logger.error("Error, the function requires an address field")
            return { 'command':'error', 'type': 'missing_par', 'description': 'Missing parameter address'}
 
        return self._rabbit.send_antagonist_unicast({
                'command' : 'stop_antagonist',
                'address' : message['address']
        }, message['address'])


    def change_antagonists_config(self, message):
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
            if docker['status'] != 'offline':
                responses.append(self.change_host_antagonist_config({
                        'heavy' : message['heavy'],
                        'balance' : message['balance'],
                        'frequency' : message['frequency'],
                        'loss' : message['loss'],
                        'duration' : message['duration'],
                        'address' : docker['address']
                }))
        return {'command': "ok", 'message': 'Responses received: ' + json.dumps(responses)}

                
    def change_host_antagonist_config(self, message):
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
    
    def _uninstall(self, message):
        dockers = []
        with self._docker_lock: # we need to garantee mutual exclusion 
            for docker in self._dockers:
                dockers.append(docker['address'])
        
        for docker in dockers:
            self._logger.debug("Removing the docker manager at " + docker['address'])
            self._remove_docker_manager({'address':docker['address']})
        
        self.close_all()
        return { 'command' : 'ok', 'description' : 'All the service removed. Service down after this message' }

    def _test( self, message ):
        threading.Thread(target=self._start_test).start()
        return {'command': 'ok', 'description' : 'Test started'}
    
    def _save_collected_data(self, destination):
        self._test_data.to_csv(destination+'.csv')
    
    def test_availability(self):
        while self._collect_data is False:
            pass
        
        while self._collect_data is True:
            update = False
            with self._info_lock:
                for docker in self._containers_data:
                    if docker['status'] == 'update_present':
                        update = True
            if update is True:
                self._availability.loc[datetime.now()] = [0]
            else:
                self._availability.loc[datetime.now()] = [1]
            sleep(0.25)
    
    def test_bandwidth(self):
        while self._collect_data is False:
            pass
        
        while self._collect_data is True:
            with self._counter_lock and self._data_lock:
                self._bandwidth.loc[datetime.now()] = [self._len_aggregation_counter]
                self._len_aggregation_counter = 0
            sleep(1)
                
    def _start_test( self):
        
        if self._collect_data is True:
            return

        threading.Thread(target=self.test_availability).start()
        threading.Thread(target=self.test_bandwidth).start()
        tests = [ {    # low attack low frequency
                  'name'      : 'test_low_low',
                  'command'   : 'conf_antagonist',
                  'loss'      : 80,
                  'balance'   : 70,
                  'heavy'     : 25,
                  'frequency' : 5,
                  'duration'  : 1
        },{    # low attack high frequency
                  'name'      : 'test_low_high',
                  'command'   : 'conf_antagonist',
                  'loss'      : 80,
                  'balance'   : 70,
                  'heavy'     : 25,
                  'frequency' : 0.5,
                  'duration'  : 1
        },{    # medium attack medium frequency
                  'name'      : 'test_med_med',
                  'command'   : 'conf_antagonist',
                  'loss'      : 80,
                  'balance'   : 60,
                  'heavy'     : 70,
                  'frequency' : 2.5,
                  'duration'  : 2
        },{    # heavy attack low frequency
                  'name'      : 'test_high_low',
                  'command'   : 'conf_antagonist',
                  'loss'      : 80,
                  'balance'   : 80,
                  'heavy'     : 95,
                  'frequency' : 5,
                  'duration'  : 1
        },{    # heavy attack high frequency
                  'name'      : 'test_high_high',
                  'command'   : 'conf_antagonist',
                  'loss'      : 70,
                  'balance'   : 80,
                  'heavy'     : 90,
                  'frequency' : 0.5,
                  'duration'  : 1
        }]
           
        waiting_time = [0.1, 0.5, 1,5,10]
        self.remove_antagonists({})
        for test in tests: 
            self._logger.debug("TEST: " + json.dumps(self.change_antagonists_config(test)))
            self._logger.debug("TEST: " + json.dumps(self.add_antagonists({})))
            self._collect_data = True
            for waiting in waiting_time:
                with self._data_lock:
                    self._availability = DataFrame(columns=['availability'])
                    self._bandwidth = DataFrame(columns=['size'])
                self._aggregation_time = waiting
                sleep(1800)
                with self._data_lock:
                    self._availability.to_csv('/home/nico/availability_'+test['name']+'_'+str(waiting)+'_'+str(datetime.now())+'.csv')
                    self._bandwidth.to_csv('/home/nico/bandwidth_'+test['name']+'_'+str(waiting)+'_'+str(datetime.now())+'.csv')
            self._logger.debug("TEST: " + json.dumps(self.remove_antagonists({})))
        self._collect_data = False
        
"""    
    
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
"""
        
#control = controller()
#try:
 #   while True:
  #      pass
#except:
 #   control.close_all()   
 
