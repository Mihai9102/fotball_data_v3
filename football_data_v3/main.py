import argparse
import logging
import sys
import time
from datetime import datetime
from logging.handlers import RotatingFileHandler

from database.models import create_tables
from scheduler.jobs import run_scheduler_in_thread
from processors.match_processor import MatchProcessor
from config.settings import LOG_LEVEL, LOG_FILE

def setup_logging():
    """Set up logging configuration"""
    log_level = getattr(logging, LOG_LEVEL.upper(), logging.INFO)
    
    # Create formatter
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # Create handlers
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    
    file_handler = RotatingFileHandler(LOG_FILE, maxBytes=10485760, backupCount=5)  # 10MB with 5 backups
    file_handler.setFormatter(formatter)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)
    
    return root_logger

def run_once(start_date=None, end_date=None):
    """Run data collection once"""
    processor = MatchProcessor()
    try:
        match_count = processor.process_matches_in_date_range(start_date, end_date)
        logging.info(f"Processed {match_count} matches")
    finally:
        processor.close()

def main():
    """Main entry point"""
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="Football Data Collection from SportMonks API")
    parser.add_argument("--init-db", action="store_true", help="Initialize the database")
    parser.add_argument("--run-once", action="store_true", help="Run data collection once and exit")
    parser.add_argument("--start-date", type=str, help="Start date for fixtures (YYYY-MM-DD)")
    parser.add_argument("--end-date", type=str, help="End date for fixtures (YYYY-MM-DD)")
    
    args = parser.parse_args()
    
    # Set up logging
    logger = setup_logging()
    logger.info("Starting Football Data Collector")
    
    # Initialize database if requested
    if args.init_db:
        logger.info("Initializing database...")
        create_tables()
        logger.info("Database initialization complete")
    
    # Run once or start scheduler
    if args.run_once:
        logger.info("Running single data collection job")
        run_once(args.start_date, args.end_date)
    else:
        logger.info("Starting scheduler for regular data collection")
        scheduler_thread = run_scheduler_in_thread()
        
        try:
            # Keep the main thread alive to allow the scheduler to run
            while True:
                time.sleep(60)
        except KeyboardInterrupt:
            logger.info("Keyboard interrupt received, shutting down...")
            sys.exit(0)

if __name__ == "__main__":
    main()