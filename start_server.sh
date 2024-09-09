#!/bin/bash

cd hindsight_server

# Start the Python backend script in the background
python server_backend.py &

# Start the flask server
python run_server.py

trap "kill $!" EXIT