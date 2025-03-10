def get_bucket_data_snippet():
    return f"""
SELECT 
  time_bucket,
  zone_name,
  COUNT(*) as total_visits,
  ROUND(AVG(duration_seconds), 2) as avg_duration_seconds,
  ROUND(MIN(duration_seconds), 2) as min_duration_seconds,
  ROUND(MAX(duration_seconds), 2) as max_duration_seconds,
  ROUND(AVG(track_conf), 2) as avg_track_confidence,
  COUNT(DISTINCT track_id) as unique_tracks
FROM visit_durations
GROUP BY 
  time_bucket,
  zone_name
ORDER BY 
  time_bucket,
  zone_name;"""
