#!/usr/bin/env python3
"""
Script to update the odds database with the latest pre-match and in-play odds.
Can be scheduled to run periodically to keep odds data fresh.
"""

import sys
import os
import logging
import argparse
from datetime import datetime, timedelta
import time
import traceback
import json

# Add parent directory to path
sys.path.append('/Users/mihaivictor/CascadeProjects/football_data/football_data_v3')

from scripts.odds_collector import collect_pre_match_odds, collect_inplay_odds
from api.sportmonks import SportMonksAPI
from api.account import SportMonksAccount
from database.models import Session, Match, Odd
from config.settings import get_start_date, get_end_date, API_RETRY_COUNT
from config.leagues import SUPPORTED_LEAGUE_IDS

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("logs/update_odds_db.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def ensure_db_structure():
    """Ensure the database structure is ready for odds data"""
    # Create session to check database
    session = Session()
    try:
        # Check if we can query the Odd table
        try:
            session.query(Odd).first()
            logger.info("Database structure check passed")
            return True
        except Exception as e:
            logger.error(f"Database structure issue: {str(e)}")
            return False
    finally:
        session.close()

def get_upcoming_match_ids(days_ahead=3, league_ids=None):
    """
    Get IDs of upcoming matches to collect odds for
    
    Args:
        days_ahead: Number of days ahead to look
        league_ids: List of league IDs to filter
        
    Returns:
        List of match IDs
    """
    api = SportMonksAPI()
    
    # Calculate date range
    start_date = datetime.now().strftime("%Y-%m-%d")
    end_date = (datetime.now() + timedelta(days=days_ahead)).strftime("%Y-%m-%d")
    
    # Get fixtures
    fixtures, success = api.get_fixtures_between_dates(
        start_date=start_date,
        end_date=end_date,
        league_ids=league_ids
    )
    
    if not success or not fixtures:
        logger.warning("No upcoming fixtures found")
        return []
    
    # Extract fixture IDs
    fixture_ids = [fixture["id"] for fixture in fixtures]
    logger.info(f"Found {len(fixture_ids)} upcoming fixtures")
    
    return fixture_ids

def update_prematch_odds(days_ahead=3, league_ids=None, bookmaker_ids=None):
    """
    Update pre-match odds for upcoming matches
    
    Args:
        days_ahead: Number of days ahead to look
        league_ids: List of league IDs to filter
        bookmaker_ids: List of bookmaker IDs to filter
        
    Returns:
        Tuple of (success count, total count)
    """
    logger.info("Updating pre-match odds...")
    
    # Calculate date range
    start_date = datetime.now().strftime("%Y-%m-%d")
    end_date = (datetime.now() + timedelta(days=days_ahead)).strftime("%Y-%m-%d")
    
    # Use default leagues if not provided
    if not league_ids:
        league_ids = SUPPORTED_LEAGUE_IDS
    
    # Collect pre-match odds
    success_count, total_count = collect_pre_match_odds(
        start_date=start_date,
        end_date=end_date,
        league_ids=league_ids,
        bookmaker_ids=bookmaker_ids,
        save_to_db=True
    )
    
    return success_count, total_count

def update_inplay_odds(league_ids=None, bookmaker_ids=None):
    """
    Update in-play odds for live matches
    
    Args:
        league_ids: List of league IDs to filter
        bookmaker_ids: List of bookmaker IDs to filter
        
    Returns:
        Tuple of (success count, total count)
    """
    logger.info("Updating in-play odds...")
    
    # Use default leagues if not provided
    if not league_ids:
        league_ids = SUPPORTED_LEAGUE_IDS
    
    # Collect in-play odds
    success_count, total_count = collect_inplay_odds(
        league_ids=league_ids,
        bookmaker_ids=bookmaker_ids,
        save_to_db=True
    )
    
    return success_count, total_count

def loop_inplay_updates(interval_minutes=5, max_iterations=None, 
                      league_ids=None, bookmaker_ids=None):
    """
    Continuously update in-play odds at regular intervals
    
    Args:
        interval_minutes: Minutes between updates
        max_iterations: Maximum number of iterations (None for infinite)
        league_ids: List of league IDs to filter
        bookmaker_ids: List of bookmaker IDs to filter
    """
    iterations = 0
    
    logger.info(f"Starting in-play odds update loop (interval: {interval_minutes} minutes)")
    
    try:
        while max_iterations is None or iterations < max_iterations:
            # Update timestamp
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            logger.info(f"Update cycle {iterations + 1} at {timestamp}")
            
            try:
                # Update in-play odds
                success_count, total_count = update_inplay_odds(
                    league_ids=league_ids,
                    bookmaker_ids=bookmaker_ids
                )
                
                logger.info(f"Updated in-play odds for {success_count}/{total_count} matches")
                
                # Check if there are any live matches
                if total_count == 0:
                    logger.info("No live matches found. Waiting for next cycle...")
                
            except Exception as e:
                logger.error(f"Error updating in-play odds: {str(e)}")
                logger.debug(traceback.format_exc())
            
            # Increment counter
            iterations += 1
            
            if max_iterations is not None and iterations >= max_iterations:
                logger.info(f"Reached maximum iterations ({max_iterations}). Stopping.")
                break
            
            # Wait for next update
            logger.info(f"Waiting {interval_minutes} minutes until next update...")
            time.sleep(interval_minutes * 60)
            
    except KeyboardInterrupt:
        logger.info("Update loop interrupted by user.")

def check_api_limits():
    """Check API rate limits and usage"""
    account = SportMonksAccount()
    rate_limits = account.get_rate_limit_info()
    
    if not rate_limits:
        logger.warning("Could not retrieve rate limit information")
        return False
    
    logger.info("=== API Rate Limits ===")
    
    if "limit" in rate_limits:
        logger.info(f"Rate limit: {rate_limits['limit']} requests per minute")
    
    if "remaining" in rate_limits:
        logger.info(f"Remaining: {rate_limits['remaining']} requests")
        
        # Check if we're close to the limit
        if rate_limits["remaining"] < 100:  # Arbitrary threshold
            logger.warning(f"Low on API requests: only {rate_limits['remaining']} remaining")
            return False
    
    if "usage" in rate_limits and "count" in rate_limits["usage"]:
        logger.info(f"Usage this period: {rate_limits['usage']['count']} requests")
    
    return True

def main():
    parser = argparse.ArgumentParser(description="Update odds database")
    parser.add_argument('--type', choices=['prematch', 'inplay', 'both'], default='both', 
                      help='Type of odds to update (prematch, inplay, or both)')
    parser.add_argument('--days', '-d', type=int, default=3, 
                      help='Number of days ahead to look for fixtures')
    parser.add_argument('--league', '-l', type=int, action='append', 
                      help='League ID (can be specified multiple times)')
    parser.add_argument('--bookmaker', '-b', type=int, action='append', 
                      help='Bookmaker ID (can be specified multiple times)')
    parser.add_argument('--loop', action='store_true', 
                      help='Run in continuous loop mode for in-play odds')
    parser.add_argument('--interval', '-i', type=int, default=5, 
                      help='Update interval in minutes (for loop mode)')
    parser.add_argument('--iterations', type=int, 
                      help='Maximum number of update iterations (for loop mode)')
    parser.add_argument('--check-limits', action='store_true', 
                      help='Check API rate limits before updating')
    
    args = parser.parse_args()
    
    # Create output directory for logs if it doesn't exist
    os.makedirs("logs", exist_ok=True)
    
    # Check database structure
    if not ensure_db_structure():
        logger.error("Database structure issue. Please check your database setup.")
        return
    
    # Check API limits if requested
    if args.check_limits:
        if not check_api_limits():
            logger.warning("API limits check failed. Continuing anyway...")
    
    # Handle different update types
    if args.loop and args.type in ['inplay', 'both']:
        # Continuous update mode for in-play odds
        loop_inplay_updates(
            interval_minutes=args.interval,
            max_iterations=args.iterations,
            league_ids=args.league,
            bookmaker_ids=args.bookmaker
        )
    else:
        # One-time update
        if args.type in ['prematch', 'both']:
            success_count, total_count = update_prematch_odds(
                days_ahead=args.days,
                league_ids=args.league,
                bookmaker_ids=args.bookmaker
            )
            logger.info(f"Updated pre-match odds for {success_count}/{total_count} matches")
            
        if args.type in ['inplay', 'both']:
            success_count, total_count = update_inplay_odds(
                league_ids=args.league,
                bookmaker_ids=args.bookmaker
            )
            logger.info(f"Updated in-play odds for {success_count}/{total_count} matches")

if __name__ == "__main__":
    main()
