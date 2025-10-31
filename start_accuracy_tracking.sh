#!/bin/bash
# Prediction Accuracy Tracking System Startup Script

echo "Starting Prediction Accuracy Tracking System..."
echo "All data is REAL - no mock data used"
echo ""

# Check if .env file exists
if [ ! -f .env ]; then
    echo "ERROR: .env file not found. Please create one with SPORTMONKS_API_TOKEN"
    exit 1
fi

# Load environment variables
export $(cat .env | xargs)

# Run prediction tracker
echo "Fetching weekend fixtures and storing predictions..."
python prediction_tracker.py

echo ""
echo "Setup complete!"
echo "To view results after matches finish:"
echo "   1. Run: python prediction_tracker.py --results"
echo "   2. Run: python accuracy_dashboard.py"
echo "   3. Open: http://localhost:5000"
