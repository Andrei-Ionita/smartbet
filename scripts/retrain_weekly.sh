#!/bin/bash

# Weekly ML Model Retraining Script for SmartBet
# This script runs the complete retraining pipeline and logs results
# Designed to be run via cron job

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
LOG_DIR="$PROJECT_DIR/logs"
VENV_PATH="$PROJECT_DIR/.venv"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
LOG_FILE="$LOG_DIR/retrain_weekly_$TIMESTAMP.log"

# Create logs directory if it doesn't exist
mkdir -p "$LOG_DIR"

# Function to log messages with timestamp
log_message() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# Function to handle errors
handle_error() {
    log_message "ERROR: $1"
    log_message "Retraining failed. Check logs for details."
    exit 1
}

# Start logging
log_message "🚀 Starting weekly ML model retraining..."
log_message "Project directory: $PROJECT_DIR"
log_message "Log file: $LOG_FILE"

# Check if virtual environment exists
if [ ! -d "$VENV_PATH" ]; then
    handle_error "Virtual environment not found at $VENV_PATH"
fi

# Activate virtual environment
log_message "📦 Activating virtual environment..."
source "$VENV_PATH/bin/activate" 2>/dev/null || source "$VENV_PATH/Scripts/activate" 2>/dev/null || handle_error "Failed to activate virtual environment"

# Change to project directory
cd "$PROJECT_DIR" || handle_error "Failed to change to project directory"

# Check if Django is available
log_message "🔍 Checking Django availability..."
python -c "import django" 2>/dev/null || handle_error "Django not available in virtual environment"

# Run the retraining pipeline
log_message "🧠 Starting automated retraining pipeline..."
python manage.py retrain_model --save-report --months 24 --cv 5 2>&1 | tee -a "$LOG_FILE"

# Check if retraining was successful
if [ ${PIPESTATUS[0]} -eq 0 ]; then
    log_message "✅ Retraining completed successfully!"
    
    # Test the model with a few predictions
    log_message "🔮 Testing model predictions..."
    python manage.py test_model_predictions --count 3 2>&1 | tee -a "$LOG_FILE"
    
    # Log model info
    log_message "📊 Model information:"
    if [ -f "$PROJECT_DIR/predictor/training_report.json" ]; then
        python -c "
import json
try:
    with open('predictor/training_report.json', 'r') as f:
        report = json.load(f)
    metrics = report.get('metrics', {})
    print(f'Accuracy: {metrics.get(\"accuracy\", \"N/A\"):.4f}')
    print(f'Log Loss: {metrics.get(\"log_loss\", \"N/A\"):.4f}')
    print(f'Model Type: {report.get(\"model_type\", \"unknown\")}')
    print(f'Trained At: {report.get(\"trained_at\", \"unknown\")}')
except Exception as e:
    print(f'Error reading report: {e}')
" 2>&1 | tee -a "$LOG_FILE"
    fi
    
    log_message "🎉 Weekly retraining completed successfully!"
    
    # Optional: Send notification (uncomment and configure as needed)
    # echo "SmartBet ML model retrained successfully on $(date)" | mail -s "SmartBet Retraining Success" admin@example.com
    
else
    handle_error "Retraining pipeline failed"
fi

# Cleanup old log files (keep last 30 days)
log_message "🧹 Cleaning up old log files..."
find "$LOG_DIR" -name "retrain_weekly_*.log" -mtime +30 -delete 2>/dev/null || true

# Cleanup old training reports (keep last 60 days)
if [ -d "$PROJECT_DIR/ml/reports" ]; then
    find "$PROJECT_DIR/ml/reports" -name "training_report_*.json" -mtime +60 -delete 2>/dev/null || true
    find "$PROJECT_DIR/ml/reports" -name "retraining_summary_*.json" -mtime +60 -delete 2>/dev/null || true
fi

log_message "📝 Log file saved to: $LOG_FILE"
log_message "✨ Weekly retraining script completed!"

# Deactivate virtual environment
deactivate 2>/dev/null || true 