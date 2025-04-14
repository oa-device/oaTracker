import os
from pathlib import Path
import time
from uuid import UUID

from pyiceberg.partitioning import PartitionSpec, PartitionField
from pyiceberg.transforms import DayTransform, IdentityTransform
from pyiceberg.table.sorting import SortOrder, SortField
from pyiceberg.transforms import IdentityTransform
from pyiceberg.catalog import load_catalog
import daft

from pyiceberg.schema import Schema
from pyiceberg.types import (
    TimestampType,
    StringType,
    NestedField,
    IntegerType,
    FixedType
)

warehouse_path = "/tmp/test"
Path(warehouse_path).mkdir(parents=True, exist_ok=True)
catalog = load_catalog(
    "default",
    **{
        "type": "sql",
        "uri": f"sqlite:///{warehouse_path}/catalog.db",
        "warehouse": f"file://{warehouse_path}",
    },
)

if not catalog.table_exists("default.events"):
    catalog.create_namespace("default")

    schema = Schema(
        NestedField(field_id=1, name="event_ts", field_type=TimestampType(), required=True),
        NestedField(field_id=2, name="event_id", field_type=FixedType(16), required=True),
        NestedField(field_id=3, name="event_name", field_type=StringType(), required=True),
        NestedField(field_id=4, name="track_conf", field_type=IntegerType(), required=True),
        NestedField(field_id=5, name="track_class", field_type=IntegerType(), required=True),
        NestedField(field_id=6, name="track_id", field_type=FixedType(16), required=True),
        NestedField(field_id=7, name="cam_id", field_type=FixedType(16), required=True),
    )

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
    
print('local warehouse works')

df = daft.from_pylist([{
    "event_ts": daft.DataType.timestamp("us"),
    "event_id": UUID(bytes=os.urandom(16), version=4).bytes,  # type: ignore
    "event_name": f"leave_zone_entrance",  # type: ignore
    "track_class": 0,
    "track_conf": 88,
    "track_id": UUID(bytes=os.urandom(16), version=4).bytes,
    "cam_id": UUID(bytes=os.urandom(16), version=4).bytes,
}])

print(df)

table = catalog.load_table("default.events")

print(df.write_iceberg(table))

