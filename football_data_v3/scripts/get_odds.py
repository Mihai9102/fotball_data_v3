#!/usr/bin/env python3
"""
Script to fetch and display pre-match odds from SportMonks API
"""

import sys
import logging
import argparse
from tabulate import tabulate

# Add parent directory to path
sys.path.append('/Users/mihaivictor/CascadeProjects/football_data/football_data_v3')

from api.sportmonks import SportMonksAPI
from config.markets import get_market_display_name, normalize_market_name, get_selection_name
from processors.odds_processor import OddsProcessor

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def display_odds_for_fixture(fixture_id, market_id=None):
    """Display odds for a specific fixture"""
    api = SportMonksAPI()
    
    # First get the fixture details to show the match info
    fixture, success = api.get_fixture_by_id(fixture_id)
    if not success or not fixture:
        print(f"Failed to get fixture with ID {fixture_id}")
        return
        
    # Show fixture details
    home_team = fixture.get('localTeam', {}).get('data', {}).get('name', 'Home Team')
    away_team = fixture.get('visitorTeam', {}).get('data', {}).get('name', 'Away Team')
    league = fixture.get('league', {}).get('data', {}).get('name', 'Unknown League')
    match_date = fixture.get('starting_at', 'Unknown date')
    
    print(f"\n=== MATCH: {home_team} vs {away_team} ===")
    print(f"League: {league}")
    print(f"Date: {match_date}")
    
    # Get pre-match odds
    if market_id:
        odds_data, success = api.get_odds_by_fixture_and_market(fixture_id, market_id)
        market_filter = f"for market ID {market_id}"
    else:
        odds_data, success = api.get_pre_match_odds_by_fixture_id(fixture_id)
        market_filter = "across all markets"
    
    if not success or not odds_data:
        print(f"No odds data available {market_filter}")
        return
    
    print(f"\nFound {len(odds_data)} odds entries {market_filter}")
    
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
        
        print(f"\n--- Market: {market_info['name']} ---")
        
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

def main():
    parser = argparse.ArgumentParser(description="Fetch and display pre-match odds")
    parser.add_argument("fixture_id", type=int, help="Fixture/match ID to get odds for")
    parser.add_argument("--market", type=int, help="Specific market ID to filter by")
    
    args = parser.parse_args()
    
    display_odds_for_fixture(args.fixture_id, args.market)

if __name__ == "__main__":
    main()
