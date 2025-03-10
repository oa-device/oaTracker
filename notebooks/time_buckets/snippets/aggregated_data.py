def get_aggregated_data_snippet():
    return f"""SELECT 
    time_bucket,
    zone_name,
    COUNT(*) AS total_visits,
    ROUND(AVG(duration_seconds), 2) AS avg_duration_seconds,
    ROUND(MIN(duration_seconds), 2) AS min_duration_seconds,
    ROUND(MAX(duration_seconds), 2) AS max_duration_seconds,
  FROM final_durations
  GROUP BY time_bucket, zone_name"""
