 from icmplib import ping
 
 print("begin test")
 
 
 host = ping('172.17.0.2', src_addr='172.17.0.3', count=10, interval=0.2)
 
 print(host.transmitted_packets)
 print(host.received_packets)
 
 print("end test")
