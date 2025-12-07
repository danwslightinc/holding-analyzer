#!/bin/bash

# Get absolute path to project
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_EXEC="$PROJECT_DIR/venv/bin/python"
SCRIPT_PATH="$PROJECT_DIR/email_report.py"

# Verify files exist
if [ ! -f "$PYTHON_EXEC" ]; then
    echo "Error: Virtual environment python not found at $PYTHON_EXEC"
    exit 1
fi

if [ ! -f "$SCRIPT_PATH" ]; then
    echo "Error: script not found at $SCRIPT_PATH"
    exit 1
fi

# Define cron job: Run at 17:00 (5PM) every Friday
# Format: m h  dom mon dow   command
CRON_JOB="0 17 * * 5 cd $PROJECT_DIR && $PYTHON_EXEC $SCRIPT_PATH >> $PROJECT_DIR/cron.log 2>&1"

# Check if job already exists to avoid duplicates
(crontab -l 2>/dev/null | grep -F "$SCRIPT_PATH") >/dev/null

if [ $? -eq 0 ]; then
    echo "Cron job already exists for this script."
    echo "Current crontab:"
    crontab -l
else
    # Add job to crontab
    (crontab -l 2>/dev/null; echo "$CRON_JOB") | crontab -
    echo "✅ Successfully added weekly Friday 5PM job to crontab."
    echo "Log file will be: $PROJECT_DIR/cron.log"
    echo "Current crontab:"
    crontab -l
fi
