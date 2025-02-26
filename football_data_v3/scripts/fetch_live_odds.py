#!/usr/bin/env python3
"""
Script to fetch and display live in-play odds for all supported leagues
"""

import sys
import logging
import argparse
import time
from datetime import datetime
from tabulate import tabulate
from typing import Dict, List

# Add parent directory to path
sys.path.append('/Users/mihaivictor/CascadeProjects/football_data/football_data_v3')

from api.sportmonks import SportMonksAPI
from database.operations import DatabaseManager
from processors.odds_processor import OddsProcessor
from config.leagues import SUPPORTED_LEAGUES, SUPPORTED_LEAGUE_IDS
from config.markets import get_market_display_name, normalize_market_name, MARKET_IDS

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def fetch_live_matches():
    """Fetch all currently live matches across supported leagues"""
    api = SportMonksAPI(use_cache=False)  # Always disable cache for live data
    
    # Get all live matches across supported leagues
    live_matches, success = api.get_live_matches_with_odds()
    
    if not success or not live_matches:
        print("No live matches found at the moment.")
        return []
    
    print(f"Found {len(live_matches)} live matches across supported leagues.")
    return live_matches

def display_live_matches(live_matches):
    """Display a table of live matches"""
    if not live_matches:
        return
    
    table_data = []
    for i, match in enumerate(live_matches):
        # Extract match details
        match_id = match.get('id')
        
        home_team = match.get('localTeam', {}).get('data', {}).get('name', 'Home')
        away_team = match.get('visitorTeam', {}).get('data', {}).get('name', 'Away')
        
        league = match.get('league', {}).get('data', {}).get('name', 'Unknown')
        
        # Get score
        local_score = match.get('scores', {}).get('localteam_score', 0)
        visitor_score = match.get('scores', {}).get('visitorteam_score', 0)
        score = f"{local_score} - {visitor_score}"
        
        # Get match status and minute
        status = match.get('status', '')
        minute = match.get('minute', '')
        match_time = f"{status} ({minute}')" if minute else status
        
        table_data.append([
            i+1,
            match_id,
            f"{home_team} vs {away_team}",
            score,
            match_time,
            league
        ])
    
    headers = ["#", "ID", "Match", "Score", "Status", "League"]
    print("\nLive Matches:")
    print(tabulate(table_data, headers=headers, tablefmt="grid"))
    print("\nUse the ID to fetch detailed odds: fetch_live_odds.py --match <ID>")

def fetch_and_display_live_odds(match_id, market_id=None):
    """Fetch and display live odds for a specific match"""
    api = SportMonksAPI(use_cache=False)  # Always disable cache for live data
    
    # First get the match details
    match, success = api.get_fixture_by_id(match_id)
    if not success or not match:
        print(f"Failed to get match with ID {match_id}")
        return
    
    # Get match details
    home_team = match.get('localTeam', {}).get('data', {}).get('name', 'Home')
    away_team = match.get('visitorTeam', {}).get('data', {}).get('name', 'Away')
    league = match.get('league', {}).get('data', {}).get('name', 'Unknown')
    local_score = match.get('scores', {}).get('localteam_score', 0)
    visitor_score = match.get('scores', {}).get('visitorteam_score', 0)
    status = match.get('status', '')
    minute = match.get('minute', '')
    
    print(f"\n=== LIVE MATCH: {home_team} vs {away_team} ===")
    print(f"League: {league}")
    print(f"Score: {local_score} - {visitor_score}")
    print(f"Status: {status} Minute: {minute}")
    
    # Get in-play odds
    if market_id:
        odds_data, success = api.get_inplay_odds_by_fixture_id(
            fixture_id=match_id, 
            market_ids=[market_id]
        )
        market_filter = f"for market ID {market_id}"
    else:
        odds_data, success = api.get_inplay_odds_by_fixture_id(match_id)
        market_filter = "across all markets"
    
    if not success or not odds_data:
        print(f"No live in-play odds available {market_filter}")
        return
    
    print(f"Found {len(odds_data)} live odds entries {market_filter}")
    
    # Group odds by market for display
    odds_by_market = {}
    for odd in odds_data:
        market_id = odd.get('market_id')
        market_name = odd.get('market_name', 'Unknown Market')
        
        if market_id not in odds_by_market:
            odds_by_market[market_id] = {
                'name': market_name,
                'normalized_name': normalize_market_name(market_name),
                'bookmakers': {}
            }
            
        bookmaker_id = odd.get('bookmaker_id')
        bookmaker_name = odd.get('bookmaker_name', 'Unknown Bookmaker')
        
        if bookmaker_id not in odds_by_market[market_id]['bookmakers']:
            odds_by_market[market_id]['bookmakers'][bookmaker_id] = {
                'name': bookmaker_name,
                'selections': {}
            }
            
        selection = odd.get('selection_name', '')
        value = odd.get('value', 0.0)
        
        odds_by_market[market_id]['bookmakers'][bookmaker_id]['selections'][selection] = value
    
    # Display odds for each market
    for market_id, market_info in odds_by_market.items():
        normalized_market = market_info['normalized_name']
        
        print(f"\n--- LIVE MARKET: {market_info['name']} ---")
        
        # Create table of odds by bookmaker
        table_data = []
        headers = ['Bookmaker']
        
        # Get all unique selections across all bookmakers for this market
        all_selections = set()
        for bookmaker_info in market_info['bookmakers'].values():
            all_selections.update(bookmaker_info['selections'].keys())
            
        # Sort selections for consistent display
        sorted_selections = sorted(all_selections)
        headers.extend(sorted_selections)
        
        # Build table rows
        for bookmaker_id, bookmaker_info in market_info['bookmakers'].items():
            row = [bookmaker_info['name']]
            
            # Add value for each selection
            for selection in sorted_selections:
                value = bookmaker_info['selections'].get(selection, '')
                row.append(f"{value:.2f}" if value else '')
                
            table_data.append(row)
        
        # Display the table
        if table_data:
            print(tabulate(table_data, headers=headers))

