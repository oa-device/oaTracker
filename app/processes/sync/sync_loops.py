
import multiprocessing
import os
from subprocess import call
from threading import Event, Thread
import time

from app.parse_args import Args

import boto3

from pathlib import Path

script_path = os.path.normpath(Path(__file__).parent / "./sync.sh")
from multiprocessing.synchronize import Event as EventClass


session = boto3.Session(profile_name='default')
s3 = session.client('s3')


class SyncLoops():
    def __init__(
        self,
        args: Args,
        server_stopped: EventClass
    ):
        self.warehouse_path = "/tmp/warehouse_oa"
        self.key_substr_len = len(self.warehouse_path)+1
        self.args = args
        self.done_files: list[str] = []
        
        self.thread_backup = Thread(target = self.backup_replication, args = (server_stopped,))
        self.thread_quick = Thread(target = self.quick_replication, args = (server_stopped,))
        self.thread_backup.daemon = True
        self.thread_quick.daemon = True

    def start(self) -> None:
        self.init_database()
        self.thread_backup.start()
        self.thread_quick.start()
        self.thread_backup.join()
        self.thread_quick.join()


    def init_database(self):
        try:
            os.mkdir(self.warehouse_path)
        except Exception:
            pass


    def backup_replication(self, stopped):
        try:
            i=0
            while True:
                if i != 300:
                    time.sleep(0.1)
                    if stopped.is_set():
                        print('Backup replication stopped, running one last time')
                        time.sleep(0.5)
                        call(script_path, shell=True)
                        return
                    i+=1
                else:
                    i = 0
                    try:
                        call(script_path, shell=True)
                    except Exception as e:
                        print("Error", e)
        except Exception as e:
            print(e)
        
        
    def quick_replication(self, stopped):
        try:
            last_check=0
            last_check_mono=0
            key_substr_len = self.key_substr_len
            warehouse_path = self.warehouse_path
            while True:
                if stopped.is_set():
                    print('Quick replication stopped')
                    return
                try:
                    time.sleep(0.1)
                    
                    if time.monotonic() - last_check_mono < 10:
                        continue
                    
                    # print("Files and Directories in '% s':" % warehouse_path)
                    for root, dirs, files in os.walk(warehouse_path, True) :
                        for name in files:
                            file_path = os.path.join(root, name)
                            mustUpdate = os.stat(file_path).st_mtime > last_check
                            if mustUpdate:
                                key = file_path[key_substr_len:]
                                # print('updating', key)
                                try:
                                    before = time.monotonic()
                                    s3.upload_file(file_path, 'detectiondb-prod', key)
                                    # print(time.monotonic() - before)
                                except Exception as e:
                                    print("Error", e)
                        
                    last_check_mono=time.monotonic()
                    last_check=time.time()
                except Exception as e:
                    print("Error", e)
        except Exception as e:
            print(e)
