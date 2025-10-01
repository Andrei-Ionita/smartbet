#!/bin/bash

# Set script variables
PROJECT_DIR="$(dirname "$(dirname "$(readlink -f "$0")")")"
LOG_FILE="/tmp/smartbet_sync.log"
DATE_FORMAT="%Y-%m-%d %H:%M:%S"

# Navigate to project directory
cd "$PROJECT_DIR" || { echo "Failed to navigate to project directory"; exit 1; }

# Log start of execution
echo "[$(date +"$DATE_FORMAT")] Starting SmartBet data sync..." >> "$LOG_FILE"

# Check for virtual environment and activate
if [ -d ".venv" ]; then
    source .venv/bin/activate
elif [ -d "venv" ]; then
    source venv/bin/activate
elif [ -d "env" ]; then
    source env/bin/activate
else
    echo "[$(date +"$DATE_FORMAT")] No virtual environment found. Proceeding without activation." >> "$LOG_FILE"
fi

# Run the sync command and capture output
OUTPUT=$(python manage.py sync_realtime_data --leagues 274 332)

# Extract summary information from output
MATCHES_CREATED=$(echo "$OUTPUT" | grep -oP "(\d+) fixtures created" | grep -oP "\d+")
MATCHES_UPDATED=$(echo "$OUTPUT" | grep -oP "(\d+) fixtures updated" | grep -oP "\d+")
ODDS_STORED=$(echo "$OUTPUT" | grep -oP "(\d+) odds snapshots stored" | grep -oP "\d+")

# Check if variables are empty and set defaults
MATCHES_CREATED=${MATCHES_CREATED:-0}
MATCHES_UPDATED=${MATCHES_UPDATED:-0}
ODDS_STORED=${ODDS_STORED:-0}

# Log command output
echo "$OUTPUT" >> "$LOG_FILE"

# Add summary log line
echo "[✓] SmartBet sync completed at $(date +"$DATE_FORMAT") – Matches: $MATCHES_UPDATED updated, $MATCHES_CREATED created, Odds: $ODDS_STORED matched" >> "$LOG_FILE"
echo "" >> "$LOG_FILE"  # Empty line for better readability

# If we activated a virtual environment, deactivate it
if command -v deactivate &> /dev/null; then
    deactivate
fi 