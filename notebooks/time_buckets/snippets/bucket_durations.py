def get_bucket_durations_snippet(bucket_size_minutes: int):
    return f"""SELECT 
        zp.track_id,
        zp.zone_name,
        tb.time_bucket,
        -- Calculate the intersection of the visit with the bucket
        GREATEST(zp.enter_time, tb.time_bucket) as bucket_start,
        LEAST(zp.leave_time, tb.time_bucket + INTERVAL '{bucket_size_minutes} minutes') as bucket_end,
        zp.enter_time,
        zp.leave_time
    FROM zone_pairs zp
    CROSS JOIN time_buckets tb
    WHERE zp.leave_time IS NOT NULL
        AND tb.time_bucket <= zp.leave_time 
        AND tb.time_bucket + INTERVAL '{bucket_size_minutes} minutes' > zp.enter_time
    """
