#!/usr/bin/env python3
"""
Script to collect odds data from SportMonks API and store in database.
Handles both pre-match and in-play odds.
"""

import sys
import os
import logging
import argparse
from datetime import datetime, timedelta
import json
from typing import Dict, List, Tuple

# Add parent directory to path
sys.path.append('/Users/mihaivictor/CascadeProjects/football_data/football_data_v3')

from api.sportmonks import SportMonksAPI
from api.odds import normalize_odds_data, convert_odds_for_db
from database.models import Session, Match, Odd
from config.settings import get_start_date, get_end_date
from config.leagues import SUPPORTED_LEAGUE_IDS
from config.markets import TRACKED_MARKETS

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def collect_pre_match_odds(start_date: str = None, end_date: str = None, league_ids: List[int] = None, 
                         bookmaker_ids: List[int] = None, market_ids: List[int] = None,
                         save_to_db: bool = True, save_raw: bool = False, output_dir: str = "outputs"):
    """
    Collect pre-match odds from SportMonks API
    
    Args:
        start_date: Start date for fixture search (YYYY-MM-DD)
        end_date: End date for fixture search (YYYY-MM-DD)
        league_ids: List of league IDs to filter
        bookmaker_ids: List of bookmaker IDs to filter
        market_ids: List of market IDs to filter
        save_to_db: Whether to save data to the database
        save_raw: Whether to save raw API responses
        output_dir: Directory to save raw data
    
    Returns:
        Tuple of (success count, total count)
    """
    # Use default date range if not provided
    if not start_date:
        start_date = get_start_date()
    if not end_date:
        end_date = get_end_date()
        
    # Use default leagues if not provided
    if not league_ids:
        league_ids = SUPPORTED_LEAGUE_IDS
    
    # Initialize API client
    api = SportMonksAPI()
    
    logger.info(f"Collecting pre-match odds for fixtures from {start_date} to {end_date}")
    logger.info(f"Leagues: {league_ids}")
    
    # Step 1: Get fixtures with odds in the date range
    fixtures, success = api.get_fixtures_with_odds(
        start_date=start_date,
        end_date=end_date,
        league_ids=league_ids,
        bookmaker_ids=bookmaker_ids,
        market_ids=market_ids
    )
    
    if not success or not fixtures:
        logger.warning("Failed to fetch fixtures with odds or no fixtures found")
        return 0, 0
    
    logger.info(f"Found {len(fixtures)} fixtures with odds. Processing...")
    
    # Step 2: Collect fixture IDs
    fixture_ids = [fixture["id"] for fixture in fixtures]
    
    # Step 3: Get odds in batches (process one fixture at a time to avoid memory issues)
    success_count = 0
    total_matches = len(fixture_ids)
    
    for i, fixture_id in enumerate(fixture_ids):
        logger.info(f"Processing fixture {i+1}/{total_matches} (ID: {fixture_id})")
        
        # Get odds for this fixture
        odds_data, odds_success = api.get_pre_match_odds_by_fixture_id(
            fixture_id=fixture_id,
            bookmaker_ids=bookmaker_ids,
            market_ids=market_ids
        )
        
        if not odds_success or not odds_data:
            logger.warning(f"Failed to fetch odds for fixture {fixture_id}")
            continue
            
        # Save raw data if requested
        if save_raw:
            os.makedirs(output_dir, exist_ok=True)
            with open(f"{output_dir}/odds_prematch_{fixture_id}.json", "w") as f:
                json.dump(odds_data, f, indent=2)
        
        # Process and normalize the odds data
        normalized_odds = normalize_odds_data({"data": odds_data})
        
        if not normalized_odds:
            logger.warning(f"No valid odds found for fixture {fixture_id}")
            continue
                
        logger.info(f"Found {len(normalized_odds)} odds entries for fixture {fixture_id}")
        
        # Save to database if requested
        if save_to_db:
            db_records = convert_odds_for_db(normalized_odds)
            success_count += save_odds_to_db(db_records, fixture_id)
    
    logger.info(f"Pre-match odds collection complete. Processed {success_count} of {total_matches} matches.")
    return success_count, total_matches

