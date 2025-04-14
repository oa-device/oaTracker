## create db

INSTALL sqlite;
LOAD sqlite;
ATTACH '../tracking.db' (TYPE SQLITE);
USE tracking;

COPY (
    SELECT
        event_id,
        track_conf,
        event_name,
        track_class,
        cam_id,
        track_id, epoch_ms(event_ts) AS event_ts
        FROM events
) TO 'events.parquet' (
    FORMAT PARQUET, CODEC 'zstd', COMPRESSION_LEVEL 9
);

## analyze query
EXPLAIN ANALYZE SELECT
          track_id,
          MIN(CASE WHEN event_name = 'enter_zone_entrance' THEN event_ts END) as start_ts,
          MAX(CASE WHEN event_name IN ('enter_zone_exit', 'leave_zone_exit') THEN event_ts END) as end_ts    FROM './events.parquet'
      GROUP BY track_id
      HAVING MIN(CASE WHEN event_name = 'enter_zone_entrance' THEN event_ts END) IS NOT NULL
      AND MAX(CASE WHEN event_name IN ('enter_zone_exit', 'leave_zone_exit') THEN event_ts END) IS NOT NULL
      AND MIN(CASE WHEN event_name = 'enter_zone_entrance' THEN event_ts END) <
          MAX(CASE WHEN event_name IN ('enter_zone_exit', 'leave_zone_exit') THEN event_ts END) ORDER BY start_ts DESC LIMIT 15;


## run query
SELECT
          track_id,
          MIN(CASE WHEN event_name = 'enter_zone_entrance' THEN event_ts END) as start_ts,
          MAX(CASE WHEN event_name IN ('enter_zone_exit', 'leave_zone_exit') THEN event_ts END) as end_ts
FROM './events.parquet'
      GROUP BY track_id
      HAVING MIN(CASE WHEN event_name = 'enter_zone_entrance' THEN event_ts END) IS NOT NULL
      AND MAX(CASE WHEN event_name IN ('enter_zone_exit', 'leave_zone_exit') THEN event_ts END) IS NOT NULL
      AND MIN(CASE WHEN event_name = 'enter_zone_entrance' THEN event_ts END) <
          MAX(CASE WHEN event_name IN ('enter_zone_exit', 'leave_zone_exit') THEN event_ts END) ORDER BY start_ts DESC LIMIT 15;