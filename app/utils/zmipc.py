import mmap
import pickle
import struct
import threading
from queue import Queue
import time
from typing import Union
import warnings
import sys


def mmap_write(mm, msg):
    payload = pickle.dumps(msg)
    payload_size = len(payload)
    not_empty = struct.unpack('!I', mm[:4])[0]
    print(payload_size)
    if not_empty:
        warnings.warn("Memory is not empty!", Warning)
    else:
        mm.seek(0)
        mm.write(struct.pack('!I', payload_size))
        mm.seek(4)
        mm.write(payload)


def mmap_read(mm, size):
    payload = pickle.loads(mm[4:4 + size])
    mm.seek(0)
    mm.write(bytearray(4 + size))  # Clear the memory after reading
    return payload


def mmap_create(topic: str, msglen):
    if sys.platform.startswith("linux"):
        directory = "/dev/shm"
        pathname = f"{directory}/{topic}.shm"
        with open(pathname, "r+b") as f:
            f.seek(msglen)
            f.write(b"\0")
        with open(pathname, "r+b") as f:
            return mmap.mmap(f.fileno(), 0)
    elif sys.platform.startswith("win"):
        return mmap.mmap(-1, msglen, topic)


class ZMHandler(threading.Thread):

    def __init__(self, publication: dict, subscription: dict, queue, bq,
                 callback=None):
        threading.Thread.__init__(self)
        self.publication = publication
        self.subscription = subscription
        self.queue = queue
        self.bq = bq
        self.callback = callback

    def run(self):
        while True:
            for topic, mm in self.subscription.items():
                payload_size = struct.unpack('!I', mm[:4])[0]
                if payload_size:
                    payload = mmap_read(mm, payload_size)
                    if self.callback:
                        self.callback(topic, payload)
                    else:
                        self.bq.put([topic, payload])
                    continue
            while True:
                if not self.queue.empty():
                    topic, msg = self.queue.get()
                    mm = self.publication[topic]
                    mmap_write(mm, msg)
                else:
                    break


class ZMClient:
    """
    A zero-copy memory-sharing IPC client
    """

    def __init__(self):
        self.queue = Queue()
        self.bq = Queue()
        self.publication = {}
        self.subscription = {}
        self.sizes = {
            
        }
        self.pub_bg = {}
        self.sub_bg = {}
        self.bg_flag = False

    def add_publication(self, topic: str, msglen: int = 10000000):
        self.publication[topic] = mmap_create(topic, msglen)
        self.sizes[topic] = msglen

    def add_subscription(self, topic: str, msglen: int = 10000000):
        self.subscription[topic] = mmap_create(topic, msglen)
        self.sizes[topic] = msglen

    def publish(self, topic, msg, background=False):
        if background:
            self.queue.put([topic, msg])
        else:
            mm = self.publication[topic]
            mmap_write(mm, msg)

    def receive(self, topic, timeout: Union[int, float] = 10):
        """
        Receive messages in either blocking or non-blocking way. Note the
        non-blocking way has to work with the ZMHandler, which means the
        user need to call the execute function prior to this function.
        :param topic: The channel where you want to receive the message.
        :param timeout: How long you want to wait in the blocking way.
        :param background: Default is false. Set it to True if you want to
        have a non-blocking call.
        :return: The unpickled message or a dictionary of topic and message
        pairs.
        """
        if self.bg_flag:
            payload_collection = {}
            while True:
                if self.bq.empty():
                    payload = payload_collection if payload_collection else \
                        None
                    break
                else:
                    topic, msg = self.bq.get()
                    payload_collection[topic] = msg
        else:
            mm = self.subscription[topic]
            start_timer = time.time()
            while True:
                if time.time() - start_timer >= timeout:
                    raise Exception("TimeoutError")
                payload_size = struct.unpack('!I', mm[:4])[0]
                if payload_size:
                    payload = mmap_read(mm, payload_size)
                    break
        return payload

    def execute(self, callback=None):
        background = ZMHandler(self.publication, self.subscription,
                               self.queue, self.bq, callback)
        background.start()
        self.bg_flag = True

    def close(self, topic: Union[None, str] = None):
        if topic:
            mm = self.publication[topic]
            mm.close()
        else:
            for mm in self.publication.values():
                mm.close()