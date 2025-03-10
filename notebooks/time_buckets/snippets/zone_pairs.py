def get_zone_pairs_snippet():
    return f"""
  SELECT 
    e.track_id,
    e.zone_name,
    e.event_ts as enter_time,
    MIN(l.event_ts) as leave_time,
  FROM base_events e
  LEFT JOIN base_events l ON 
    e.track_id = l.track_id AND
    e.zone_name = l.zone_name AND
    l.action_type = 'leave' AND
    l.event_ts > e.event_ts
  WHERE e.action_type = 'enter'
  GROUP BY 
    e.track_id,
    e.zone_name,
    e.event_ts"""