def collect_inplay_odds(league_ids: List[int] = None, bookmaker_ids: List[int] = None, 
                      market_ids: List[int] = None, save_to_db: bool = True, 
                      save_raw: bool = False, output_dir: str = "outputs"):
    """
    Collect in-play (live) odds from SportMonks API
    
    Args:
        league_ids: List of league IDs to filter
        bookmaker_ids: List of bookmaker IDs to filter
        market_ids: List of market IDs to filter
        save_to_db: Whether to save data to the database
        save_raw: Whether to save raw API responses
        output_dir: Directory to save raw data
    
    Returns:
        Tuple of (success count, total count)
    """
    # Use default leagues if not provided
    if not league_ids:
        league_ids = SUPPORTED_LEAGUE_IDS
    
    # Initialize API client
    api = SportMonksAPI()
    
    logger.info("Collecting in-play odds for live matches")
    
    # Step 1: Get live matches
    live_matches, success = api.get_live_matches_with_odds(league_ids=league_ids)
    
    if not success or not live_matches:
        logger.warning("Failed to fetch live matches with odds or no matches found")
        return 0, 0
    
    logger.info(f"Found {len(live_matches)} live matches. Processing...")
    
    # Step 2: Collect match IDs
    match_ids = [match["id"] for match in live_matches]
    
    # Step 3: Get in-play odds for these matches
    success_count = 0
    total_matches = len(match_ids)
    
    for i, match_id in enumerate(match_ids):
        logger.info(f"Processing live match {i+1}/{total_matches} (ID: {match_id})")
        
        # Get in-play odds for this match
        odds_data, odds_success = api.get_inplay_odds_by_fixture_id(
            fixture_id=match_id,
            bookmaker_ids=bookmaker_ids,
            market_ids=market_ids
        )
        
        if not odds_success or not odds_data:
            logger.warning(f"Failed to fetch in-play odds for match {match_id}")
            continue
            
        # Save raw data if requested
        if save_raw:
            os.makedirs(output_dir, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            with open(f"{output_dir}/odds_inplay_{match_id}_{timestamp}.json", "w") as f:
                json.dump(odds_data, f, indent=2)
        
        # Process and normalize the odds data
        normalized_odds = normalize_odds_data({"data": odds_data})
        
        if not normalized_odds:
            logger.warning(f"No valid in-play odds found for match {match_id}")
            continue
                
        logger.info(f"Found {len(normalized_odds)} in-play odds entries for match {match_id}")
        
        # Save to database if requested
        if save_to_db:
            # Mark all odds as live
            for odd in normalized_odds:
                odd["is_live"] = True
                
            db_records = convert_odds_for_db(normalized_odds)
            success_count += save_odds_to_db(db_records, match_id)
    
    logger.info(f"In-play odds collection complete. Processed {success_count} of {total_matches} matches.")
    return success_count, total_matches

def save_odds_to_db(odds_records: List[Dict], fixture_id: int) -> int:
    """
    Save odd records to the database
    
    Args:
        odds_records: List of odd records
        fixture_id: Associated fixture ID
        
    Returns:
        1 if successful, 0 if not
    """
    session = Session()
    try:
        # Check if match exists
        match = session.query(Match).filter(Match.id == fixture_id).first()
        if not match:
            # Create a basic match record if it doesn't exist
            logger.warning(f"Match with ID {fixture_id} not found in database, creating minimal record")
            match = Match(
                id=fixture_id,
                starting_at_timestamp=datetime.utcnow()  # Placeholder, will be updated later
            )
            session.add(match)
            session.commit()
        
        # Delete existing odds for this match (for the same markets and bookmakers)
        existing_bookmakers = set()
        existing_markets = set()
        
        for record in odds_records:
            existing_bookmakers.add(record.get("bookmaker_id"))
            existing_markets.add(record.get("market_name"))
        
        # Only delete existing records that match the bookmakers and markets we're updating
        if odds_records[0].get("is_live", False):
            # For live odds, delete previous live odds for the same bookmaker/market
            for odd in session.query(Odd).filter(
                Odd.match_id == fixture_id,
                Odd.is_live == True,
                Odd.bookmaker_id.in_(existing_bookmakers)
            ).all():
                if odd.market_name in existing_markets:
                    session.delete(odd)
        else:
            # For pre-match odds, delete all pre-match odds for the same bookmaker/market
            for odd in session.query(Odd).filter(
                Odd.match_id == fixture_id,
                Odd.is_live == False,
                Odd.bookmaker_id.in_(existing_bookmakers)
            ).all():
                if odd.market_name in existing_markets:
                    session.delete(odd)
        
        # Create odd objects and add to session
        for record in odds_records:
            # Filter out markets we don't care about
            market = record.get("normalized_market")
            if market not in TRACKED_MARKETS:
                continue
                
            odd = Odd(
                match_id=record["match_id"],
                bookmaker_id=record["bookmaker_id"],
                bookmaker_name=record["bookmaker_name"],
                market_id=record.get("market_id"),
                market_name=record["market_name"],
                normalized_market=record["normalized_market"],
                selection_id=record.get("selection_id"),
                selection_name=record["selection_name"],
                normalized_selection=record["normalized_selection"],
                value=record["value"],
                implied_probability=record["implied_probability"],
                is_live=record.get("is_live", False)
            )
            session.add(odd)
        
        # Commit the changes
        session.commit()
        return 1
        
    except Exception as e:
        logger.error(f"Error saving odds for match {fixture_id}: {str(e)}")
        session.rollback()
        return 0
        
    finally:
        session.close()

def main():
    parser = argparse.ArgumentParser(description="Collect odds data from SportMonks API")
    parser.add_argument('--type', choices=['prematch', 'inplay', 'both'], default='both', 
                      help='Type of odds to collect (prematch, inplay, or both)')
    parser.add_argument('--start-date', help='Start date (YYYY-MM-DD) for fixture search')
    parser.add_argument('--end-date', help='End date (YYYY-MM-DD) for fixture search')
    parser.add_argument('--league', type=int, action='append', help='League ID (can be specified multiple times)')
    parser.add_argument('--bookmaker', type=int, action='append', help='Bookmaker ID (can be specified multiple times)')
    parser.add_argument('--save-raw', action='store_true', help='Save raw API responses')
    parser.add_argument('--output-dir', default='outputs', help='Directory to save raw data')
    parser.add_argument('--no-db', action='store_true', help='Skip saving to database')
    
    args = parser.parse_args()
    
    if args.type in ['prematch', 'both']:
        collect_pre_match_odds(
            start_date=args.start_date,
            end_date=args.end_date,
            league_ids=args.league,
            bookmaker_ids=args.bookmaker,
            save_to_db=not args.no_db,
            save_raw=args.save_raw,
            output_dir=args.output_dir
        )
    
    if args.type in ['inplay', 'both']:
        collect_inplay_odds(
            league_ids=args.league,
            bookmaker_ids=args.bookmaker,
            save_to_db=not args.no_db,
            save_raw=args.save_raw,
            output_dir=args.output_dir
        )

if __name__ == "__main__":
    main()
