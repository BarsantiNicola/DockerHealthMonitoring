from rabbit import client
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
        self._result_ready = threading.Event()   # lock for the rest interface to wait all the pending updates completed
        self._docker_lock = threading.Lock()     # lock for mutual exclusion on self.dockers operations
        self._info_lock = threading.Lock()       # lock for mutual exclusion on self.containers_data operations
        self._update_available = False           # verification for new pending updates received during container update
        self._logger = None          # class logger
        
        self.initialize_logger()
        if self.load_conf() is False:   # load the configuration which contains the IP address of rabbitMQ
            return None
        
        # we don't have mutual exclusion on load_data so is important to be used before init_rabbit()
        self.load_data()     # load the stored data about the connected dockerManagers
        
        if self.init_rabbit() is False: # initialization of rabbitMQ, creation of the channels to receive and send messages
            return None
        
        # starting initial update of containers
        self._rabbit.send_manager_multicast( json.dumps({
                'command' : 'give_content'
        }))
        
        self._logger.debug("Started periodic service of pending management")
        threading.Thread(target=self.pending_manager).start()
        self._logger.debug("Service started")
        self._logger.debug("Started periodic service of heartbeat management")
        threading.Thread(target=self.heartbeat_manager).start()
        self._logger.debug("Service started")
        self._logger.info("Controller initialization completed")    
            
    """ UTILITY FUNCTIONS """
    
    """ configure the logger behaviour """
    def initialize_logger(self):
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
    def load_conf(self) -> bool:
        
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
    def init_rabbit(self) -> bool:
        try:
            # connect the client to the rabbitMQ broker 
            self._logger.debug("Connecting to the rabbitMQ broker..")
            self._rabbit = client(self._configuration['address'])
            self._logger.debug("Correctly connected to the broker. Send message action available")
            
            if self._rabbit is not None:
                self._logger.debug("Allocating the receiver queue")
                # allocating a queue on a different thread and connect it to a callback function to be used
                # on a message arrival
                self._rabbit.allocate_receiver('controller', self.controller_callback)
                self._logger.debug("Receiving queue correctly connected. Component fully functional")
                return True
            
        except KeyError:
            self._logger.error('Error, address field not found')
            
        return False 
    
    """ callback function used on message arrival """
    def controller_callback(self, method, properties, x, body):
        self._logger.debug("New message received: " + str(body))
        # messages are encoded as json objects
        self.command_management(json.loads(body)) # message management function
        
    """ DOCKER MANAGERS MANAGEMENT """
            
    """ [ DATA STORING ] """
    
    """ load from the file system the configured docker managers. Used in case of service restart """
    def load_data(self):
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
    def save_data(self) -> bool:
        
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
    def verify_docker_presence(self, address) -> bool:
        
        with self._docker_lock: # we need to garantee mutual exclusion
            self._logger.debug("Starting verification of docker manager presence for host: " + address)    
            for docker in self._dockers:
                if docker['address'] == address: # address is used as an identificator of a docker manager
                    self._logger.debug("Docker manager found")  
                    return True
                
        self._logger.debug("Docker manager not found")          
        return False

    """ removes a docker manager instance from the docker manager container """
    def remove_docker(self, address) -> bool:
        
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
    def get_docker_password(self, address) -> str:
        
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
    def generate_configuration(self, address) -> None:
        # configuration file used by managers will be in the components folder
        self._logger.debug("Generation of configuration file..")
        with open('components/configuration','w') as writer:
            writer.write(json.dumps({'address': address}))
        self._logger.debug("Generation of configuration file completed")
        
    """ load the docker manager and the antagonist into an host identified by its address and root password """
    def load_docker_manager(self, address, password) -> bool:

        # verification that the docker manager isn't registered yet
        if self.verify_docker_presence(address) is False:   
            try:
                self._logger.debug("Starting secure channel generation..")
                # generation of the configuration file the rabbitMQ broker ip address
                self.generate_configuration(address)
                # generation of an ssh connection with the host
                ssh = paramiko.SSHClient() 
                ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                ssh.load_host_keys(os.path.expanduser(os.path.join("~", ".ssh", "known_hosts")))
                ssh.connect(address, username='root', password=password)
                self._logger.debug("Secure channel created")
                # generation of a secure ftp session for the data transfer
                self._logger.debug("Generation of a secure ftp communication over the ssh connection")
                sftp = ssh.open_sftp()
                self._logger.debug("Generation of sftp service completed. Controller ready to send data")
                try:
                    self._logger.debug("Starting transfer of needed data..")
                    # we have to manually generate the folder
                    sftp.mkdir('/root/health_manager')
                    # inside the folder we put all the files present into the components subdirectory
                    for item in os.listdir('components'):
                        sftp.put('components/'+item,'/root/health_manager/'+item)
                except OSError:
                    self._logger.warning('Folder already present') # if the folder is already present. 
                
                # the manager/antagonist will run as a service on the remove machine. We need to put its definition
                sftp.put('docker-health-monitor.service','/etc/systemd/system/docker-health-monitor.service')
                self._logger.debug("Data completely transfered to the machine " + address)
                sftp.close()
                self._logger.debug("Sftp channel closed")
                self._logger.debug("Execution of final operation on the remove host..")
                # the service definition must be set as executable
                ssh.exec_command('apt-get install -y python3.7 pip')
                ssh.exec_command('update-alternatives  --set python /usr/bin/python3.7')
                ssh.exec_command('pip install --no-cache-dir -r /root/health_manager/requirements.txt')
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
                                'address': address,
                                'password': password
                        })
                self._logger.debug("Managers information updated")
                
                self._logger.debug("Building container information for the new manager")    
                # building a placeholder for the docker manager containers
                with self._info_lock: # we need to garantee mutual exclusion
                    self._containers_data.append({
                        'address' : address,    # to identify the manager which the data are referring to
                        'content' : 'NO CONTENT AVAILABLE',     
                        'status' : 'offline',    # we don't know yet if the manager is correctly running
                        'last_alive' : datetime.now() + timedelta(minutes=5) })   # to know soon or later if the manager is active
                self._logger.debug("Controller has complete the update")

            except:
                self._logger.error('Error during the machine connection. Abort operation')
                return False
            return self.save_data()
        return False
    

    """ removes a docker manager previusly registered inside the controller """     
    def remove_docker_manager(self, address) -> bool:
        
        # verification of docker manager presence
        if self.verify_docker_presence(address) is True: 
            try:
                # generation of a secure channel
                self._logger.debug("Starting a secure channel generation to " + address)
                ssh = paramiko.SSHClient() 
                ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                ssh.load_host_keys(os.path.expanduser(os.path.join("~", ".ssh", "known_hosts")))
                ssh.connect(address, username='root', password=self.get_docker_password(address))
                self._logger.debug("Secure channel created")
                # generation of a secure ftp session for the data transfer
                self._logger.debug("Manager service stopped")

                ssh.exec_command('service docker-health-monitor stop')
                ssh.exec_command('rm /etc/systemd/system/docker-health-monitor.service')
                ssh.exec_command('rm -R /root/health_manager')
                ssh.exec_command('systemctl daemon-reload')
                ssh.close()
                self._logger.debug("Data completely removed from the machine " + address + ". Secure channel closed")
                self.remove_docker(address)
                return self.save_data()
            except:
                self._logger.error('Error during the removal of the manager service')
        return False
        
    """ CONTAINERS INFORMATION MANAGEMENT """
    
    """ [ DATA STORING ] """
    
    """ gives the container status. Possible statuses: offline, pending_update, wait_update, updated """
    def get_container_status(self, address) -> str:
        
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
    def set_container_status_update_present(self, address) -> bool:
        with self._info_lock: # we need to garantee mutual exclusion
            self._logger.debug("Searching the container information for " + address)
            for docker in self._containers_data:
                if docker['address'] == address:
                    self._logger.debug("Container found")
                    if docker['status'] != 'wait_update': # if controller is already waiting the update no change needed
                        docker['status'] = 'update_present'
                        self._logger.debug("Container " + address + " status set to 'update_present'")
                        return True
                    self._logger.debug("Container " + address + " already waiting the update. Operation aborted")
                    return False
        
        self._logger.debug("Container not found")          
        return False

    """ sets the container status to offline. The flag means that the manager isn't reachable """
    def set_container_status_offline(self, address) -> bool:
        with self._info_lock: # we need to garantee mutual exclusion
            self._logger.debug("Searching the container information for " + address)
            for docker in self._containers_data:
                if docker['address'] == address:
                    self._logger.debug("Container " + address + " found. Status set to 'offline'")
                    docker['status'] = 'offline'
                    return True 
        self._logger.debug("Container not found")          
        return False
    
    """ sets the container status to wait_update. The flag means that the controller has sent a request for receiving
        the update from the manager and it's waiting for the reply """
    def set_container_status_wait_update(self, address) -> bool:
        with self._info_lock: # we need to garantee mutual exclusion
            self._logger.debug("Searching the container information for " + address)
            for docker in self._containers_data:
                if docker['address'] == address:
                    self._logger.debug("Container found")
                    if docker['status'] != 'updated': # a content update can be sent only from an explicit controller request
                        self._logger.debug("Container " + address + " status set to 'wait_update'")                        
                        docker['status'] = 'wait_present'
                        return True 
                    self._logger.debug("Container " + address + " is signed as updated. Operation aborted")
                    return False
                
        self._logger.debug("Container not found")          
        return False
    
    """ sets the container status to updated. The flag means that the controller is updated with the information maitained
        by the manager """
    def set_container_status_updated(self, address) -> bool:
        with self._info_lock: # we need to garantee mutual exclusion
            self._logger.debug("Searching the container information for " + address)
            for docker in self._containers_data:
                if docker['address'] == address:
                    self._logger.debug("Container found")
                    if docker['status'] != 'wait_update': # a content update can be sent only from an explicit controller request
                        self._logger.debug("Container " + address + " status set to 'updated'")                        
                        docker['status'] = 'updated'
                        return True 
                    self._logger.debug("Container " + address + " is not waiting an update. Operation aborted")
                    return False
                
        self._logger.debug("Container not found")          
        return False
    
    """ sets the container content. The content is the list of the containers with their status"""
    def set_container_content(self, address, content) ->bool:
        with self._info_lock: # we need to garantee mutual exclusion
            self._logger.debug("Searching the container information for " + address)
            for docker in self._containers_data:
                if docker['address'] == address:
                    docker['content'] = content
                    docker['status'] = 'updated'
                    self._logger.debug("Container found")
                    return True
        
        self._logger.debug("Container not found")
        return False  
    
    """ stringifies a docker manager content to be showed to the user """
    def generate_content(self, containers) -> str:
        
        if containers['status'] == 'offline':
            return "Docker Manager: "+ containers['address'] + " Status: OFFLINE\n NO CONTENT AVAILABLE"
        if containers['status'] == 'updated':
            return "Docker Manager: "+ containers['address'] + " Status: UPDATED\n Content: "+ containers['content']
        return ''
    
    """ gets the content for a specific docker manager identified by its address """
    def get_container_content(self, address ) -> str:
        
        
        with self._info_lock: # we need to garantee mutual exclusion
            self._logger.debug( "Searching the content for manager " + address)
            dock = None
            for docker in self._containers_data:
                if docker['address'] == address:
                    self._logger.debug( "Container found")
                    dock = docker
        if dock is None: 
            self._logger.warning("Manager not found. Not registered into the controller")
            return ''
        
        if dock['status'] == 'wait_update':
            self._logger.debug( "Status of the manager: wait_update. Waiting the update receival")
            self._result_ready.wait()
            self._logger.debug( "Container updated. Aggregation of the result")
            return self.get_container_content(address)
        
        if dock['status'] == 'update_present':
            self._logger.debug( "Status of the manager: update_present. Sending a content request")
            self._rabbit.send_manager_unicast(json.dumps({
                    "command" : "give_content"
            }), dock['address'])
            self._logger.debug( "Status of the manager set to wait_update. Waiting the update receival")
            self._result_ready.wait()
            self._logger.debug( "Container updated. Aggregation of the result")
            return self.get_container_content(address)
        
        self._logger.debug( "Information ready. Generating the result")
        return self.generate_content(dock)
    
    """ gets the content from all the docker managers """
    def get_containers_content(self) -> list:
        wait = False
        with self._info_lock: # we need to garantee mutual exclusion
            for docker in self._containers_data:
                
                if docker['status'] != 'offline' and docker['status'] != 'update':
                    self._logger.debug( "Manager of " + docker['address'] +" is not ready: " + docker['status'])
                    # for each manager is it has status update_present or wait_update we need to wait the content
                    wait = True
                    # if there is a pending update we send a request to receive it
                    if docker['status'] == 'update_present':
                        self._rabbit.send_manager_unicast(json.dumps({
                                "command" : "give_content"
                        }), docker['address'])
                        # we set status as wait_update to prevent other update requests
                        docker['status'] = 'wait_update'
                        self._logger.debug( "Request of update sent to " + docker['address'])
        # if something need to be updated we wait until all the content is ready
        if wait is True:
            self._logger.debug( "Pending updated present. Waiting all the data to be ready")
            self._result_ready.wait()
            self._logger.debug( "Pending updates resolved")
            
        self._logger.debug( "Starting aggregation of the results")
        # we generate an array with all the formatted responses
        with self._info_lock:
            return [self.generate_content(docker) for docker in self._containers_data] 

    """ sets the last received heartbeat for the manager activity management """
    def set_heartbeat(self, address) -> bool:
    
        with self._info_lock:
            self._logger.debug("Searching manager of " + address +" for heartbeat update")
            for docker in self._containers_data:
                if docker['address'] == address:
                    self._logger.debug("Container found")
                    docker['last_alive'] = datetime.now() + timedelta(minutes=5)
                    if docker['status'] == 'offline':
                        docker['status'] = 'update_present'
                        self._logger.debug("Changed manager status from offline to update_present")
                    return True
                
        self._logger.debug("Container not found")
        return False
    
    """ verifies if there are some pending updates and in case it unlock any eventual waiting thread """
    def verify_pending_updates(self):
        
        with self._info_lock:
            self._logger.debug("Verification of containers status")
            for docker in self._containers_data:
                if docker['status'] != 'update' and docker['status'] != 'offline':
                    self._logger.debug("Pending update found on manager " + docker['address'] + " with status "+docker['status'])
                    return
        self._result_ready.set()
       
    """ [ MAIN FUNCTIONALITIES ] """
    
    """ management of messages received by the controller. Supported functionalities: 
        - update containers 
        - heartbeat system
        - async containers management
    """
    def command_management(self, message) -> None:
        
        self._logger.debug("Received message from "+message['address'] +". Message type: " + message['command'])
        
        # heartbeat system. Periodically managers will send a live message to inform that they are active.
        # If no heartbeat messages are received in last 5 minutes the manager is defined as offline
        try:
            if message['command'] == 'live':
                self.set_heartbeat(message['address'])
                return
                
            if message['command'] == 'update':
                self.set_container_status_update_present(message['address'])
                return
        
            if message['command'] == 'content':
                self.set_container_content(message['address'], message['content'])
                self.verify_pending_updates()
                return
            if message['command'] == 'enable_test':
                self._enable_test = True
                return
            if message['command'] == 'disable_test':
                self._enable_test = False
                return
        except:
            self._logger.debug("Unable to understand the content of the request")
         
    def pending_manager(self) -> None:
        while True:
            self._logger.debug("Executing pending updates verification")
            with self._info_lock:
                for docker in self._containers_data:
                    if docker['status'] == 'update_present':
                        self._rabbit.send_manager_unicast(json.dumps({
                                    "command" : "give_content"
                        }), docker['address'])
            time.sleep(self._aggregation_time)
            
    def heartbeat_manager(self) -> None:
        while True:
            self._logger.debug("Executing hearbeat verification")
            with self._info_lock:
                for docker in self._containers_data:
                    if docker['last_alive'] < datetime.now():
                        docker['status'] = 'offline'
            
            self.verify_pending_updates()
            time.sleep(60)