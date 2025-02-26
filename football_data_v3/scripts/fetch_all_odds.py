#!/usr/bin/env python3
"""
Script to fetch all pre-match odds for upcoming matches across all supported leagues
"""

import sys
import logging
import argparse
import time
from datetime import datetime, timedelta
from tqdm import tqdm  # Install with: pip install tqdm

# Add parent directory to path
sys.path.append('/Users/mihaivictor/CascadeProjects/football_data/football_data_v3')

from api.sportmonks import SportMonksAPI
from database.operations import DatabaseManager
from processors.odds_processor import OddsProcessor
from config.leagues import SUPPORTED_LEAGUES, SUPPORTED_LEAGUE_IDS
from config.settings import get_start_date, get_end_date
from config.markets import get_market_display_name, MARKET_IDS

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def fetch_all_odds(days_ahead=14, batch_size=5, save_to_db=True):
    """
    Fetch all pre-match odds for upcoming matches across all supported leagues
    
    Args:
        days_ahead: Number of days ahead to fetch odds for
        batch_size: Number of leagues to process in each batch (to respect API limits)
        save_to_db: Whether to save the fetched data to the database
    """
    api = SportMonksAPI(use_cache=True)
    db = DatabaseManager() if save_to_db else None
    odds_processor = OddsProcessor(db_manager=db) if save_to_db else None
    
    start_date = datetime.now().strftime("%Y-%m-%d")
    end_date = (datetime.now() + timedelta(days=days_ahead)).strftime("%Y-%m-%d")
    
    logger.info(f"Fetching pre-match odds from {start_date} to {end_date} for {len(SUPPORTED_LEAGUE_IDS)} leagues")
    
    total_fixtures = 0
    total_odds = 0
    
    # Process leagues in batches to respect API rate limits
    league_batches = [SUPPORTED_LEAGUE_IDS[i:i + batch_size] for i in range(0, len(SUPPORTED_LEAGUE_IDS), batch_size)]
    
    for batch_idx, league_batch in enumerate(league_batches):
        logger.info(f"Processing batch {batch_idx + 1}/{len(league_batches)}: Leagues {league_batch}")
        
        # Step 1: Get fixtures for these leagues in the date range
        fixtures, success = api.get_fixtures_between_dates(
            start_date=start_date,
            end_date=end_date,
            include_odds=False,  # Don't include odds here to reduce API load
            league_ids=league_batch
        )
        
        if not success:
            logger.error(f"Failed to fetch fixtures for leagues {league_batch}")
            continue
        
        logger.info(f"Found {len(fixtures)} fixtures for leagues {league_batch}")
        total_fixtures += len(fixtures)
        
        # Step 2: For each fixture, get all pre-match odds
        for fixture in tqdm(fixtures, desc="Fetching odds"):
            fixture_id = fixture.get('id')
            if not fixture_id:
                continue
                
            # Get pre-match odds for this fixture
            odds_data, success = api.get_pre_match_odds_by_fixture_id(fixture_id)
            
            if not success or not odds_data:
                logger.warning(f"No odds data available for fixture {fixture_id}")
                continue
                
            total_odds += len(odds_data)
            logger.debug(f"Fetched {len(odds_data)} odds entries for fixture {fixture_id}")
            
            # Save to database if required
            if save_to_db and odds_processor:
                # First make sure the match exists in the database
                db.save_match(fixture)
                
                # Then process the odds
                processed = odds_processor.process_match_odds(fixture_id, odds_data)
                logger.debug(f"Processed {processed} odds for fixture {fixture_id}")
        
        # Sleep between batches to be kind to the API
        if batch_idx < len(league_batches) - 1:
            logger.info(f"Sleeping for 5 seconds before next batch...")
            time.sleep(5)
    
    logger.info(f"Completed fetching odds for {total_fixtures} fixtures")
    logger.info(f"Total odds entries: {total_odds}")
    
    if save_to_db and db:
        db.close()
    
    return total_fixtures, total_odds

