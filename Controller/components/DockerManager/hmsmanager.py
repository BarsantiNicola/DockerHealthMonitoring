import socket
import docker
#import pika
from icmplib import ping, multiping, traceroute, resolve
from time import sleep

def callback(ch, method, properties, body):    
    global ignore_list
    global set_threshold_val
    if body.docker_id and (len(body.docker_id) == 12) : # check if received a container ID and if the size is correct
        if body.docker_id in ignore_list: # check if inserted ID is on the ignored list - in this case REMOVE ID from the list
            idx = 0
            length = len(ignore_list)
            while (idx<length): # find where the ID is on the ignore_list and remove it
                if body.docker_id == ignore_list[idx]:
                    ignore_list.pop(idx)
                idx += 1
        else : # the received ID is new - in this case ADD ID to the list
            ignore_list.append(body.docker_id)          
    if ((body.threshold > 0) and (body.threshold < 1)):
        set_threshold_val = body.threshold


print("Start Health Monitoring System")
# obtain Manager IP addr
local_ip = socket.gethostbyname(socket.gethostname())
print ("Manager IP [", local_ip,"]")

ignore_list = [] # ignored container list starts empty
set_threshold_val = 0.1 # initial threshold value for reboot a container is 90% packet loss
err_val = "ERR_OK"

# TODO start RabbitMQ communication

monitor_log_id = 0
while(1):
    client = docker.from_env()
    client_env = docker.APIClient(base_url='unix://var/run/docker.sock')
    hms_container_list = []
    status_ctr = "active"
    monitor_log_id +=1
    print("\nMonitoring Log ID:", monitor_log_id) # used only as a reference value (if necessary can be used to store Monitoring Logs)
    for container in client.containers.list(): # check all ACTIVE containers
        if not (container.short_id in ignore_list):    # ignore listed containers
            ip_ctr = client_env.inspect_container(container.short_id)['NetworkSettings']['Networks']['bridge']['IPAddress'] # get container IP
            if ip_ctr:
                host = ping(ip_ctr, count=20, interval=0.01) # ping the container
                if host.packet_loss > set_threshold_val: # check Packet Loss
                    status_ctr = "reboot"
                    print(container.short_id, " rebooting...")
                    container.restart()
                else :
                    status_ctr = "active"
                container_desc = "< Container ID: "+container.short_id+" >" + " IP addr:[" + ip_ctr + "]" # add ID and network param to String 
                container_desc += " Pkt Loss =" + str(100*(host.packet_loss)) + "% (TS="+str(set_threshold_val)+")" # add Health param to String
                container_desc += " Monitor Status: " + status_ctr
                hms_container_list.append(container_desc)
            else :
                container_desc = "< Container ID: "+container.short_id+" > Monitor Status: not active / network error"
                hms_container_list.append(container_desc)
        else :
            container_desc = "< Container ID: "+container.short_id+" > Monitor Status: ignored"
            hms_container_list.append(container_desc)
    
    for ctr_monitoring in hms_container_list:
        print(ctr_monitoring)
    #TODO send RabbitMQ msg (hms_container_list)
    sleep(1) # hold for 1 second before monitoring again
    
