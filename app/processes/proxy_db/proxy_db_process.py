
import asyncio
import multiprocessing
import os
import random
import sqlite3
import subprocess

from app.parse_args import Args

from app.utils.mmap import mmap_read, pathname_state

from pathlib import Path

litestream_path = os.path.normpath(Path(__file__).parent / "../../../.venv/bin/litestream")
database_folder_path = os.path.normpath(Path(__file__).parent / "../../../db/")

class ProxyDBProcess(multiprocessing.Process):
    def __init__(
        self,
        args: Args
    ):
        multiprocessing.Process.__init__(self, name=f"ProxyDB")
        
        self.args = args


    def run(self) -> None:
        self.init_database()
        #self.start_replication()

    def db_filename(self):
        return f"{str(database_folder_path)}/test.db"

    def replication_db_filename(self):
        return f"{str(database_folder_path)}/replication.db"

    def init_database(self):
        try:
            os.mkdir(database_folder_path)
        except:
            pass
        sqlite3.connect(self.replication_db_filename())
        self.connection = sqlite3.connect(self.db_filename())
        self.cursor = self.connection.cursor()
        self.cursor.execute('PRAGMA busy_timeout = 5000;')
        self.cursor.execute('PRAGMA synchronous = NORMAL;')
        self.cursor.execute("""
                create table IF NOT EXISTS boxes
                (
                    id TEXT not null primary key,
                    class INT,
                    x_center FLOAT,
                    y_center FLOAT,
                    xa FLOAT,
                    ya FLOAT,
                    xb FLOAT,
                    yb FLOAT
                )
            """)
        

        def numbers(n):
            return [str(random.random()), 0, random.random(),random.random(),random.random(),random.random(),random.random(),random.random()]
        
        for i in range(0, 26):
            boxes = list(map(numbers, list(range(100_000))))
            print(boxes[:10])
            self.cursor.executemany("insert into boxes(id,class,x_center,y_center,xa,ya,xb,yb) values (?,?,?,?,?,?,?,?)", boxes)
            
        self.connection.commit()
            
        
        
    def start_replication(self):
        print('proxydb 1')
        print([litestream_path, "replicate", self.db_filename(), self.replication_db_filename()])
        proc = subprocess.Popen([litestream_path, "replicate", self.db_filename(), "file://"+self.replication_db_filename()])
        print('proxydb 2')

        res = proc.wait()
        print('proxydb 3', res)


def start_db_proxy_process(
    args: Args
):
    ProxyDBProcess(
        args
    ).start()


