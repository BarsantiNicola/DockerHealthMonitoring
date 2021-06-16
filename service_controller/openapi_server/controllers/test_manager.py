#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Jun 15 22:23:13 2021

@author: nico
"""
import time
import json
from numpy.random import exponential
import threading

from rabbit import client
class tester:
    
    def test_callback(self, method, properties, x,body):
        message = json.loads(body)
        if message['command'] == 'give_content':
            print("update request received")
            self.rabbit.send_controller(json.dumps({
                    'command' : 'content',
                    'content' : 'data',
                    'address' : '127.0.0.1'
                    }))
        
    def __init__(self, address):
        self.rabbit = client(address)
        self.rabbit.allocate_receiver('manager',self.test_callback)
        self.start_execution()
    
    def start_execution(self):
        self.rabbit.send_controller(json.dumps({
                    'command' : 'started',
                    'address' : '127.0.0.1'
                    }))
        threading.Thread(target=self.heartbeat).start()
        while True:
            time.sleep(exponential(60))
            print("send update")
            self.rabbit.send_controller(json.dumps({
                    'command' : 'update',
                    'address' : '127.0.0.1'
                    }))
    
    def heartbeat(self):
        while True:
            time.sleep(60)
            print('send heartbeat')
            self.rabbit.send_controller(json.dumps({
                    'command' : 'alive',
                    'address' : '127.0.0.1'
                    }))
            