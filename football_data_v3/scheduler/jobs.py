import logging
import schedule
import time
import threading
from datetime import datetime

from processors.match_processor import MatchProcessor
from config.settings import SCHEDULE_INTERVAL_HOURS

logger = logging.getLogger(__name__)

def collect_data_job():
    """Job to collect data from SportMonks API"""
    logger.info("Starting scheduled data collection job")
    
    processor = MatchProcessor()
    try:
        match_count = processor.process_matches_in_date_range()
        logger.info(f"Scheduled job completed. Processed {match_count} matches")
    except Exception as e:
        logger.error(f"Error in scheduled job: {str(e)}")
    finally:
        processor.close()

def setup_schedule():
    """Set up the schedule for data collection"""
    # Schedule job to run every SCHEDULE_INTERVAL_HOURS
    schedule.every(SCHEDULE_INTERVAL_HOURS).hours.do(collect_data_job)
    
    # Also run immediately at startup
    schedule.every().day.at("00:00").do(collect_data_job)
    
    logger.info(f"Scheduled data collection every {SCHEDULE_INTERVAL_HOURS} hours")

def run_scheduler():
    """Run the scheduler loop"""
    setup_schedule()
    
    # Run the job immediately
    collect_data_job()
    
    # Run the scheduler loop
    while True:
        schedule.run_pending()
        time.sleep(60)  # Check every minute

def run_scheduler_in_thread():
    """Run the scheduler in a separate thread"""
    thread = threading.Thread(target=run_scheduler, daemon=True)
    thread.start()
    return thread
