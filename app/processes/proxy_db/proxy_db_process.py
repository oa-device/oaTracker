
import multiprocessing
import os
import time

from pyiceberg.partitioning import PartitionSpec, PartitionField
from pyiceberg.transforms import DayTransform, IdentityTransform
from pyiceberg.table.sorting import SortOrder, SortField
from pyiceberg.transforms import IdentityTransform
from app.parse_args import Args
from pyiceberg.catalog import load_catalog

        
from pyiceberg.schema import Schema
from pyiceberg.types import (
    TimestampType,
    StringType,
    NestedField,
    IntegerType,
    FixedType
)


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
        self.start_replication()

    def db_filename(self):
        return f"{str(database_folder_path)}/cam1.db"

    def replication_db_filename(self):
        return f"{str(database_folder_path)}/cam1_replication.db"

    def init_database(self):
        pass
        # try:
        #     os.mkdir(database_folder_path)
        # except Exception:
        #     pass
        # sqlite3.connect(self.replication_db_filename())
        # connection = sqlite3.connect(self.db_filename())
        # cursor = connection.cursor()
        # cursor.execute('PRAGMA optimize = 0x10002')
        # cursor.execute('PRAGMA journal_mode = WAL;')
        # cursor.execute('PRAGMA synchronous = normal;')
        # cursor.execute('PRAGMA mmap_size = 30000000000;')
        # cursor.execute('PRAGMA page_size = 1024;')
        # cursor.execute(f""" CREATE TABLE IF NOT EXISTS events (
        #     event_id TEXT PRIMARY KEY,
        #     event_ts NUMERIC NOT NULL,
        #     track_conf NUMERIC NOT NULL,
        #     event_name TEXT NOT NULL,
        #     track_class INTEGER NOT NULL,
        #     location_id TEXT NOT NULL,
        #     cam_id TEXT NOT NULL,
        #     track_id TEXT NOT NULL
        # )""")
        # connection.commit()

    def start_replication(self):
        
        return
        
        schema = Schema(
            NestedField(field_id=1, name="event_ts", field_type=TimestampType(), required=True),
            NestedField(field_id=2, name="event_id", field_type=FixedType(16), required=True),
            NestedField(field_id=3, name="event_name", field_type=StringType(), required=True),
            NestedField(field_id=4, name="track_conf", field_type=IntegerType(), required=True),
            NestedField(field_id=5, name="track_class", field_type=IntegerType(), required=True),
            NestedField(field_id=6, name="track_id", field_type=FixedType(16), required=True),
            NestedField(field_id=7, name="cam_id", field_type=FixedType(16), required=True),
        )
        
        
        warehouse_path = "/tmp/warehouse_oa"
        Path(warehouse_path).mkdir(parents=True, exist_ok=True)
        catalog = load_catalog(
            "default",
            **{
                "type": "sql",
                "uri": f"sqlite:///{warehouse_path}/catalog.db",
                "warehouse": f"s3://icebergdb-prod",
            },
        )
        
        if catalog.table_exists("default.events"):
            return
    
        catalog.create_namespace("default")

        # Sort on the track_id
        partition_spec = PartitionSpec(
            PartitionField(
                source_id=1, field_id=1000, transform=DayTransform(), name="datetime_day"
            ),
            PartitionField(
                source_id=7, field_id=1001, transform=IdentityTransform(), name="cam"
            )
        )

        # Sort on the track_id
        sort_order = SortOrder(SortField(source_id=7, transform=IdentityTransform()))

        catalog.create_table(
            identifier="default.events",
            schema=schema,
            partition_spec=partition_spec,
            sort_order=sort_order,
        )
        
        
        table = catalog.load_table("default.events")
        schema = table.schema().as_arrow()
        print(schema)
        

        # while True:
        #     begin = time.monotonic()
        #     connection = duckdb.connect(':memory:')
        #     cursor = connection.cursor()
        # # try: 
        #     cursor.sql("INSTALL sqlite;")
        #     cursor.sql("LOAD sqlite;")
        #     cursor.sql(f"ATTACH '{str(database_folder_path)}/cam1.db' AS sqlite_db (TYPE SQLITE);")
        #     cursor.sql(f"""
        #     COPY
        #     sqlite_db.events
        #     TO '{str(database_folder_path)}/cam1.parquet'
        #     (FORMAT 'parquet');
        #             """)
        #     connection.commit()
        #     print('done', time.monotonic() - begin)
        #     cursor.close()
        #     connection.close()
        #     time.sleep(1)
                    
        # except Exception as e :
        #     print(111, e)
        #     cursor.close()
        #     connection.close()
