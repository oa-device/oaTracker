def get_final_durations_snippet():
    return """  SELECT 
        track_id,
        zone_name,
        time_bucket,
        -- Calculate the actual duration within this bucket
        EXTRACT(EPOCH FROM (bucket_end - bucket_start)) as duration_seconds
    FROM bucket_durations
    WHERE bucket_end > bucket_start
    """
