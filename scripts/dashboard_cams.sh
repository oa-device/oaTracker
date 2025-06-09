#!/bin/bash

while true; do
    VAL=$(duckdb -c "CREATE OR REPLACE SECRET secret ( TYPE s3, REGION 'ca-central-1', PROVIDER credential_chain ); SELECT COALESCE(f.Camera_Name, 'Unknown Camera') as camera_name, CASE WHEN s.last_update > (EXTRACT(epoch FROM now()) - 10) THEN '🟢' WHEN s.last_update > (EXTRACT(epoch FROM now()) - 60) THEN '🟠' ELSE '🔴' END as health, ROUND(EXTRACT(epoch FROM (now() - to_timestamp(s.last_update)))) as last_detection, ROUND(EXTRACT(epoch FROM (now() - to_timestamp(s.boot))) / 60) as minutes_since_boot, s.cam_id, f.Tailscale_hostname FROM read_csv('s3://detectiondb-prod/cams/stats/*.csv') s LEFT JOIN read_csv('s3://detectiondb-prod/cams/from_sheets.csv') f ON s.cam_id = f.Camera_UUID ORDER BY f.Camera_name DESC;" | tail -n +7)
    clear
    echo "$VAL"
    sleep 0.1 # Sleep for 10 seconds
done
