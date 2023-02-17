import json

import pika


class PikaQueue:
    def __init__(self, host, port, username, password):
        self.connection = pika.BlockingConnection(pika.ConnectionParameters(host, port=port,
                                                                            credentials=pika.PlainCredentials(
                                                                                username=username, password=password),
                                                                            heartbeat=0))
        self.channel = self.connection.channel()
        self.channel.basic_qos(prefetch_count=1)

    def DeclareQueue(self, queue_name):
        self.channel.queue_declare(queue=queue_name, durable=True)

    def AddToQueue(self, queue_name, data):
        self.channel.basic_publish(exchange='', routing_key=queue_name, body=json.dumps(data),
                                   properties=pika.BasicProperties(delivery_mode=2))

    def GetFromQueue(self, queue_name, callback, auto_ack):
        self.channel.basic_consume(queue=queue_name, on_message_callback=callback, auto_ack=auto_ack)
        self.channel.start_consuming()

    def Close(self):
        self.connection.close()
