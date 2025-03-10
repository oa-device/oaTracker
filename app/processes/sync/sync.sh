#!/bin/bash

# Configuration
DEST="s3://detectiondb-prod"      # Replace with your source
SOURCE="/tmp/warehouse_oa/"     # Replace with your destination

# Run sync with performance optimizations
aws s3 sync "$SOURCE" "$DEST" \
    --cli-read-timeout=10 \
    --cli-connect-timeout=5 \
    --no-verify-ssl \
    --no-progress \
        --exact-timestamps \
        --include="*.parquet" \
        --no-guess-mime-type \
        --region="ca-central-1" \
        --content-type="application/vnd.apache.parquet" \
        --profile=default \
        --size-only

# CREATE SECRET s3 (
#     TYPE S3,

#     REGION 'ca-central-1'
# );