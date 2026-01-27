#!/bin/bash

# Activate virtual environment
if [ -f "venv/Scripts/activate" ]; then
    source venv/Scripts/activate
elif [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
else
    echo "Virtual environment not found. Please create one first."
    exit 1
fi

# Function to kill all child processes on script exit
cleanup() {
    echo "Stopping servers..."
    kill $(jobs -p) 2>/dev/null
}
trap cleanup EXIT

echo "Starting Backend..."
uvicorn backend.app.main:app --reload --port 8000 &
BACKEND_PID=$!

echo "Starting Frontend..."
cd frontend
npm install
npm run start &
FRONTEND_PID=$!

# Wait for both processes
wait $BACKEND_PID $FRONTEND_PID