def fetch_specific_market_odds(market_id, days_ahead=14, save_to_db=True):
    """
    Fetch odds for a specific market across all upcoming fixtures
    
    Args:
        market_id: Market ID to fetch
        days_ahead: Number of days ahead to fetch odds for
        save_to_db: Whether to save the fetched data to the database
    """
    api = SportMonksAPI(use_cache=True)
    db = DatabaseManager() if save_to_db else None
    odds_processor = OddsProcessor(db_manager=db) if save_to_db else None
    
    start_date = datetime.now().strftime("%Y-%m-%d")
    end_date = (datetime.now() + timedelta(days=days_ahead)).strftime("%Y-%m-%d")
    
    market_name = get_market_display_name(MARKET_IDS.get(market_id, str(market_id)))
    logger.info(f"Fetching odds for market: {market_id} ({market_name}) from {start_date} to {end_date}")
    
    # First get all fixtures in the date range
    fixtures, success = api.get_fixtures_between_dates(
        start_date=start_date,
        end_date=end_date,
        include_odds=False,
        league_ids=SUPPORTED_LEAGUE_IDS
    )
    
    if not success:
        logger.error("Failed to fetch fixtures")
        return 0, 0
    
    logger.info(f"Found {len(fixtures)} fixtures")
    
    total_odds = 0
    processed_fixtures = 0
    
    # For each fixture, get odds for the specific market
    for fixture in tqdm(fixtures, desc=f"Fetching {market_name} odds"):
        fixture_id = fixture.get('id')
        if not fixture_id:
            continue
            
        # Get odds for this fixture and market
        odds_data, success = api.get_odds_by_fixture_and_market(fixture_id, market_id)
        
        if not success or not odds_data:
            continue
            
        total_odds += len(odds_data)
        processed_fixtures += 1
        
        # Save to database if required
        if save_to_db and odds_processor:
            # First make sure the match exists in the database
            db.save_match(fixture)
            
            # Then process the odds
            processed = odds_processor.process_match_odds(fixture_id, odds_data)
            logger.debug(f"Processed {processed} odds for fixture {fixture_id}")
    
    logger.info(f"Completed fetching {market_name} odds for {processed_fixtures} fixtures")
    logger.info(f"Total odds entries: {total_odds}")
    
    if save_to_db and db:
        db.close()
    
    return processed_fixtures, total_odds

def list_leagues():
    """List all configured leagues"""
    print("\nSupported Leagues:")
    print("-" * 50)
    print(f"{'ID':<8} {'League Name'}")
    print("-" * 50)
    
    for league_id, league_name in SUPPORTED_LEAGUES.items():
        print(f"{league_id:<8} {league_name}")

def list_markets():
    """List all available markets"""
    print("\nCommon Markets:")
    print("-" * 50)
    print(f"{'ID':<8} {'Market Type'}")
    print("-" * 50)
    
    for market_id, market_type in MARKET_IDS.items():
        print(f"{market_id:<8} {get_market_display_name(market_type)}")

def main():
    parser = argparse.ArgumentParser(description="Fetch all pre-match odds for upcoming matches")
    parser.add_argument("--days", type=int, default=14, help="Number of days ahead to fetch odds")
    parser.add_argument("--batch-size", type=int, default=5, help="Number of leagues to process in each batch")
    parser.add_argument("--dry-run", action="store_true", help="Don't save data to database (preview mode)")
    parser.add_argument("--market", type=int, help="Fetch odds for a specific market ID only")
    parser.add_argument("--list-leagues", action="store_true", help="List all configured leagues")
    parser.add_argument("--list-markets", action="store_true", help="List known market types")
    
    args = parser.parse_args()
    
    if args.list_leagues:
        list_leagues()
        return
        
    if args.list_markets:
        list_markets()
        return
    
    save_to_db = not args.dry_run
    
    if args.market:
        fetch_specific_market_odds(args.market, args.days, save_to_db)
    else:
        fetch_all_odds(args.days, args.batch_size, save_to_db)

if __name__ == "__main__":
    main()
