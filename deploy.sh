#!/bin/bash

echo "Starting deployment process..."

# Print current directory and its contents
echo "Current directory: $(pwd)"
echo "Directory contents:"
ls -la

# Create data directory if it doesn't exist
echo "Creating data directory..."
mkdir -p data
echo "Data directory created at: $(pwd)/data"

# Find and copy the latest consolidated jobs file
echo "Looking for consolidated jobs files..."
LATEST_FILE=$(ls -t consolidated_jobs_*.xlsx | head -n1)

if [ -n "$LATEST_FILE" ]; then
    echo "Found latest file: $LATEST_FILE"
    echo "Copying to data directory..."
    cp -v "$LATEST_FILE" "data/"
    
    # Verify the copy
    if [ -f "data/$LATEST_FILE" ]; then
        echo "File copied successfully to data directory"
        echo "Data directory contents:"
        ls -la data/
    else
        echo "Error: File copy failed"
        exit 1
    fi
else
    echo "Error: No consolidated jobs file found"
    echo "Current directory contents:"
    ls -la
    exit 1
fi

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Print Python version and environment
echo "Python version:"
python --version
echo "Python path:"
which python
echo "Environment variables:"
env | grep -E "PYTHON|PATH"

# Start the application
echo "Starting application..."
gunicorn app:app 