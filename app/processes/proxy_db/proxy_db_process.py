
import multiprocessing
import os
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
        return f"{str(database_folder_path)}/cam1.db"

    def replication_db_filename(self):
        return f"{str(database_folder_path)}/cam1_replication.db"

    def init_database(self):
        try:
            os.mkdir(database_folder_path)
        except Exception:
            pass
        sqlite3.connect(self.replication_db_filename())
        connection = sqlite3.connect(self.db_filename())
        cursor = connection.cursor()
        cursor.execute('PRAGMA busy_timeout = 5000;')
        cursor.execute('PRAGMA synchronous = NORMAL;')
        cursor.execute(f""" CREATE TABLE IF NOT EXISTS events (
            event_id BLOB PRIMARY KEY,
            start NUMERIC NOT NULL,
            end NUMERIC NOT NULL,
            conf NUMERIC NOT NULL,
            name TEXT NOT NULL,
            class INTEGER NOT NULL,
            cam_id BLOB NOT NULL,
            track_id BLOB NOT NULL
        )""")
        connection.commit()


    def start_replication(self):
        print('proxydb 1')
        print([litestream_path, "replicate", self.db_filename(), self.replication_db_filename()])
        proc = subprocess.Popen([litestream_path, "replicate", self.db_filename(), "file://"+self.replication_db_filename()])
        print('proxydb 2')

        res = proc.wait()
        print('proxydb 3', res)
