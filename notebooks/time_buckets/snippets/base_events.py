def get_base_events_snippet(source: str, bucket_size_minutes: int):
    return f"""
SELECT
    track_id,
    event_ts,
    DATE_TRUNC('minute', event_ts) - 
        (INTERVAL '1 minute' * (EXTRACT(MINUTE FROM event_ts)::int % {bucket_size_minutes})) as time_bucket,
    event_name,
    REGEXP_REPLACE(event_name, '^(enter|leave)_zone_', '') as zone_name,
    CASE 
        WHEN event_name LIKE 'enter%' THEN 'enter'
        WHEN event_name LIKE 'leave%' THEN 'leave'
    END as action_type
    FROM '{source}'
    WHERE event_name LIKE '%zone_%'"""
