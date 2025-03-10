

def get_time_buckets_snippet(bucket_size_minutes: int): 
    return f"""SELECT time_bucket
  FROM (
    SELECT DISTINCT DATE_TRUNC('minute', event_ts) - 
      (INTERVAL '{bucket_size_minutes} minute' * (EXTRACT(MINUTE FROM event_ts)::int % {bucket_size_minutes})) as time_bucket
    FROM base_events
  ) t"""