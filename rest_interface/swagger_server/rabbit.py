import ipaddress
import socket
import threading
import pika
import random
import string
import json
import logging
import coloredlogs
import sys
from datetime import datetime
from datetime import timedelta

def test(message):
    return message
    
class rabbit_client:

    """ initialize the rabbit_client class
        Parameters:
            - address: the Ipv4 address of a rabbitMQ instance
            - receiver_type: type of module which use the rabbit_client(antagonist, manager, controller, interface)
            - responses: a dictionary of all the command which the client must respond connected with a function to be invoked
                         ex: { 'test': test, 'give_content': get_data }
                         all the functions must get as a parameter only a dictionary(the message received)
    """
    
    def __init__(self, address, receiver_type, responses):
        
        # connections used. If we don't use different connections sometime they make some interference
        self._send_connection = None
        self._callback_connection = None
        self._receive_connection = None
        
        # channels used
        self._send_channel = None
        self._receive_channel = None
        self._callback_channel = None
        
        # used for sync communications
        self._responses = {}
        
        # address of the client
        self._address = address
        
        # type of receiver
        self._receiver_type = receiver_type
        
        # maximum waiting time for a reply
        if receiver_type == 'controller':
            self._waiting_time = timedelta(seconds=30)
        elif receiver_type == 'manager':
            self._waiting_time = timedelta(seconds=10)
        elif receiver_type == 'interface':
            self._waiting_time = timedelta(seconds=60)
        else:
            self._waiting_time = timedelta(seconds=15)
        # lock for mutual exclusion on _responses
        self._responses_lock = threading.Lock()   
        
        # dictionary of all the command to response linked with a function
        self._responses = responses
        self._logger = None
            
        self._initialize_logger()   # initialization of the logger
        self._generate_channel()    # generation of the rabbitMQ channels
        self._allocate_receiver()  # allocation of thread for message receival

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

    # PRIVATE FUNCTIONS

    """ verification of an IPv4 address """
    @staticmethod
    def _validate_address(address) -> bool:
        try:
            ipaddress.ip_address(address)
            return True
        except ValueError:
            return False

    """ it generates the connections with the rabbitMQ broker and generate the channel for the message listening """
    def _generate_channel(self) -> bool:
        
        self._logger.debug("Starting verification of IPv4 address")
        if self._address is None or self._validate_address(self._address) is False:
            self._logger.error("Error, invalid IPv4 address detected")
            return False
        self._logger.debug("IPv4 address verification completed")
        
        try:
            self._logger.debug("Starting creation of connections to rabbitMQ message broker")
            credentials = pika.PlainCredentials('health-monitor', 
                                                '2a55f70a841f18b97c3a7db939b7adc9e34a0f1b')
            parameters = pika.ConnectionParameters(self._address,
                                       5672,
                                       '/',
                                       credentials)
            self._send_connection = pika.BlockingConnection(parameters)
            self._callback_connection = pika.BlockingConnection(parameters)
            self._receive_connection = pika.BlockingConnection(parameters)
            self._send_channel = self._send_connection.channel()
            self._send_channel.exchange_declare(exchange='health_system_exchange', exchange_type='direct',
                                            arguments={'x-message-ttl' : 0})
            self._logger.debug("Connections correctly generated")
            return True

        except:
            self._logger.error("An error has occurred during the connection generation")
            self._send_connection = None
            self._callback_connection = None
            self._receive_connection = None
            self._send_channel = None
            return False

    """ verifies if the reply of a request has been received using a correlationID associated with the request """
    def _check_result(self, correlation_id) -> bool:
        try:
            with self._responses_lock:
                self._responses[correlation_id]
            return True
        except KeyError: # if the key isn't present it will raise a KeyError
            return False
    
    """ takes the reply of a request basing on a correlationID associated with the request """
    def _get_result(self, correlation_id):
        try:
            with self._responses_lock:
                self._logger.debug("RESPONSE: " + json.dumps(self._responses[correlation_id]))
                value = self._responses[correlation_id]
                del self._responses[correlation_id]
                return value
        except KeyError: # if the key isn't present it will raise a KeyError
            return None
    
    """ adds the reply of a request to the archive """
    def _add_result(self, correlation_id, value):
        #with self._responses_lock:
        self._responses[correlation_id] = str(value)
        
    """ MESSAGE RECEIVAL MANAGEMENT """

    """ allocate receiving queue and start them on threads """
    def _allocate_receiver(self) -> bool:
        
        # this is a one-pass function. It can be used only one time
        if self._receive_channel is not None:
            return False
        
        try:
            self._logger.debug("Starting generation of receiving channels")
            self._receive_channel = self._receive_connection.channel()
            self._callback_channel = self._callback_connection.channel()
            self._logger.debug("Channels correctly instantiated")
            self._logger.debug("Starting queues generation")
            result = self._receive_channel.queue_declare(queue='', exclusive=True)
            queue_name = result.method.queue
            
            result2 = self._callback_channel.queue_declare(queue='', exclusive=True)
            callback_queue = result2.method.queue
            self._logger.debug("Queues correctly instantiated")
            self._logger.debug("Executing queues binding to the exchange")
            self._receive_channel.queue_bind(exchange='health_system_exchange',
                                            queue=queue_name,
                                            routing_key=self._receiver_type,
                                                arguments={'x-message-ttl' : 0})

            if self._receiver_type == 'interface':
                self._receive_channel.queue_bind(exchange='health_system_exchange',queue=queue_name,routing_key=self._receiver_type + '.' + self._address,arguments={'x-message-ttl' : 0})
            
                self._callback_channel.queue_bind( exchange='health_system_exchange',
                                               queue=callback_queue,
                                               routing_key=self._receiver_type+'.callback.'+ self._address,
                                                   arguments={'x-message-ttl' : 0})
            else:    
                self._receive_channel.queue_bind(exchange='health_system_exchange',
                                            queue=queue_name,
                                            routing_key=self._receiver_type + '.' + socket.gethostbyname(socket.gethostname()),
                                                arguments={'x-message-ttl' : 0})
            
                self._callback_channel.queue_bind( exchange='health_system_exchange',
                                               queue=callback_queue,
                                               routing_key=self._receiver_type+'.callback.'+ socket.gethostbyname(socket.gethostname()),
                                               arguments={'x-message-ttl' : 0})
            
            self._logger.debug("Allocated channels: " + self._receiver_type + " : " + self._receiver_type+"."+self._address + " : callback." + self._receiver_type + "." + self._address)
            self._callback_channel.basic_consume(queue=callback_queue, on_message_callback=self._on_response, auto_ack=True)
            self._receive_channel.basic_consume(queue=queue_name, on_message_callback=self._message_callback, auto_ack=True)
            self._logger.debug("Queues correctly binded")
            self._logger.debug("Allocating thread and start message consuming")
            threading.Thread(target=self._callback_channel.start_consuming, daemon=True).start()
            threading.Thread(target=self._receive_channel.start_consuming, daemon=True).start()
            self._logger.debug("Receiving queues fully operational")
            return True
        
        except:
            self._logger.error("An error has occurred during the generation of the receiving queues")
            self._receive_channel = None
            self._callback_channel = None
            return False

    """ callback function called by the queues for the management of the incoming messages """
    def _message_callback(self, ch, method, props, body):
        
        # messages are JSON encoded
        message = json.loads(body)
        try:  # verification of the mandatory fields
            message['sender']
            message['command']
        except KeyError:
            self._logger.warning('Error, the incoming message not have the mandatory field command and sender. Abort operation')
            return
        
        # this is an information used by the client, not to be shared outside
        sender = message['sender']
        del message["sender"]
        if props.correlation_id is None:
            self._logger.info("New async message received. Type: "+ message['command'])
        else:
            self._logger.info("New message received. Type: " + message['command'] + " Id: "+ props.correlation_id)
        try:
            response = self._responses[message['command']](message) # we use a set of given command -> response
            if props.correlation_id is None:
                self._logger.info("Management of request " + message['command'] +" completed")
                return
            else:    
                self._logger.info("Request " + props.correlation_id + " completed")
        except KeyError:
            if props.correlation_id is None:
                self._logger.error("Error on received request, type not supported: " + message['command'])
                return
            else:
                self._logger.error("Error on received request " + props.correlation_id + ": request type not supported: " + message['command'])
                response = {'command':'error', 'message':'command not found'}
        
        self._logger.debug("Sending the computed reply to " + sender)
        self._send_channel.basic_publish(exchange='health_system_exchange',
                     routing_key= sender,
                     properties=pika.BasicProperties(correlation_id = \
                                                         props.correlation_id),
                     body=json.dumps(response))
        self._logger.debug("Computed reply sent")           

    """ callback function called by the callback queue for the management of the incoming replies """
    def _on_response(self, ch, method, props, body):
        self._logger.debug("Received reply to request " + props.correlation_id)
        self._add_result(props.correlation_id, json.loads(body))
        
    """ MESSAGE SENDERS"""
    
    """ send a unicast message to an antagonist
        Parameters:
            message(dict): the message to be sent
            address(str):  the IPv4 address of the host
            reply(bool): to not be used. Its used by the system
            
        Return(dict): the reply to the request
    """
    def send_antagonist_unicast(self, message, address, reply=True) -> dict:
        
        self._logger.debug("Starting verification of environment")
        if self._address is None or message is None or address is None:
            self._logger.error("Error, the given parameters cannot be None")
            return {'command':'error', 'message':'internal error', 'type':'internal_error'}

        if self._send_connection is None and self._generate_channel() is False:
            self._logger.error("Error, client not connected")
            return {'command':'error', 'message':'internal error', 'type':'internal_error'}
        self._logger.debug("Environment verification succeded")
        
        try:
            
            correlation_id = ''.join(random.choices(string.ascii_uppercase +
                    string.digits, k = 10))
            self._logger.debug("Sending request " + correlation_id)
            message['sender'] =self._receiver_type+'.callback.' + socket.gethostbyname(socket.gethostname())
            self._send_channel.basic_publish(exchange='health_system_exchange', routing_key='antagonist.' + address,
                                        properties=pika.BasicProperties(
                                                correlation_id=correlation_id
                                        ),
                                        body=json.dumps(message))
            self._logger.debug("Request " + correlation_id + " sent. Waiting reply")
            
            expire = datetime.now() + self._waiting_time             
            while self._check_result(correlation_id) is False and expire > datetime.now():
                self._receive_connection.process_data_events()
            
            if expire < datetime.now():
                self._logger.error("Destination antagonist at " + address +" unreachable")
                return {'command':'error', 'message':'destination unreachable', 'type':'unreachable'}
            
            self._logger.debug("Reply to request " + correlation_id + " received")    
            return self._get_result(correlation_id)
        
        except:
            if reply is True:
                self._logger.warning("Temporary disconnection from the broker. Trying reconnection..")
                self._generate_channel()
                return self.send_antagonist_unicast(message, address, False)
         
        self._logger.error("Error. Unable to contact the broker. Connection down")
        return {}

    """ send a unicast message to a manager
        Parameters:
            message(dict): the message to be sent
            address(str):  the IPv4 address of the host
            reply(bool): to not be used. Its used by the system
            
        Return(dict): the reply to the request
    """
    def send_manager_unicast(self, message, address, reply=True) -> bool:

        self._logger.debug("Starting verification of environment")
        if self._address is None or message is None or address is None:
            self._logger.error("Error, the given parameters cannot be None")
            return {'command':'error', 'message':'internal error', 'type':'internal_error'}

        if self._send_connection is None and self._generate_channel() is False:
            self._logger.error("Error, client not connected")
            return {'command':'error', 'message':'internal error', 'type':'internal_error'}
        self._logger.debug("Environment verification succeded")
        try:
            correlation_id = ''.join(random.choices(string.ascii_uppercase +
                    string.digits, k = 10))
            self._logger.debug("Sending request " + correlation_id)
            message['sender'] =self._receiver_type+'.callback.' + socket.gethostbyname(socket.gethostname())
            self._send_channel.basic_publish(exchange='health_system_exchange', routing_key='manager.' + address,
                                            properties=pika.BasicProperties(
                                                    correlation_id=correlation_id
                                            ),
                                            body=json.dumps(message))

            expire = datetime.now() + self._waiting_time         
            while self._check_result(correlation_id) is False and expire > datetime.now():
                self._receive_connection.process_data_events()
            
            if expire < datetime.now():
                self._logger.error("Destination manager at " + address +" unreachable")
                return {'command':'error', 'message':'destination unreachable', 'type':'unreachable'}
            
            self._logger.debug("Reply to request " + correlation_id + " received")   
            return self._get_result(correlation_id)
        
        except:
            if reply is True:
                self._logger.warning("Temporary disconnection from the broker. Trying reconnection..")
                self._generate_channel()
                return self.send_manager_unicast(message, address, False)

    """ send a multicast message to the antagonists. To be used from the managers to 
        generate an asynchronous notification of updates to the controller 
        Parameters:
            reply(bool): to not be used. Its used by the system
            alive(bool): identifies the type of message to be sent. If true(default) it sends
                         a keepalive message otherwise a message notification message
                         
        Return(bool): define if the request is sent or not   
    """
    def send_controller_async(self, alive=True, reply=True) -> bool:

        if self._address is None:
            return False

        if self._send_connection is None and self._generate_channel() is False:
            return False
        try:
            if alive is True:
                message = {'command':'live', 'address': socket.gethostbyname(socket.gethostname())}
                message['sender'] =self._receiver_type+'.callback.' + socket.gethostbyname(socket.gethostname())
            else:
                message = {'command':'update', 'address': socket.gethostbyname(socket.gethostname())}
                message['sender'] =self._receiver_type+'.callback.' + socket.gethostbyname(socket.gethostname())
            self._send_channel.basic_publish(exchange='health_system_exchange', routing_key='controller', body=json.dumps(message))
            return True
        except:
            if reply is True:
                self._generate_channel()
                return self.send_controller_async(message, False)
            return False
        
    """ send a sync message to a controller
        Parameters:
            message(dict): the message to be sent
            address(str):  the IPv4 address of the host
            reply(bool): to not be used. Its used by the system
            
        Return(dict): the reply to the request
    """
    def send_controller_sync(self, message, address, reply=True) -> bool:

        self._logger.debug("Starting verification of environment")
        if self._address is None or message is None or address is None:
            self._logger.error("Error, the given parameters cannot be None")
            return {'command':'error', 'message':'internal error', 'type':'internal_error'}

        if self._send_connection is None and self._generate_channel() is False:
            self._logger.error("Error, client not connected")
            return {'command':'error', 'message':'internal error', 'type':'internal_error'}
        self._logger.debug("Environment verification succeded")
        try:
            correlation_id = ''.join(random.choices(string.ascii_uppercase +
                    string.digits, k = 10))
            self._logger.debug("Sending request " + correlation_id + " to controller."+address)
            message['sender'] =self._receiver_type+'.callback.' + self._address
            try:
                self._send_channel.basic_publish(exchange='health_system_exchange', routing_key='controller.' + address,
                                            properties=pika.BasicProperties(
                                                    correlation_id=correlation_id
                                            ),
                                            body=json.dumps(message))
            except ValueError:
                self._logger.error("Error, invalid message given. It must be a dictionary")
                return {'command':'error', 'message':'invalid parameters'}
            
            expire = datetime.now() + self._waiting_time              
            while self._check_result(correlation_id) is False and expire > datetime.now():
                self._receive_connection.process_data_events()
            
            if expire < datetime.now():
                self._logger.error("Destination controller at " + address +" unreachable")
                return {'command':'error', 'message':'destination unreachable', 'type':'unreachable'}
                
        except:
            if reply is True:
                self._logger.warning("Temporary disconnection from the broker. Trying reconnection..")
                self._generate_channel()
                return self.send_controller_sync(message, address, False)        
            return "ERROR"
        
        self._logger.debug("Reply to request " + correlation_id + " received")   
        return self._get_result(correlation_id)
        

            
        self._logger.error("Error. Unable to contact the broker. Connection down")
        return {'command':'error', 'message':'internal error', 'type':'internal_error'}

        
