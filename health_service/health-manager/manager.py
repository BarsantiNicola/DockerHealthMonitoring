import socket
import docker
import threading
from icmplib import ping
from time import sleep
from rabbit import rabbit_client

ignore_list = list() # global variable used to store ignored containers IDs
threshold_val = int() # global variable used to store the Threshold value for Packet Loss reboot protocol
monitor_log = list() # global variable used to store updated containers information

def get_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('8.8.8.8', 1))
        IP = s.getsockname()[0]
    except Exception:
        IP = '127.0.0.1'
    finally:
        s.close()
    return IP


def ignore (message):
    global ignore_list
    container_id = message["containerID"]
    if container_id and (len(container_id) >= 12) : # check if received a container ID and if the size is correct
        if not container_id in ignore_list: # check if inserted ID is not already inserted in the list - in this case ADD ID to the list
            ignore_list.append(container_id) # add container to the ignored list
    print("< ", container_id, " > Added to ignore list")

    
def remove (message):
    global ignore_list
    container_id = message["containerID"]
    if container_id and (len(container_id) >= 12) : # check if received a container ID and if the size is correct
        if container_id in ignore_list: # check if inserted ID is on the ignored list - in this case REMOVE ID from the list
            idx = 0
            length = len(ignore_list)
            while (idx<length): # find where the ID is on the ignore_list and remove it
                if body.container_id == ignore_list[idx]:
                    ignore_list.pop(idx)
                idx += 1
    print("< ", container_id, " > Removed from ignore list")    


def threshold (message):
    global threshold_val
    th = body["threshold"]
    if th > 0 and th < 1 :    
        threshold_val = th
    print("Set Pkt Loss threshold to ", th)


def monitor_list (message):
    global monitor_log
    global manager_ip
    global comm_client
    msg = { "command" : "give_content", "address" : manager_ip, "data": monitor_log }
    comm_client.send_controller_sync(msg, manager_ip)
    for log in monitor_log:
        print(log)
        

# get Manager information
manager_hostname = socket.gethostname()
manager_ip = get_ip()
print ("Manager: ", manager_hostname, "[", manager_ip,"]")

# Health monitoring system control variables
ignore_list = [] # ignored container list starts empty
threshold_val = 0.1 # initial threshold value - reboot every container that has a higher or equal packet packet loss value

# create RabbitMQ conection
comm_client = rabbit_client('172.17.0.2', 'manager',{'container_ignore': ignore, 'container_rmv_ignore': remove, 'container_threshold': threshold, 'give_content': monitor_list})
 
msg = {
    "command" : "alive",
    "address" : manager_ip    
}
comm_client.send_controller_sync(msg, manager_ip)

print("Health Monitoring System ON")       

      
def execute_monitor ():
    global ignore_list
    global threshold_val
    global monitor_log
    client = docker.from_env() # get Docker Host information
    client_env = docker.APIClient(base_url='unix://var/run/docker.sock') # get Docker environment information
    current_log = [] # start a new log
    update = 0 # clear update flag
    for container in client.containers.list(all=True) : # list all deployed containers        
        if not (container.short_id in ignore_list) : # check containers that are NOT on the ignored list
            if  container.status == "running" :
                ip_ctr = client_env.inspect_container(container.short_id)['NetworkSettings']['Networks']['bridge']['IPAddress'] # get container IP    
                if ip_ctr : # valid IP found
                    host = ping(ip_ctr, count=20, interval=0.01, timeout=0.1) # ping the container
                    container_desc = "<"+container.short_id+"> <"+str(container.image)+"> RUNNING"+" ["+ip_ctr + "]"+" [Pkt Loss ="+str(100*(host.packet_loss))+"%] "
                    if host.packet_loss < threshold_val : # check Packet Loss
                        container_desc += "[HMS: ACTIVE]" 
                    else : # Exceeded threshold value
                        container_desc += "[Threshold Exceeded] [HMS: RESTART]"
                        container.restart()
                        update = 1
                else : # invalid IP addr
                    container_desc = "<"+container.short_id+"> <"+str(container.image)+"> RUNNING"+" [Network error] [HMS: RESTART]"
                    container.restart()
                    update = 1
            elif container.status == "exited" : # container was shut down       
                container_desc = "<"+container.short_id+"> <"+str(container.image)+"> EXITED"+" [HMS: RESTART]"
                container.restart()
                update = 1
        elif container.short_id in ignore_list : # container is on the ignored list            
            container_desc = "<"+container.short_id+"> <"+str(container.image)+">"+" [HMS: IGNORED]"

        current_log.append(container_desc) # add the container description to the log
    
    monitor_log = current_log # update the monitor log
    return update


def start_manager ():
    global comm_client
    global monitor_log
    global manager_ip
    n = 0
    alive_freq = 0
    while (1):
        n +=1
        print("\nmonitoring log n:",n)
        update_ret = execute_monitor()
        
        if update_ret == 1 :                     
            comm_client.send_controller_async(alive=False) # update message to the controller            
        
        for log in monitor_log:
            print(log)
        
        alive_freq +=1
        if alive_freq >=10:
            comm_client.send_controller_async() # alive message to the controller every ~20 seconds
            alive_freq=0
        
        sleep(2)

manager = threading.Thread(target=start_manager)
manager.start()


