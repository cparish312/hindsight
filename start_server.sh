#!/bin/bash

cd hindsight_server

# Start the Python backend script in the background
python server_backend.py &

# Start the Gunicorn server
gunicorn --certfile=$HOME/.hindsight_server/server.crt --keyfile=$HOME/.hindsight_server/server.key -w 4 -b 0.0.0.0:6000 "run_server:create_app()"

# Optional: If you want to ensure that if the Gunicorn server exits, the background Python process is also killed
trap "kill $!" EXIT