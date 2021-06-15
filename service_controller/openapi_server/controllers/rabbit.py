import ipaddress
import socket
import threading
import pika


class client:

    def __init__(self, address):
        self.send_connection = None
        self.receive_connection = None
        self.send_channel = None
        self.receive_channel = None
        self.address = address
        self.generate_channel()

    # PRIVATE FUNCTIONS

    # verify an address is present and defined in the form x.x.x.x
    @staticmethod
    def validate_address(address) -> bool:
        try:
            ipaddress.ip_address(address)
            return True
        except ValueError:
            return False

    # generate a channel to the rabbitMQ instance
    def generate_channel(self) -> bool:

        if self.address is None:
            return False
        try:
            self.send_connection = pika.BlockingConnection(pika.ConnectionParameters(self.address))
            self.receive_connection = pika.BlockingConnection(pika.ConnectionParameters(self.address))
            self.send_channel = self.send_connection.channel()
            self.send_channel.exchange_declare(exchange='health_system_exchange', exchange_type='direct')
            return True

        except:
            self.send_connection = None
            self.send_channel = None
            return False

    # [MAYBE TO BE REMOVED] change the address used to reach the rabbitMQ instance
    def change_address(self, address) -> bool:

        if address is None:
            return False

        if self.send_connection is not None:
            self.send_connection.close()

        self.address = address
        return self.generate_channel()

    # send a unicast message to an antagonist. The hostname must be the hostname of the local selected machine
    def send_antagonist_unicast(self, message, address, reply=True) -> bool:

        if self.address is None or message is None or hostname is None:
            return False

        if self.send_connection is None and self.generate_channel() is False:
            return False
        try:
            self.send_channel.basic_publish(exchange='health_system_exchange', routing_key='antagonist.' + address,
                                            body=message)
            return True
        except:
            if reply is True:
                self.generate_channel()
                return self.send_antagonist_unicast(message, hostname, False)
            return False

    # send a broadcast message to all the antagonists
    def send_antagonist_multicast(self, message, reply=True):

        if self.address is None or message is None:
            return False

        if self.send_connection is None and self.generate_channel() is False:
            return False
        try:
            self.send_channel.basic_publish(exchange='health_system_exchange', routing_key='antagonist', body=message)
            return True
        except:
            if reply is True:
                self.generate_channel()
                return self.send_antagonist_multicast(message, False)
            return False

    # send a unicast message to a manager. The hostname must be the hostname of the local selected machine
    def send_manager_unicast(self, message, address, reply=True) -> bool:

        if self.address is None or message is None or hostname is None:
            return False

        if self.send_connection is None and self.generate_channel() is False:
            return False
        try:
            self.send_channel.basic_publish(exchange='health_system_exchange', routing_key='manager.' + address,
                                            body=message)
            return True
        except:
            if reply is True:
                self.generate_channel()
                return self.send_manager_unicast(message, hostname, False)
            return False

    # send a broadcast message to all the docker managers
    def send_manager_multicast(self, message, reply=True) -> bool:

        if self.address is None or message is None:
            return False

        if self.send_connection is None and self.generate_channel() is False:
            return False
        try:
            self.send_channel.basic_publish(exchange='health_system_exchange', routing_key='manager', body=message)
            return True
        except:
            if reply is True:
                self.generate_channel()
                return self.send_manager_multicast(message, False)
            return False

    # send a message to the controller
    def send_controller(self, message, reply=True) -> bool:

        if self.address is None or message is None:
            return False

        if self.send_connection is None and self.generate_channel() is False:
            return False
        try:
            self.send_channel.basic_publish(exchange='health_system_exchange', routing_key='controller', body=message)
            return True
        except:
            if reply is True:
                self.generate_channel()
                return self.send_controller(message, False)
            return False

    # set a policy to receive message and set a thread to execute a callback function when new messages arrive
    # receiver_type: antagonist,manager,controller
    # callback_fun: function to be called whena message arrive
    def allocate_receiver(self, receiver_type, callback_fun) -> bool:
        if self.receive_channel is not None:
            return False
        try:
            self.receive_channel = self.receive_connection.channel()
            result = self.receive_channel.queue_declare(queue='', exclusive=True)
            queue_name = result.method.queue

            self.receive_channel.queue_bind(exchange='health_system_exchange',
                                            queue=queue_name,
                                            routing_key=receiver_type)

            self.receive_channel.queue_bind(exchange='health_system_exchange',
                                            queue=queue_name,
                                            routing_key=receiver_type + '.' + socket.gethostbyname(socket.gethostname()))
            self.receive_channel.basic_consume(queue=queue_name, on_message_callback=callback_fun, auto_ack=True)
            threading.Thread(target=self.receive_channel.start_consuming).start()
            return True
        except:
            self.receive_channel = None
            return False

    # example of valid callback function to be used into the allocate_receiver[TO BE DEFINED OUTSIDE RABBITCLIENT]
    @staticmethod
    def callback_example(method, properties, x, body):
        print(" [x] Received %r" % body)
