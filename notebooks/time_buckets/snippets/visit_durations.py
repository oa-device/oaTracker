
def get_visit_durations_snippet():
    return f"""
  SELECT
    track_id,
    zone_name,
    time_bucket,
    enter_time,
    leave_time,
    EXTRACT(EPOCH FROM (leave_time - enter_time)) as duration_seconds,
    track_conf
  FROM zone_pairs
  WHERE leave_time IS NOT NULL"""


