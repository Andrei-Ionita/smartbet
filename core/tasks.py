"""
Scheduled tasks for the SmartBet application.
"""

import logging
from io import StringIO
from datetime import datetime
from django.core.management import call_command

logger = logging.getLogger(__name__)

def sync_realtime_data():
    """
    Run the sync_realtime_data command and log results.
    This function is scheduled to run via Django-Q.
    """
    # Capture command output
    output = StringIO()
    start_time = datetime.now()
    
    try:
        # Execute the management command with the specified leagues
        call_command('sync_realtime_data', leagues=[274, 332], stdout=output)
        
        command_output = output.getvalue()
        
        # Parse the output to extract statistics
        matches_created = 0
        matches_updated = 0
        odds_stored = 0
        
        for line in command_output.splitlines():
            if "fixtures created" in line and "fixtures updated" in line:
                parts = line.split()
                for i, part in enumerate(parts):
                    if part == "created,":
                        matches_created = int(parts[i-1])
                    elif part == "updated,":
                        matches_updated = int(parts[i-1])
            elif "odds snapshots stored" in line:
                parts = line.split()
                for i, part in enumerate(parts):
                    if part == "stored":
                        odds_stored = int(parts[i-1])
        
        # Calculate duration
        duration = (datetime.now() - start_time).total_seconds()
        
        # Log the summary
        logger.info(
            f"[✓] SmartBet sync completed at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} – "
            f"Matches: {matches_updated} updated, {matches_created} created, "
            f"Odds: {odds_stored} matched (Duration: {duration:.2f}s)"
        )
        
        return f"Matches: {matches_updated} updated, {matches_created} created, Odds: {odds_stored} matched"
        
    except Exception as e:
        logger.error(f"Error in sync_realtime_data task: {str(e)}")
        return f"Error: {str(e)}" 