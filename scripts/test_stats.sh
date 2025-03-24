#!/bin/bash

# Test statistics endpoint
# Usage: ./test_stats.sh [minutes]
# Example: ./test_stats.sh 5

# Default to 1 minute if not specified
MINUTES=${1:-1}

# API URL
API_URL="http://localhost:8080/api/stats?minutes=$MINUTES"

echo "Fetching detection statistics for the last $MINUTES minute(s)..."

# Make the API request and format the JSON response
curl -s "$API_URL" | python3 -m json.tool

echo ""
echo "To access the stats dashboard in a browser, go to:"
echo "http://localhost:8080/stats"
