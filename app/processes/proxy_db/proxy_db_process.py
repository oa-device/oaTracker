
import multiprocessing
import os
import time

from app.parse_args import Args

from os import listdir
from os.path import isfile, join
import boto3

s3 = boto3.resource('s3')
# s3.meta.client.upload_file('/tmp/hello.txt', 'mybucket', 'replace/this/file.txt')


from pathlib import Path
litestream_path = os.path.normpath(Path(__file__).parent / "../../../.venv/bin/litestream")
database_folder_path = os.path.normpath(Path(__file__).parent / "../../../db/")


class ProxyDBProcess(multiprocessing.Process):
    def __init__(
        self,
        args: Args
    ):
        multiprocessing.Process.__init__(self, name=f"ProxyDB")
        
        self.warehouse_path = "/tmp/warehouse_oa"
        self.args = args
        self.done_files: list[str] = []


    def run(self) -> None:
        self.init_database()
        self.start_replication()


    def init_database(self):
        try:
            os.mkdir(self.warehouse_path)
        except Exception:
            pass


    def start_replication(self):
        pass
        # while(True):
            # time.sleep(0.1)
            # print("Files and Directories in '% s':" % self.warehouse_path)
            # obj = os.scandir(self.warehouse_path)
            # for entry in obj :
            #     if entry.is_dir() or entry.is_file():
            #         print(entry.name, entry.stat())
            # obj.close()        
            