def monitor_live_odds(match_id, market_id=None, refresh_seconds=30):
    """Monitor live odds for a specific match with periodic refresh"""
    try:
        while True:
            # Clear screen (works on most terminals)
            print("\033c", end="")
            
            print(f"Live Odds Monitor - Updated: {datetime.now().strftime('%H:%M:%S')}")
            print(f"(Refreshing every {refresh_seconds} seconds, press Ctrl+C to quit)")
            
            fetch_and_display_live_odds(match_id, market_id)
            
            print(f"\nNext update in {refresh_seconds} seconds...")
            time.sleep(refresh_seconds)
    except KeyboardInterrupt:
        print("\nLive monitoring stopped.")

def list_live_markets(match_id):
    """List all available markets for a live match"""
    api = SportMonksAPI(use_cache=False)
    
    # Get all in-play odds for the match
    odds_data, success = api.get_inplay_odds_by_fixture_id(match_id)
    
    if not success or not odds_data:
        print(f"No live odds available for match {match_id}")
        return
    
    # Extract unique markets
    markets = {}
    for odd in odds_data:
        market_id = odd.get('market_id')
        market_name = odd.get('market_name')
        if market_id and market_name and market_id not in markets:
            markets[market_id] = market_name
    
    # Display markets
    if markets:
        print(f"\nAvailable live markets for match {match_id}:")
        print("-" * 50)
        print(f"{'ID':<8} {'Market Name'}")
        print("-" * 50)
        
        for market_id, market_name in sorted(markets.items()):
            print(f"{market_id:<8} {market_name}")
    else:
        print(f"No markets found for match {match_id}")

def main():
    parser = argparse.ArgumentParser(description="Fetch and display live in-play odds")
    parser.add_argument("--list", action="store_true", help="List all live matches")
    parser.add_argument("--match", type=int, help="Fetch odds for a specific match ID")
    parser.add_argument("--market", type=int, help="Specific market ID to filter by")
    parser.add_argument("--markets", action="store_true", help="List available markets for a match")
    parser.add_argument("--monitor", action="store_true", help="Continuously monitor odds with refresh")
    parser.add_argument("--refresh", type=int, default=30, help="Refresh interval in seconds for monitor mode")
    
    args = parser.parse_args()
    
    if args.list or (not args.match and not args.markets):
        # If no specific action is requested, or --list is specified, show live matches
        live_matches = fetch_live_matches()
        display_live_matches(live_matches)
    elif args.match and args.markets:
        # List available markets for the match
        list_live_markets(args.match)
    elif args.match and args.monitor:
        # Monitor mode - continuously fetch and display odds
        monitor_live_odds(args.match, args.market, args.refresh)
    elif args.match:
        # Fetch odds for specific match
        fetch_and_display_live_odds(args.match, args.market)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
