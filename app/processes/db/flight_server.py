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
            f"""
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

def parse_zone_occupancy_query(query_string):
    """
    Parse a zone_occupancy function call and replace it with the full SQL query.
    
    Args:
        query_string: A SQL query string containing a zone_occupancy function call
        
    Returns:
        The full SQL query with the function call replaced
    """
    # First, check if the query contains our function
    if "zone_occupancy" not in query_string:
        return query_string
    
    # Extract the parameters
    import re
    pattern = r"zone_occupancy\((\d+),\s*([^)]*)\)"
    match = re.search(pattern, query_string)
    
    if not match:
        # Try matching just a timestamp without camera IDs
        pattern = r"zone_occupancy\((\d+)\)"
        match = re.search(pattern, query_string)
        if match:
            ts = match.group(1)
            cam_ids = "NULL"
        else:
            return query_string  # No valid function call found
    else:
        ts = match.group(1)
        cam_ids = match.group(2)
    
    # Build the full query
    full_query = f"""
    WITH time_params AS (
      SELECT 
        epoch_ms({int(ts) * 1000}) AS requested_ts,
        epoch_ms({int(ts) - 60*60*1000}) AS window_start,    -- Look back 1 hour (reduced from 2)
        epoch_ms({int(ts) + 10*60*1000}) AS window_end,      -- Look ahead 10 minutes (reduced from 1 hour)
        epoch_ms({int(ts) - 5*1000}) AS fallback_start       -- Look back 5 seconds for fallback
    ),
    -- Get all enter events for the time window
    all_enter_events AS (
      SELECT
        track_id,
        cam_id,
        track_class,
        SUBSTRING(event_name, LENGTH('zone_enter_') + 1) AS zone_name,
        event_ts,
        'enter' AS event_type
      FROM zone_events, time_params
      WHERE 
        event_name LIKE 'zone_enter_%' AND
        event_ts BETWEEN time_params.window_start AND time_params.requested_ts
        {f" AND ({cam_ids} IS NULL OR cam_id = ANY({cam_ids}))" if cam_ids != "NULL" else ""}
    ),
    -- Get all leave events for the time window
    all_leave_events AS (
      SELECT
        track_id,
        cam_id,
        NULL AS track_class, -- We'll join to get the track_class from enter events
        SUBSTRING(event_name, LENGTH('zone_leave_') + 1) AS zone_name,
        event_ts,
        'leave' AS event_type
      FROM zone_events, time_params
      WHERE 
        event_name LIKE 'zone_leave_%' AND
        event_ts BETWEEN time_params.window_start AND time_params.requested_ts
        {f" AND ({cam_ids} IS NULL OR cam_id = ANY({cam_ids}))" if cam_ids != "NULL" else ""}
    ),
    -- Combine all events
    all_events AS (
      SELECT * FROM all_enter_events
      UNION ALL
      SELECT * FROM all_leave_events
    ),
    -- Directly find all zone/cam/track class combinations from the data
    zone_combinations AS (
      SELECT DISTINCT
        CASE 
          WHEN event_name LIKE 'zone_enter_%' THEN 
            SUBSTRING(event_name, LENGTH('zone_enter_') + 1)
          ELSE 
            SUBSTRING(event_name, LENGTH('zone_leave_') + 1)
        END AS zone_name,
        cam_id,
        track_class
      FROM zone_events
      WHERE 
        event_name LIKE 'zone_%' AND 
        track_class IS NOT NULL
        {f" AND ({cam_ids} IS NULL OR cam_id = ANY({cam_ids}))" if cam_ids != "NULL" else ""}
    ),
    -- Find the latest event for each track in each zone
    latest_events AS (
      SELECT 
        track_id,
        cam_id,
        zone_name,
        MAX(event_ts) AS latest_event_ts
      FROM all_events
      GROUP BY track_id, cam_id, zone_name
    ),
    -- Join to get the type of the latest event
    latest_event_types AS (
      SELECT
        le.track_id,
        le.cam_id,
        le.zone_name,
        ae.track_class,
        ae.event_type AS latest_event_type,
        le.latest_event_ts
      FROM latest_events le
      JOIN all_events ae ON
        le.track_id = ae.track_id AND
        le.cam_id = ae.cam_id AND
        le.zone_name = ae.zone_name AND
        le.latest_event_ts = ae.event_ts
    ),
    -- Find latest entry and exit for each track/zone
    entry_exit_times AS (
      SELECT
        track_id,
        cam_id,
        zone_name,
        MAX(CASE WHEN event_type = 'enter' THEN event_ts ELSE NULL END) AS latest_entry,
        MAX(CASE WHEN event_type = 'leave' THEN event_ts ELSE NULL END) AS latest_exit
      FROM all_events
      GROUP BY track_id, cam_id, zone_name
    ),
    -- Combine latest event type with entry/exit times
    track_state AS (
      SELECT
        let.track_id,
        let.cam_id,
        let.zone_name,
        let.track_class,
        eet.latest_entry,
        eet.latest_exit,
        let.latest_event_type,
        -- Determine if track is in the zone at requested time:
        -- Either its most recent event is "enter" or it entered after its most recent exit
        CASE
          WHEN let.latest_event_type = 'enter' THEN TRUE
          WHEN eet.latest_entry > eet.latest_exit OR eet.latest_exit IS NULL THEN TRUE
          ELSE FALSE
        END AS is_in_zone
      FROM latest_event_types let
      JOIN entry_exit_times eet ON
        let.track_id = eet.track_id AND
        let.cam_id = eet.cam_id AND
        let.zone_name = eet.zone_name
      WHERE eet.latest_entry IS NOT NULL -- Must have at least one entry
    ),
    -- Current zone occupancy based on track state
    current_zone_occupancy AS (
      SELECT
        cam_id,
        zone_name,
        track_class,
        (SELECT requested_ts FROM time_params) AS effective_timestamp,
        COUNT(DISTINCT track_id) AS count
      FROM track_state
      WHERE is_in_zone = TRUE
      GROUP BY cam_id, zone_name, track_class
    ),
    -- Simple recent non-zero results for fallback
    recent_non_zero AS (
      WITH recent_timestamps AS (
        -- Generate the 5 most recent timestamps (1 second apart)
        SELECT 
          epoch_ms({int(ts) - 5 * 1000}) AS check_ts,
          {int(ts) - 5} AS ts_epoch
        FROM (
          -- This generates 5 rows with values 1,2,3,4,5 representing seconds to look back
          SELECT UNNEST(ARRAY[1, 2, 3, 4, 5]) AS seconds_ago
        ) lookback_seconds
        CROSS JOIN time_params
      ),
      -- For each recent timestamp, get all enter events
      recent_enter_events AS (
        SELECT
          rt.check_ts,
          rt.ts_epoch,
          ae.track_id,
          ae.cam_id,
          ae.track_class,
          ae.zone_name,
          ae.event_ts
        FROM all_enter_events ae
        CROSS JOIN recent_timestamps rt
        WHERE ae.event_ts <= rt.check_ts
      ),
      -- For each recent timestamp, get all leave events
      recent_leave_events AS (
        SELECT
          rt.check_ts,
          rt.ts_epoch,
          al.track_id,
          al.cam_id,
          al.zone_name,
          al.event_ts
        FROM all_leave_events al
        CROSS JOIN recent_timestamps rt
        WHERE al.event_ts <= rt.check_ts
      ),
      -- For each track/zone at each timestamp, get latest entry
      recent_entries AS (
        SELECT
          check_ts,
          ts_epoch,
          track_id,
          cam_id,
          zone_name,
          MAX(event_ts) AS latest_entry_ts,
          track_class
        FROM recent_enter_events
        GROUP BY check_ts, ts_epoch, track_id, cam_id, zone_name, track_class
      ),
      -- For each track/zone at each timestamp, get latest exit
      recent_exits AS (
        SELECT
          check_ts,
          ts_epoch,
          track_id,
          cam_id,
          zone_name,
          MAX(event_ts) AS latest_exit_ts
        FROM recent_leave_events
        GROUP BY check_ts, ts_epoch, track_id, cam_id, zone_name
      ),
      -- Determine which tracks are in zones at each timestamp
      recent_track_states AS (
        SELECT
          re.check_ts,
          re.ts_epoch,
          re.track_id,
          re.cam_id,
          re.zone_name,
          re.track_class,
          re.latest_entry_ts,
          rx.latest_exit_ts,
          -- Track is in zone if either:
          -- 1. It entered but never left (latest_exit_ts IS NULL)
          -- 2. It entered after its most recent exit (latest_entry_ts > latest_exit_ts)
          CASE
            WHEN rx.latest_exit_ts IS NULL THEN TRUE
            WHEN re.latest_entry_ts > rx.latest_exit_ts THEN TRUE
            ELSE FALSE
          END AS is_in_zone
        FROM recent_entries re
        LEFT JOIN recent_exits rx ON
          re.check_ts = rx.check_ts AND
          re.track_id = rx.track_id AND
          re.cam_id = rx.cam_id AND
          re.zone_name = rx.zone_name
      ),
      -- Count tracks in zone at each recent timestamp
      recent_counts AS (
        SELECT
          check_ts,
          ts_epoch,
          cam_id,
          zone_name,
          track_class,
          COUNT(DISTINCT track_id) AS count
        FROM recent_track_states
        WHERE is_in_zone = TRUE
        GROUP BY check_ts, ts_epoch, cam_id, zone_name, track_class
        HAVING COUNT(DISTINCT track_id) > 0 -- Only keep non-zero counts
      ),
      -- Get the most recent non-zero count for each zone
      latest_non_zero_counts AS (
        SELECT
          cam_id,
          zone_name,
          track_class,
          MAX(check_ts) AS latest_ts
        FROM recent_counts
        GROUP BY cam_id, zone_name, track_class
      ),
      -- Join back to get the count and timestamp
      latest_counts AS (
        SELECT
          lnz.cam_id,
          lnz.zone_name,
          lnz.track_class,
          rc.ts_epoch,
          rc.count
        FROM latest_non_zero_counts lnz
        JOIN recent_counts rc ON
          lnz.cam_id = rc.cam_id AND
          lnz.zone_name = rc.zone_name AND
          lnz.track_class = rc.track_class AND
          lnz.latest_ts = rc.check_ts
      )
      -- Final fallback data
      SELECT
        cam_id,
        zone_name,
        track_class,
        CAST(ts_epoch AS VARCHAR) AS effective_timestamp,
        count
      FROM latest_counts
    )
    
    -- Final result with fallback to recent non-zero
    SELECT
      zc.cam_id,
      zc.zone_name,
      zc.track_class,
      CASE
        WHEN czo.count > 0 THEN CAST((SELECT requested_ts FROM time_params) AS VARCHAR)
        ELSE COALESCE(rnz.effective_timestamp, CAST((SELECT requested_ts FROM time_params) AS VARCHAR))
      END AS effective_timestamp,
      COALESCE(
        NULLIF(czo.count, 0), -- Use current if non-zero
        rnz.count,            -- Otherwise use recent non-zero
        0                     -- Final fallback to 0
      ) AS count
    FROM zone_combinations zc
    LEFT JOIN current_zone_occupancy czo ON
      zc.cam_id = czo.cam_id AND
      zc.zone_name = czo.zone_name AND
      zc.track_class = czo.track_class
    LEFT JOIN recent_non_zero rnz ON
      zc.cam_id = rnz.cam_id AND
      zc.zone_name = rnz.zone_name AND
      zc.track_class = rnz.track_class
    ORDER BY
      zc.cam_id,
      zc.zone_name,
      zc.track_class
    """
    
    # Replace the function call with the full query
    return re.sub(r"SELECT\s+\*\s+FROM\s+zone_occupancy\([^)]+\)", full_query.strip(), query_string)