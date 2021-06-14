from rabbit import client
import json
import os
import paramiko
import threading

class controller:
    
    def controller_callback(self, method, properties, x, body):
        self.command_management(json.dumps(body))
        
    def __init__(self):
        self.configuration = None
        self.rabbit = None
        self.dockers = []
        self.containers_data = []
        self.result_ready = threading.Event()
        self.docker_lock = threading.Lock()
        self.info_lock = threading.Lock()
        self.update_available = False
        
        if self.load_conf() is False:
            return None
        if self.init_rabbit() is False:
            return None
        self.load_data()
        print("Controller initialization completed")    
        
    def load_conf(self) -> bool:
        try:
            with open('configuration','r') as reader:
                self.configuration = json.load(reader)
                return True
        except ValueError:
            print("Error, configuration file corrupted")
            return False
        except FileNotFoundError:
            print("Error, configuration file not found")
            return False
    
    def load_data(self):
        try:
            with open('data','rb') as reader:
                self.dockers = json.load(reader)
            for docker in self.dockers:
                self.containers_data.append({
                        'address' : docker['address'],
                        'update' : '',
                        'status' : 'unknown'})
        except FileNotFoundError:
            print("Data stored not found")
        except ValueError:
            print("Error, stored data corrupted. Data not loaded")

            
    def save_data(self) -> bool:
        with open('data','wb') as writer:
            try:
                writer.write(bytes(json.dumps(self.dockers),'utf-8'))
                return True
            except ValueError:
                print("Data saved")
                return False 
            
    def init_rabbit(self) -> bool:
        try:
            self.rabbit = client(self.configuration['address'])
            if self.rabbit is not None:
                self.rabbit.allocate_receiver('controller', self.controller_callback)
                return True
            
        except KeyError:
            print('Error, address field not found')
            
        return False 
    
    def verify_docker_presence(self, address) -> bool:
        for docker in self.dockers:
            if docker['address'] == address:
                return True
        return False

    def remove_docker(self, address) -> bool:
        for docker in self.dockers:
            if docker['address'] == address:
                self.dockers.remove(docker)
                return True
            return False
        
    def command_management(self, message) -> None:
        if message['command'] == 'started':
            self.containers_data.append({
                    'address' : message['address'],
                    'update' : '',
                    'status' : 'unknown'})
            return
        
        if message['command'] == 'updated':
            if self.updateSemaphore is True:
                self.request_container_content(message['address'])
            else:    
                self.set_container_status(message['address'], 'update_present')
            return
        
        if message['command'] == 'update':
            self.set_container_content(message['address'], message['update'])
            self.verify_pending_updates()
            return
        
    def load_docker_manager(self, address, password) -> bool:

        if self.verify_docker_presence(address) is False:   
            try:
                self.generate_configuration(address)
                ssh = paramiko.SSHClient() 
                ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                ssh.load_host_keys(os.path.expanduser(os.path.join("~", ".ssh", "known_hosts")))
                ssh.connect(address, username='root', password=password)
                sftp = ssh.open_sftp()
                print('connected, load data')
                try:
                    sftp.mkdir('/root/health_manager')
                    for item in os.listdir('components'):
                        sftp.put('components/'+item,'/root/health_manager/'+item)
                except OSError:
                    print('Folder already present')
                print('put components')
                sftp.put('docker-health-monitor.service','/etc/systemd/system/docker-health-monitor.service')
                print('put service')
                sftp.close()
                ssh.exec_command('chmod 0777 /etc/systemd/system/docker-health-monitor.service')
                #ssh.exec_command('service docker-health-monitor start')
                ssh.close()
                self.dockers.append(
                        {
                                'address': address,
                                'password': password
                        })
            except:
                print('Error during the machine connection. Abort operation')
                return False
            return self.save_data()
        return False
    
    def generate_configuration(self, address):
        with open('components/configuration','w') as writer:
            writer.write(address)
            
    def remove_docker_manager(self, address) -> bool:
        with self.docker_lock:
            if self.verify_docker_presence(address) is True: 
                try:
                    ssh = paramiko.SSHClient() 
                    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                    ssh.load_host_keys(os.path.expanduser(os.path.join("~", ".ssh", "known_hosts")))
                    ssh.connect(address, username='root', password=self.get_docker_password(address))
                    #ssh.exec_command('service docker-health-monitor stop')
                    ssh.exec_command('rm /etc/systemd/system/docker-health-monitor.service')
                    ssh.exec_command('rm -R /root/health_manager')
                    ssh.close()
                    self.remove_docker(address)
                    return self.save_data()
                except:
                    print('Error during the removal of the manager service')
        return False
        
    def get_docker_password(self, address) -> str:
        for docker in self.dockers:
            if docker['address'] == address:
                return docker['password']
            return ''    
    
    def get_container_status(self, address) -> str:
        with self.info_lock:
            for docker in self.containers_data:
                if docker['address'] == address:
                    return docker['status']
                return ''
    
    def set_container_status(self, address, status) -> bool:
        with self.info_lock:
            for docker in self.containers_data:
                if docker['address'] == address:
                    docker['status'] = status
                    return True
                return False
    
    def set_container_content(self, address, content) ->bool:
        with self.info_lock:
            for docker in self.containers_data:
                if docker['address'] == address:
                    docker['content'] = content
                    docker['status'] = 'updated'
                    return True
                return False   
    
    def request_container_content(self, address=None) -> bool:
        if address is None:
            return self.rabbit.send_manager_multicast(json.dumps({"command": 'give_content'}))
        return self.rabbit.send_antagonist_unicast(json.dumps({"command": 'give_content'}),address)
        
    def get_containers_content(self) -> list:
        with self.info_lock:
            self.update_available = False
            for docker in self.containers_data:
                if docker['status'] != 'updated':
                    self.request_container_content(docker['address'])
                    self.update_available = True
        if self.update_available is True:
            self.result_ready.wait()

        with self.info_lock:
            return [{ "address" : docker['address'], "content" : docker['content']} for docker in self.dockers]        
    
    
    def verify_pending_updates(self) -> bool:
        with self.info_lock:
            for docker in self.containers_data:
                if docker['status'] != 'updated':
                    return False
            if self.update_available == True:
                self.update_available = False
                self.result_ready.set()
            return True            
