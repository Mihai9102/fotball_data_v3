#!/usr/bin/env python3
"""
Script to find fixtures that have odds available using the SportMonks hasodds endpoint
"""

import sys
import logging
import argparse
from datetime import datetime, timedelta
from tabulate import tabulate

# Add parent directory to path
sys.path.append('/Users/mihaivictor/CascadeProjects/football_data/football_data_v3')

from api.sportmonks import SportMonksAPI
from config.leagues import SUPPORTED_LEAGUES, SUPPORTED_LEAGUE_IDS
from config.markets import MARKET_IDS, get_market_display_name
from database.operations import DatabaseManager
from processors.odds_processor import OddsProcessor

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def find_fixtures_with_odds(days_range=7, league_ids=None, market_id=None, fetch_odds=False):
    """
    Find fixtures that have odds available
    
    Args:
        days_range: Number of days to look ahead/behind (default: 7)
        league_ids: Optional list of league IDs to filter
        market_id: Optional market ID to filter
        fetch_odds: Whether to also fetch odds for the fixtures
    """
    api = SportMonksAPI()
    
    # Set date range
    start_date = (datetime.now() - timedelta(days=days_range//2)).strftime("%Y-%m-%d")
    end_date = (datetime.now() + timedelta(days=days_range//2)).strftime("%Y-%m-%d")
    
    # Define market filter
    market_ids = None
    if market_id:
        market_ids = [market_id]
        market_name = get_market_display_name(MARKET_IDS.get(market_id, str(market_id)))
        logger.info(f"Filtering fixtures with odds for market: {market_id} ({market_name})")
    
    logger.info(f"Finding fixtures with odds from {start_date} to {end_date}")
    
    # Get fixtures with odds
    fixtures, success = api.get_fixtures_with_odds(
        start_date=start_date,
        end_date=end_date,
        league_ids=league_ids,
        market_ids=market_ids
    )
    
    if not success or not fixtures:
        logger.warning("No fixtures with odds found")
        return
    
    logger.info(f"Found {len(fixtures)} fixtures with odds")
    
    # Display fixtures in a table
    table_data = []
    for i, fixture in enumerate(fixtures):
        # Extract fixture details
        fixture_id = fixture.get('id')
        date = fixture.get('starting_at', '').split('T')[0]
        time = fixture.get('starting_at', '').split('T')[1].split('.')[0] if 'T' in fixture.get('starting_at', '') else ''
        
        home_team = fixture.get('localTeam', {}).get('data', {}).get('name', 'Home')
        away_team = fixture.get('visitorTeam', {}).get('data', {}).get('name', 'Away')
        
        league = fixture.get('league', {}).get('data', {}).get('name', 'Unknown')
        
        table_data.append([
            i+1,
            fixture_id,
            f"{date} {time}",
            f"{home_team} vs {away_team}",
            league
        ])
    
    headers = ["#", "ID", "Date/Time", "Match", "League"]
    print("\nFixtures with Odds Available:")
    print(tabulate(table_data, headers=headers, tablefmt="grid"))
    
    # If requested, fetch odds for the first fixture as an example
    if fetch_odds and fixtures:
        fixture_id = fixtures[0].get('id')
        home_team = fixtures[0].get('localTeam', {}).get('data', {}).get('name', 'Home')
        away_team = fixtures[0].get('visitorTeam', {}).get('data', {}).get('name', 'Away')
        
        print(f"\nFetching odds for fixture {fixture_id}: {home_team} vs {away_team}")
        
        if market_id:
            odds, success = api.get_odds_by_fixture_and_market(fixture_id, market_id)
        else:
            odds, success = api.get_pre_match_odds_by_fixture_id(fixture_id)
        
        if success and odds:
            print(f"Found {len(odds)} odds entries for this fixture")
            
            # Count odds by market
            market_counts = {}
            for odd in odds:
                market_name = odd.get('market_name', 'Unknown')
                if market_name not in market_counts:
                    market_counts[market_name] = 0
                market_counts[market_name] += 1
                
            # Display market counts
            print("\nMarkets available:")
            for market, count in sorted(market_counts.items(), key=lambda x: x[1], reverse=True):
                print(f"  - {market}: {count} odds")
        else:
            print("No odds data found for this fixture")

def save_fixtures_with_odds(days_range=7, league_ids=None, market_id=None):
    """
    Find fixtures with odds and save them to the database
    
    Args:
        days_range: Number of days to look ahead/behind (default: 7)
        league_ids: Optional list of league IDs to filter
        market_id: Optional market ID to filter
    """
    api = SportMonksAPI()
    db = DatabaseManager()
    odds_processor = OddsProcessor(db_manager=db)
    
    # Set date range
    start_date = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    end_date = (datetime.now() + timedelta(days=days_range)).strftime("%Y-%m-%d")
    
    # Define market filter
    market_ids = None
    if market_id:
        market_ids = [market_id]
    
    logger.info(f"Finding fixtures with odds from {start_date} to {end_date}")
    
    # Get fixtures with odds
    fixtures, success = api.get_fixtures_with_odds(
        start_date=start_date,
        end_date=end_date,
        league_ids=league_ids,
        market_ids=market_ids
    )
    
    if not success or not fixtures:
        logger.warning("No fixtures with odds found")
        return
    
    logger.info(f"Found {len(fixtures)} fixtures with odds")
    
    # Save fixtures to database
    fixtures_saved = 0
    for fixture in fixtures:
        # Save match to database
        if db.save_match(fixture):
            fixtures_saved += 1
    
    logger.info(f"Saved {fixtures_saved} fixtures to the database")
    
    # Close database connections
    db.close()
    odds_processor.close()

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
    parser = argparse.ArgumentParser(description="Find fixtures that have odds available")
    parser.add_argument("--days", type=int, default=7, help="Number of days range to search (default: 7)")
    parser.add_argument("--market", type=int, help="Filter by market ID")
    parser.add_argument("--league", type=int, help="Filter by league ID")
    parser.add_argument("--fetch-odds", action="store_true", help="Fetch odds for the first fixture as example")
    parser.add_argument("--save", action="store_true", help="Save fixtures to database")
    parser.add_argument("--list-leagues", action="store_true", help="List all configured leagues")
    parser.add_argument("--list-markets", action="store_true", help="List known market types")
    
    args = parser.parse_args()
    
    if args.list_leagues:
        list_leagues()
        return
        
    if args.list_markets:
        list_markets()
        return
    
    league_ids = [args.league] if args.league else None
    
    if args.save:
        save_fixtures_with_odds(args.days, league_ids, args.market)
    else:
        find_fixtures_with_odds(args.days, league_ids, args.market, args.fetch_odds)

if __name__ == "__main__":
    main()
