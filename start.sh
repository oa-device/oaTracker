#!/bin/bash

# Function to handle termination
cleanup() {
  echo "Stopping the tracker..."
  if [ ! -z "$PID" ]; then
    kill $PID
  fi
  exit
}

# Set up trap for SIGINT and SIGTERM
trap cleanup SIGINT SIGTERM

# Source the virtual environment
source .venv/bin/activate

# Run the tracker.py script in the background
python tracker.py &
PID=$!

# Wait for the process to finish or for a termination signal
wait $PID
