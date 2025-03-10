def get_merged_data_snippet(zones: list[str]):
    body = ""

    for zone in zones:
        body += f"""
  MAX(CASE WHEN zone_name = '{zone}' THEN total_visits ELSE 0 END) AS {zone}_total_visits,
  MAX(CASE WHEN zone_name = '{zone}' THEN avg_duration_seconds ELSE 0 END) AS {zone}_avg_duration_seconds,
  SUM((CASE WHEN zone_name = '{zone}' THEN avg_duration_seconds ELSE 0 END) * (CASE WHEN zone_name = '{zone}' THEN total_visits ELSE 0 END)) AS {zone}_total_time,
"""

    return f"""
SELECT 
  time_bucket,
  {body}
FROM aggregated_data
GROUP BY time_bucket
ORDER BY time_bucket;
"""
