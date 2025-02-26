#!/usr/bin/env python3
"""
Script to check API rate limit status and other system information
"""

import sys
import logging
import argparse
from datetime import datetime
import time

# Add parent directory to path
sys.path.append('/Users/mihaivictor/CascadeProjects/football_data/football_data_v3')

from api.sportmonks import SportMonksAPI
from config.leagues import SUPPORTED_LEAGUES
from database.operations import DatabaseManager

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def check_rate_limits():
    """Check current API rate limit status"""
    api = SportMonksAPI(use_cache=False)
    
    logger.info("Making a test request to check rate limits...")
    # Use a lightweight API endpoint that doesn't consume much of quota
    data, success = api._make_request('leagues', {'per_page': 1})
    
    if not success:
        logger.error("Failed to check rate limits. API request unsuccessful.")
        return

    limiter = api.rate_limiter
    
    if limiter.limit is None or limiter.remaining is None:
        logger.warning("Couldn't retrieve rate limit information from API")
        return
        
    print("\n=== RATE LIMIT STATUS ===")
    print(f"Limit:     {limiter.limit} requests per minute")
    print(f"Remaining: {limiter.remaining} requests")
    
    if limiter.reset_timestamp:
        reset_time = datetime.fromtimestamp(limiter.reset_timestamp)
        now = datetime.now()
        time_until_reset = reset_time - now
        print(f"Reset:     {reset_time.strftime('%H:%M:%S')} ({time_until_reset.total_seconds():.0f}s)")
    
    # Calculate usage percentage
    if limiter.limit and limiter.remaining is not None:
        usage_percent = ((limiter.limit - limiter.remaining) / limiter.limit) * 100
        print(f"Usage:     {usage_percent:.1f}%")
        
        # Warning if usage is high
        if usage_percent > 80:
            print("\n⚠️  WARNING: Rate limit usage is high! Be careful with additional requests.")
    
def check_database_status():
    """Check database status and statistics"""
    db = DatabaseManager()
    
    try:
        match_count = len(db.get_matches())
        
        print("\n=== DATABASE STATUS ===")
        print(f"Total matches:     {match_count}")
        
        # Count by league
        print("\nMatches by league:")
        for league_id in SUPPORTED_LEAGUES:
            league_name = SUPPORTED_LEAGUES[league_id]
            count = len(db.get_matches(league_ids=[league_id]))
            if count > 0:
                print(f"  {league_name}: {count}")
    
    except Exception as e:
        logger.error(f"Error checking database status: {e}")
    finally:
        db.close()

def main():
    parser = argparse.ArgumentParser(description="Check system status")
    parser.add_argument("--api", action="store_true", help="Check API rate limits")
    parser.add_argument("--db", action="store_true", help="Check database status")
    
    args = parser.parse_args()
    
    # If no specific checks requested, do all
    do_all = not (args.api or args.db)
    
    if args.api or do_all:
        check_rate_limits()
        
    if args.db or do_all:
        check_database_status()

if __name__ == "__main__":
    main()
