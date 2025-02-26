#!/usr/bin/env python3
"""
Script to analyze market coverage across leagues using the hasodds endpoint
"""

import sys
import logging
import argparse
from datetime import datetime, timedelta
from tabulate import tabulate
from collections import defaultdict

# Add parent directory to path
sys.path.append('/Users/mihaivictor/CascadeProjects/football_data/football_data_v3')

from api.sportmonks import SportMonksAPI
from config.leagues import SUPPORTED_LEAGUES, SUPPORTED_LEAGUE_IDS
from config.markets import MARKET_IDS, get_market_display_name

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def analyze_market_coverage():
    """Analyze the coverage of markets across different leagues"""
    api = SportMonksAPI()
    
    # Use a 7-day window for analysis
    start_date = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    end_date = (datetime.now() + timedelta(days=6)).strftime("%Y-%m-%d")
    
    logger.info(f"Analyzing market coverage from {start_date} to {end_date}")
    
    # Create a dictionary to store results
    results = {}
    
    # First, get all fixtures that have any odds
    fixtures, success = api.get_fixtures_with_odds(
        start_date=start_date,
        end_date=end_date
    )
    
    if not success or not fixtures:
        logger.error("No fixtures with odds found")
        return
    
    total_fixtures = len(fixtures)
    logger.info(f"Found {total_fixtures} fixtures with odds")
    
    # Group fixtures by league
    leagues = defaultdict(list)
    for fixture in fixtures:
        league_id = fixture.get('league_id')
        leagues[league_id].append(fixture.get('id'))
    
    # For each common market, check how many fixtures have that market
    market_coverage = {}
    
    for market_id, market_type in MARKET_IDS.items():
        logger.info(f"Checking coverage for Market ID {market_id} - {get_market_display_name(market_type)}")
        
        # Get fixtures with this market
        fixtures_with_market, success = api.get_fixtures_with_odds(
            start_date=start_date,
            end_date=end_date,
            market_ids=[market_id]
        )
        
        if not success:
            continue
            
        # Count fixtures by league
        market_fixtures_by_league = defaultdict(list)
        for fixture in fixtures_with_market:
            league_id = fixture.get('league_id')
            market_fixtures_by_league[league_id].append(fixture.get('id'))
        
        # Store coverage info
        market_coverage[market_id] = {
            'name': get_market_display_name(market_type),
            'total': len(fixtures_with_market),
            'coverage': len(fixtures_with_market) / total_fixtures if total_fixtures else 0,
            'by_league': {
                league_id: len(fixtures) / len(leagues[league_id]) if leagues[league_id] else 0
                for league_id, fixtures in market_fixtures_by_league.items()
            }
        }
    
    # Display results
    print("\nMarket Coverage Analysis:")
    print(f"Period: {start_date} to {end_date}")
    print(f"Total fixtures with odds: {total_fixtures}")
    
    # Display overall coverage by market
    table_data = []
    for market_id, data in sorted(market_coverage.items(), key=lambda x: x[1]['coverage'], reverse=True):
        table_data.append([
            market_id,
            data['name'],
            data['total'],
            f"{data['coverage']:.1%}"
        ])
    
    headers = ["Market ID", "Market Name", "Fixtures", "Coverage"]
    print("\nOverall Market Coverage:")
    print(tabulate(table_data, headers=headers, tablefmt="grid"))
    
    # Display top 5 leagues with best coverage
    league_coverage = {}
    for league_id, fixtures in leagues.items():
        league_name = SUPPORTED_LEAGUES.get(league_id, f"League {league_id}")
        
        # Calculate average market coverage for this league
        market_counts = 0
        covered_markets = 0
        
        for market_id, data in market_coverage.items():
            if league_id in data['by_league']:
                market_counts += 1
                covered_markets += data['by_league'][league_id]
        
        avg_coverage = covered_markets / market_counts if market_counts else 0
        
        league_coverage[league_id] = {
            'name': league_name,
            'fixtures': len(fixtures),
            'market_coverage': avg_coverage
        }
    
    # Display leagues by coverage
    table_data = []
    for league_id, data in sorted(league_coverage.items(), key=lambda x: x[1]['market_coverage'], reverse=True)[:10]:
        table_data.append([
            league_id,
            data['name'],
            data['fixtures'],
            f"{data['market_coverage']:.1%}"
        ])
    
    headers = ["League ID", "League Name", "Fixtures", "Market Coverage"]
    print("\nTop 10 Leagues by Market Coverage:")
    print(tabulate(table_data, headers=headers, tablefmt="grid"))
    
    # Display coverage details for top 5 leagues
    top_leagues = sorted(league_coverage.items(), key=lambda x: x[1]['market_coverage'], reverse=True)[:5]
    
    for league_id, league_data in top_leagues:
        print(f"\nMarket Coverage for {league_data['name']} (ID: {league_id}):")
        
        table_data = []
        for market_id, market_data in sorted(market_coverage.items(), 
                                        key=lambda x: x[1]['by_league'].get(league_id, 0), 
                                        reverse=True):
            coverage = market_data['by_league'].get(league_id, 0)
            table_data.append([
                market_id,
                market_data['name'],
                f"{coverage:.1%}"
            ])
        
        headers = ["Market ID", "Market Name", "Coverage"]
        print(tabulate(table_data, headers=headers, tablefmt="simple"))

def main():
    parser = argparse.ArgumentParser(description="Analyze market coverage across leagues")
    
    # Simply call the analysis function - no complex args needed
    analyze_market_coverage()

if __name__ == "__main__":
    main()
