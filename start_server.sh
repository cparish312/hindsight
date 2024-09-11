#!/bin/bash

# Function to kill both server processes
cleanup() {
    echo "Cleaning up and exiting..."
    kill -SIGTERM $PID_BACKEND $PID_SERVER
    wait $PID_BACKEND $PID_SERVER  # Wait for both processes to exit before exiting the script
    exit 0
}

# Trap SIGINT and SIGTERM signals and call cleanup
trap cleanup SIGINT SIGTERM

cd hindsight_server

# Start the Python backend script in the background
python server_backend.py &
PID_BACKEND=$!  # Save the PID of the backend server

# Start the Flask server in the background
python run_server.py &
PID_SERVER=$!  # Save the PID of the Flask server

# Wait for both processes
wait $PID_BACKEND $PID_SERVER