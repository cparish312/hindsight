#!/bin/bash

cd hindsight_server

# Start the Python backend script in the background
python server_backend.py &

# Start the Gunicorn server
uwsgi --https :6000,$HOME/.hindsight_server/server.crt,$HOME/.hindsight_server/server.key --workers 4 --wsgi-file run_server.py --callable app --master --enable-threads --py-autoreload 1

# Optional: If you want to ensure that if the Gunicorn server exits, the background Python process is also killed
trap "kill $!" EXIT