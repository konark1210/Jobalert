#!/bin/bash

# Activate virtual environment
source venv/bin/activate

# Get local IP address
LOCAL_IP=$(ipconfig getifaddr en0 || ipconfig getifaddr en1)
echo "Starting server..."
echo "Your local IP address is: $LOCAL_IP"
echo "Other computers can access the server at: http://$LOCAL_IP:8000"
echo "Press Ctrl+C to stop the server"

# Start Gunicorn
gunicorn -c gunicorn_config.py app:app 