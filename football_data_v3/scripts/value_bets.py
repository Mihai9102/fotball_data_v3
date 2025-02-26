#!/usr/bin/env python3
"""
Script to fetch and display value betting recommendations from SportMonks API
"""

import sys
import logging
import argparse
from datetime import datetime, timedelta
from tabulate import tabulate
import json
import os

# Add parent directory to path
sys.path.append('/Users/mihaivictor/CascadeProjects/football_data/football_data_v3')

from api.sportmonks import SportMonksAPI
from config.leagues import SUPPORTED_LEAGUES, get_league_name
from config.markets import MARKET_IDS, get_market_display_name

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def display_value_bets(league_id=None, min_edge=0.05, min_odds=1.5, market_id=None, 
                     save_to_file=False, output_format='table', sort_by='edge'):
    """
    Display value betting recommendations
    
    Args:
        league_id: Optional league ID to filter
        min_edge: Minimum edge/value (probability difference)
        min_odds: Minimum odds to consider
        market_id: Filter by specific market ID
        save_to_file: Whether to save results to a file
        output_format: Output format (table or json)
        sort_by: Field to sort results by (edge, odds, prob, date)
    """
    api = SportMonksAPI()
    
    # Prepare league filter
    league_ids = None
    if league_id:
        league_ids = [league_id]
        logger.info(f"Fetching value bets for league ID {league_id} ({get_league_name(league_id)})")
    else:
        logger.info("Fetching value bets for all supported leagues")
        
    # Get value bets
    value_bets, success = api.get_value_bets(
        league_ids=league_ids,
        min_odds=min_odds,
        market_id=market_id
    )
    
    if not success or not value_bets:
        logger.warning("No value bets found")
        return
    
    logger.info(f"Found {len(value_bets)} value bet recommendations")
    
    # Process and enrich data
    processed_bets = []
    for bet in value_bets:
        # Skip if edge is too small
        edge = bet.get('probability', 0) - (1.0 / bet.get('odds', 999))
        if edge < min_edge:
            continue
            
        # Extract fixture info
        fixture = bet.get('fixture', {}).get('data', {})
        fixture_id = fixture.get('id')
        match_date = fixture.get('starting_at', '').replace('T', ' ').split('.')[0] if 'starting_at' in fixture else 'Unknown'
        
        # Get team names
        participants = fixture.get('participants', {}).get('data', [])
        home_team = 'Home'
        away_team = 'Away'
        
        for participant in participants:
            if participant.get('position') == 'home':
                home_team = participant.get('name', 'Home')
            elif participant.get('position') == 'away':
                away_team = participant.get('name', 'Away')
        
        match = f"{home_team} vs {away_team}"
        
        # Get league info
        league = bet.get('fixture', {}).get('league', {}).get('data', {})
        league_name = league.get('name', 'Unknown League')
        
        # Get bet details
        market_name = get_market_display_name(bet.get('market_name', 'Unknown Market'))
        selection = bet.get('selection_name', 'Unknown')
        bookmaker = bet.get('bookmaker_name', 'Unknown')
        odds = bet.get('odds', 0)
        probability = bet.get('probability', 0)
        implied_probability = 1.0 / odds if odds else 0
        
        # Create record
        processed_bet = {
            'fixture_id': fixture_id,
            'date': match_date,
            'match': match,
            'league': league_name,
            'market': market_name,
            'selection': selection,
            'bookmaker': bookmaker,
            'odds': odds,
            'prob': probability,
            'implied_prob': implied_probability,
            'edge': edge
        }
        
        processed_bets.append(processed_bet)
    
    # Sort results
    if sort_by == 'edge':
        processed_bets.sort(key=lambda x: x['edge'], reverse=True)
    elif sort_by == 'odds':
        processed_bets.sort(key=lambda x: x['odds'], reverse=True)
    elif sort_by == 'prob':
        processed_bets.sort(key=lambda x: x['prob'], reverse=True)
    elif sort_by == 'date':
        processed_bets.sort(key=lambda x: x['date'])
    
    # Display results
    if not processed_bets:
        print(f"No value bets found with minimum edge {min_edge:.1%}")
        return
        
    if output_format == 'json':
        output = json.dumps(processed_bets, indent=2)
        print(output)
        
        if save_to_file:
            output_dir = 'outputs'
            os.makedirs(output_dir, exist_ok=True)
            filename = f"{output_dir}/value_bets_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(filename, 'w') as f:
                f.write(output)
            print(f"Value bets saved to {filename}")
    else:
        # Display as table
        table_data = []
        for bet in processed_bets:
            table_data.append([
                bet['date'],
                bet['match'],
                bet['league'],
                f"{bet['market']} - {bet['selection']}",
                bet['bookmaker'],
                f"{bet['odds']:.2f}",
                f"{bet['implied_prob']:.1%}",
                f"{bet['prob']:.1%}",
                f"{bet['edge']:.1%}"
            ])
            
        # Display table
        headers = ["Date", "Match", "League", "Bet", "Bookmaker", "Odds", 
                  "Implied Prob", "Predicted Prob", "Edge"]
        print("\nValue Betting Recommendations:")
        print(tabulate(table_data, headers=headers, tablefmt="grid"))
        print(f"\nFound {len(processed_bets)} value bets with {min_edge:.1%}+ edge")
        
        if save_to_file:
            output_dir = 'outputs'
            os.makedirs(output_dir, exist_ok=True)
            filename = f"{output_dir}/value_bets_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            with open(filename, 'w') as f:
                f.write(f"Value Betting Recommendations - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                f.write(tabulate(table_data, headers=headers, tablefmt="grid"))
                f.write(f"\n\nFound {len(processed_bets)} value bets with {min_edge:.1%}+ edge")
            print(f"Value bets saved to {filename}")

def list_available_leagues():
    """List leagues that have value bet recommendations available"""
    api = SportMonksAPI()
    
    # Get all value bets
    value_bets, success = api.get_value_bets()
    
    if not success or not value_bets:
        print("No value bets available")
        return
    
    # Extract unique leagues
    leagues = {}
    for bet in value_bets:
        league = bet.get('fixture', {}).get('league', {}).get('data', {})
        league_id = league.get('id')
        league_name = league.get('name')
        
        if league_id and league_name:
            leagues[league_id] = league_name
    
    # Display leagues
    print("\nLeagues with Value Bet Recommendations:")
    print("-" * 50)
    print(f"{'ID':<8} {'League Name'}")
    print("-" * 50)
    
    for league_id, league_name in sorted(leagues.items(), key=lambda x: x[1]):
        print(f"{league_id:<8} {league_name}")

def list_available_markets():
    """List markets that have value bet recommendations available"""
    api = SportMonksAPI()
    
    # Get all value bets
    value_bets, success = api.get_value_bets()
    
    if not success or not value_bets:
        print("No value bets available")
        return
    
    # Extract unique markets
    markets = {}
    for bet in value_bets:
        market_id = bet.get('market_id')
        market_name = bet.get('market_name')
        
        if market_id and market_name:
            markets[market_id] = market_name
    
    # Display markets
    print("\nMarkets with Value Bet Recommendations:")
    print("-" * 50)
    print(f"{'ID':<8} {'Market Name'}")
    print("-" * 50)
    
    for market_id, market_name in sorted(markets.items(), key=lambda x: x[0]):
        print(f"{market_id:<8} {get_market_display_name(market_name)}")

def analyze_value_bet_performance(days=30):
    """
    Analyze historical performance of value bet recommendations
    
    Args:
        days: Number of days to analyze
    """
    # This would require access to historical value bets and results
    # The current SportMonks API doesn't provide this directly
    # We would need to build our own tracking system
    
    print("Value bet performance analysis is not currently available through the SportMonks API.")
    print("To analyze performance, you would need to track bets over time and compare with actual results.")

def main():
    parser = argparse.ArgumentParser(description="Get value bet recommendations from SportMonks")
    parser.add_argument("--league", type=int, help="Filter by league ID")
    parser.add_argument("--market", type=int, help="Filter by market ID")
    parser.add_argument("--min-edge", type=float, default=0.05, help="Minimum edge (probability difference)")
    parser.add_argument("--min-odds", type=float, default=1.5, help="Minimum odds to consider")
    parser.add_argument("--list-leagues", action="store_true", help="List leagues with value bets")
    parser.add_argument("--list-markets", action="store_true", help="List markets with value bets")
    parser.add_argument("--analyze", action="store_true", help="Analyze value bet performance")
    parser.add_argument("--save", action="store_true", help="Save results to file")
    parser.add_argument("--json", action="store_true", help="Output in JSON format")
    parser.add_argument("--sort", choices=['edge', 'odds', 'prob', 'date'], default='edge',
                       help="Sort results by field (default: edge)")
    
    args = parser.parse_args()
    
    if args.list_leagues:
        list_available_leagues()
    elif args.list_markets:
        list_available_markets()
    elif args.analyze:
        analyze_value_bet_performance()
    else:
        display_value_bets(
            league_id=args.league,
            min_edge=args.min_edge,
            min_odds=args.min_odds,
            market_id=args.market,
            save_to_file=args.save,
            output_format='json' if args.json else 'table',
            sort_by=args.sort
        )

if __name__ == "__main__":
    main()
