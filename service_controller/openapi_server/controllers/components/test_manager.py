#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Jun 15 22:23:13 2021

@author: nico
"""
import time
import json
import threading
import socket

from rabbit import client

    
class tester:
    
    def test_callback(self, method, properties, x,body):
        message = json.loads(body)
        if message['command'] == 'give_content':
            self.rabbit.send_controller(json.dumps({
                    'command' : 'content',
                    'content' : 'data',
                    'address' : socket.gethostbyname(socket.gethostname())
                    }))
        
    def __init__(self):
        self._configuration = None
        if self.load_conf() is True:
            self.rabbit = client(self._configuration['address'])
            self.rabbit.allocate_receiver('manager',self.test_callback)
            self.start_execution()

    
    def start_execution(self):
        threading.Thread(target=self.heartbeat).start()
        while True:
            time.sleep(100)
            print("send update")
            self.rabbit.send_controller(json.dumps({
                    'command' : 'update',
                    'address' : socket.gethostbyname(socket.gethostname())
                    }))
    
    def heartbeat(self):
        while True:
            time.sleep(60)
            print('send heartbeat')
            self.rabbit.send_controller(json.dumps({
                    'command' : 'live',
                    'address' : socket.gethostbyname(socket.gethostname())
                    }))
       
    def load_conf(self) -> bool:
        
        try:
            # file is putted inside the same folder of the script
            with open('configuration','r') as reader:
                # the content is organized as a json file
                self._configuration = json.load(reader)
                return True
            
        except ValueError:
            print("Error, invalid configuration file")
            return False
        except FileNotFoundError:
            print("Error, configuration file not found")
            return False
 
print("launching!")       
tester()