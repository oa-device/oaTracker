# data
SELECT 
    track_id,
    MIN(CASE WHEN event_name = 'enter_zone_entrance' THEN event_ts END) as entrance_ts,
    MAX(CASE WHEN event_name IN ('enter_zone_exit', 'leave_zone_exit') THEN event_ts END) as exit_ts,
    exit_ts - entrance_ts as duration
FROM '/tmp/warehouse_oa/*.parquet'
GROUP BY track_id
HAVING MIN(CASE WHEN event_name = 'enter_zone_entrance' THEN event_ts END) IS NOT NULL
   AND MAX(CASE WHEN event_name IN ('enter_zone_exit', 'leave_zone_exit') THEN event_ts END) IS NOT NULL
   AND MIN(CASE WHEN event_name = 'enter_zone_entrance' THEN event_ts END) < 
       MAX(CASE WHEN event_name IN ('enter_zone_exit', 'leave_zone_exit') THEN event_ts END);


# count
SELECT COUNT(*) FROM (SELECT 
    track_id
FROM '/tmp/warehouse_oa/*.parquet'
GROUP BY track_id
HAVING MIN(CASE WHEN event_name = 'enter_zone_entrance' THEN event_ts END) IS NOT NULL
   AND MAX(CASE WHEN event_name IN ('enter_zone_exit', 'leave_zone_exit') THEN event_ts END) IS NOT NULL
   AND MIN(CASE WHEN event_name = 'enter_zone_entrance' THEN event_ts END) < 
       MAX(CASE WHEN event_name IN ('enter_zone_exit', 'leave_zone_exit') THEN event_ts END));