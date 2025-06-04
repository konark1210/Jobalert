#!/bin/bash

# Create data directory if it doesn't exist
mkdir -p data

# Copy the latest consolidated jobs file to the data directory
LATEST_FILE=$(ls -t consolidated_jobs_*.xlsx | head -n1)
if [ -n "$LATEST_FILE" ]; then
    echo "Copying $LATEST_FILE to data directory..."
    cp "$LATEST_FILE" "data/"
    echo "File copied successfully"
else
    echo "No consolidated jobs file found"
    exit 1
fi

# Install dependencies
pip install -r requirements.txt

# Start the application
gunicorn app:app 