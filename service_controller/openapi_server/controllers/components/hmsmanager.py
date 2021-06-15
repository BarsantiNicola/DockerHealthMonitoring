import socket
import docker
#import pika
from icmplib import ping, multiping, traceroute, resolve
from time import sleep

ignore_list = list()
set_threshold_val = int()

class manager_control:
    def __init__(self, container_id, threshold):
        self.container_id = container_id
        self.threshold = threshold

def callback(ch, method, properties, body): # RabbitMQ callback (recv.) - The message from the Queue must send a body of Class 'manager_control'    
    global ignore_list                      # The message contains the Threshold Value to be set and a container ID to be added to the Ignored List
    global set_threshold_val                                                                                                                       
    if body.container_id and (len(body.container_id) >= 12) : # check if received a container ID and if the size is correct
        if body.container_id in ignore_list: # check if inserted ID is on the ignored list - in this case REMOVE ID from the list
            idx = 0
            length = len(ignore_list)
            while (idx<length): # find where the ID is on the ignore_list and remove it
                if body.container_id == ignore_list[idx]:
                    ignore_list.pop(idx)
                idx += 1
        else : # the received ID is new - in this case ADD ID to the list
            ignore_list.append(body.container_id)          
    if ((body.threshold > 0) and (body.threshold < 1)):
        set_threshold_val = body.threshold
        

def main():
    global ignore_list
    global set_threshold_val
    print("Start Health Monitoring System")
    # obtain Manager IP addr
    manager_hostname = socket.gethostname()
    manager_ip = socket.gethostbyname(socket.gethostname())
    print ("Manager: ", manager_hostname, "[", manager_ip,"]")

    ignore_list = [] # ignored container list starts empty
    set_threshold_val = 0.1 # initial threshold value for reboot a container is 10% packet loss
    err_val = "ERR_OK"
    monitor_log_id = 0
    # TODO start RabbitMQ communication
 
    while(1):
        client = docker.from_env() # get Docker Host information
        client_env = docker.APIClient(base_url='unix://var/run/docker.sock') # get Docker environment information
        hms_container_list = [] # clear the list of monitored containers
        status_ctr = "active"
        monitor_log_id +=1
        print("\nMonitoring Log ID:", monitor_log_id) # used only as a reference value (if necessary can be used to store Monitoring Logs)
        for container in client.containers.list(all=True): # check all containers deployed            
            if not (container.short_id in ignore_list): # ignore listed containers
                if  container.status == "running": # container is running
                    ip_ctr = client_env.inspect_container(container.short_id)['NetworkSettings']['Networks']['bridge']['IPAddress'] # get container IP
                    if ip_ctr: # valid IP found
                        host = ping(ip_ctr, count=20, interval=0.01, timeout=0.1) # ping the container
                        if host.packet_loss >= set_threshold_val: # check Packet Loss and reboot the container if value is higher then the SET THRESHOLD
                            status_ctr = "reboot"
                            print(container.short_id, " rebooting...")
                            container.restart()
                        else :
                            status_ctr = "active" # if Packet Loss is OK
                        # Write monitoring LOG
                        container_desc = "< Container ID: "+container.short_id+" RUNNING >" + " IP addr:[" + ip_ctr + "]" # add ID and network param to String 
                        container_desc += " Pkt Loss =" + str(100*(host.packet_loss)) + "% (TS="+str(set_threshold_val)+")" # add Health param to String
                        container_desc += " Monitor Status: " + status_ctr # monitoring status: 'active' or 'reboot'
                        hms_container_list.append(container_desc)
                    else : # not found an IP addr
                        container_desc = "< Container ID: "+container.short_id+" RUNNING > [IP ERROR] Monitor Status: reboot" # if the container IP is not found
                        hms_container_list.append(container_desc)
                        print(container.short_id, " rebooting...")
                        container.restart()
                elif container.status == "exited": # container was stopped
                    container_desc = "< Container ID: "+container.short_id+" EXITED > Monitor Status: reboot" # if the container IP is not found
                    hms_container_list.append(container_desc)
                    print(container.short_id, " rebooting...")
                    container.restart()
            else :
                container_desc = "< Container ID: "+container.short_id+" > Monitor Status: ignored" # if container is ignored 
                hms_container_list.append(container_desc)
            
        for ctr_monitoring in hms_container_list:
            print(ctr_monitoring)
        #TODO send RabbitMQ msg (hms_container_list)
        sleep(1) # hold for 1 second before monitoring again
    
main()
