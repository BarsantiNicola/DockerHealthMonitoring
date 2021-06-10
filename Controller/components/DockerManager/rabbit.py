import ipaddress
import socket
import threading
import pika


class client:

    def __init__(self, address):
        self.connection = None
        self.channel = None
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
            self.connection = pika.BlockingConnection(pika.ConnectionParameters(self.address))
            self.channel = self.connection.channel()
            self.channel.exchange_declare(exchange='health_system_exchange', exchange_type='direct')
            return True

        except:
            self.connection = None
            self.channel = None
            return False

    # [MAYBE TO BE REMOVED] change the address used to reach the rabbitMQ instance
    def change_address(self, address) -> bool:

        if address is None:
            return False

        if self.connection is not None:
            self.connection.close()

        self.address = address
        return self.generate_channel()

    # send a unicast message to an antagonist. The hostname must be the hostname of the local selected machine
    def send_antagonist_unicast(self, message, hostname, reply=True) -> bool:

        if self.address is None or message is None or hostname is None:
            return False

        if self.connection is None and self.generate_channel() is False:
            return False
        try:
            self.channel.basic_publish(exchange='health_system_exchange', routing_key='antagonist.' + hostname,
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

        if self.connection is None and self.generate_channel() is False:
            return False
        try:
            self.channel.basic_publish(exchange='health_system_exchange', routing_key='antagonist', body=message)
            return True
        except:
            if reply is True:
                self.generate_channel()
                return self.send_antagonist_multicast(message, False)
            return False

    # send a unicast message to a manager. The hostname must be the hostname of the local selected machine
    def send_manager_unicast(self, message, hostname, reply=True) -> bool:

        if self.address is None or message is None or hostname is None:
            return False

        if self.connection is None and self.generate_channel() is False:
            return False
        try:
            self.channel.basic_publish(exchange='health_system_exchange', routing_key='manager.' + hostname,
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

        if self.connection is None and self.generate_channel() is False:
            return False
        try:
            self.channel.basic_publish(exchange='health_system_exchange', routing_key='manager', body=message)
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

        if self.connection is None and self.generate_channel() is False:
            return False
        try:
            self.channel.basic_publish(exchange='health_system_exchange', routing_key='controller', body=message)
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
        try:
            result = self.channel.queue_declare(queue='', exclusive=True)
            queue_name = result.method.queue

            self.channel.queue_bind(exchange='health_system_exchange',
                                    queue=queue_name,
                                    routing_key=receiver_type)

            self.channel.queue_bind(exchange='health_system_exchange',
                                    queue=queue_name,
                                    routing_key=receiver_type + '.' + socket.gethostname())
            self.channel.basic_consume(queue=queue_name, on_message_callback=callback_fun, auto_ack=True)
            threading.Thread(target=self.channel.start_consuming).start()
            return True
        except:
            return False

    # example of valid callback function to be used into the allocate_receiver[TO BE DEFINED OUTSIDE RABBITCLIENT]
    @staticmethod
    def callback_example(method, properties, x, body):
        print(" [x] Received %r" % body)
