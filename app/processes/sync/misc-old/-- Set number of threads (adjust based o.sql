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

SELECT
      track_id,
      SUM(CASE WHEN event_name = 'enter_zone_exit' THEN 1 ELSE 0 END) as enter_exit_count,
      SUM(CASE WHEN event_name = 'leave_zone_exit' THEN 1 ELSE 0 END) as leave_exit_count,
      SUM(CASE WHEN event_name = 'enter_zone_entrance' THEN 1 ELSE 0 END) as enter_entrance_count,
      SUM(CASE WHEN event_name = 'leave_zone_entrance' THEN 1 ELSE 0 END) as leave_entrance_count,
      SUM(CASE WHEN event_name = 'enter_zone_center' THEN 1 ELSE 0 END) as enter_center_count,
      SUM(CASE WHEN event_name = 'leave_zone_center' THEN 1 ELSE 0 END) as leave_center_count,
  FROM '/tmp/warehouse_oa/*.parquet'
  GROUP BY track_id
  HAVING leave_exit_count != enter_exit_count OR enter_entrance_count != leave_entrance_count OR enter_center_count != leave_center_count;