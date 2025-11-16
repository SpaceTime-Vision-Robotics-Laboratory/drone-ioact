"""udp_controller.py - Converts a udp message to a generic action. Useful for end-to-end tests."""
import threading
import socket

from drone_ioact import DataProducer, DataConsumer, ActionsProducer, ActionsQueue, Action
from drone_ioact.utils import logger

HOST = "127.0.0.1"

class UDPController(DataConsumer, ActionsProducer, threading.Thread):
    """
    Converts a udp message to a generic action.
    Parameters:
    - data_producer The DataProducer object with which this controller communicates
    - actions_queue The queue of possible actions this controller can send to the data_producer object
    """
    def __init__(self, data_producer: DataProducer, actions_queue: ActionsQueue, port: int):
        DataConsumer.__init__(self, data_producer)
        ActionsProducer.__init__(self, actions_queue)
        threading.Thread.__init__(self, daemon=True)
        self.port = port
        self.actions = set(actions_queue.actions)

    def add_to_queue(self, action: Action):
        """pushes an action to queue. Separate method so we can easily override it (i.e. priority queue put)"""
        self.actions_queue.put(action, block=True)

    def run(self):
        (s := socket.socket(socket.AF_INET, socket.SOCK_DGRAM)).bind((HOST, self.port))
        logger.info(f"UDP socket listening to '{HOST}:{self.port}'")

        while self.data_producer.is_streaming():
            data, addr = s.recvfrom(1024)
            message = data.decode("utf-8").strip()
            logger.debug(f"Received from '{addr[0]}:{addr[1]}', message: '{message}'")

            if message not in self.actions:
                logger.debug(msg := f"Unknown message: {message}")
            else:
                logger.debug(msg := f"Recevied '{message}'. Pushing to the actions queue.")
                self.add_to_queue(message)

            s.sendto(f"{msg}\n".encode("utf-8"), addr)
        s.close()
