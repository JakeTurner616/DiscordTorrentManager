#!/bin/sh

# This script initializes and starts both the backend Flask application and the Discord bot.
# It first starts the Flask backend using Gunicorn, waits for it to initialize,
# and then starts the Discord bot. This ensures that both components run in sequence
# within the same container.

# Use this script as the entrypoint in the Dockerfile

# Start the backend (Flask app)
echo "Starting Flask backend..."
gunicorn app:app --bind 127.0.0.1:5000 --timeout 200 --workers 1 &

# Wait for the backend to initialize fully
sleep 4
echo "Flask backend started." 

# Start the frontend (Discord bot)
echo "Starting Discord bot..." 
python bot.py
