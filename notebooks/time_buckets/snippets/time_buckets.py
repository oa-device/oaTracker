

def get_time_buckets_snippet(): 
    return f"""SELECT time_bucket
  FROM (
    SELECT DISTINCT DATE_TRUNC('minute', event_ts) - 
      (INTERVAL '1 minute' * (EXTRACT(MINUTE FROM event_ts)::int % 5)) as time_bucket
    FROM base_events
  ) t"""