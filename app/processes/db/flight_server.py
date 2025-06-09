import json
import duckdb
import pyarrow as pa
import pyarrow.flight as flight

class DuckDBFlightServer(flight.FlightServerBase):
    def __init__(self, location="grpc://0.0.0.0:8815", db_path="events.db"):
        self.conn = duckdb.connect(db_path)
        self.db_path = db_path
        
        self.conn.checkpoint()
        
        # Create table if it doesn't exist
        cur = self.conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS zone_events (
                event_ts TIMESTAMP,
                event_id UUID PRIMARY KEY,
                event_name TEXT,
                track_conf TINYINT,
                track_class TINYINT,
                track_id UUID,
                cam_id UUID
            )
        """
        )
        cur.close()
        
        super().__init__(location)
        
    def on_close(self):
        self.conn.checkpoint()
        print('Closing flight server')
        # self.event_server.set()
        self.shutdown()

    def do_get(self, context, ticket):
        """Handle 'GET' requests from clients to retrieve data."""
        query = ticket.ticket.decode("utf-8")
        cur = self.conn.cursor()
        result_table = cur.execute(query).fetch_arrow_table()
        cur.close()
        # Convert to record batches with alignment
        batches = result_table.to_batches(
            max_chunksize=1024
        )  # Use power of 2 for alignment

        if len(batches) > 0:
            return flight.RecordBatchStream(pa.Table.from_batches(batches))
        else:
            # If no results, return an empty table with the schema from the result_table
            return flight.RecordBatchStream(pa.Table.from_batches([], schema=result_table.schema))

    def do_put(self, context, descriptor, reader, writer):
        """Handle 'PUT' requests to upload data to the DuckDB instance."""
        table = reader.read_all()
        info = json.loads(descriptor.path[0])

        table_name = info["table"]

        # Convert to record batches for better alignment
        batches = table.to_batches(max_chunksize=1024)
        aligned_table = pa.Table.from_batches(batches)
        
        cur = self.conn.cursor()
        cur.register("temp_table", aligned_table)

        # Insert new data
        cur.execute(
            f"""
            INSERT INTO {table_name} 
                SELECT * FROM temp_table 
                WHERE event_name LIKE 'zone_enter%';
        """
        )

        cur.execute(
            f"""
            INSERT INTO {table_name} 
                 SELECT * FROM temp_table 
                 WHERE event_name LIKE 'zone_leave%'
                 ON CONFLICT (event_id) DO UPDATE SET
                    event_ts = excluded.event_ts,
                    track_conf = excluded.track_conf;
        """
        )
        cur.close()
