#!/usr/bin/env python3
"""
Example script showing how to make your first request with the SportMonks API
Based on: https://docs.sportmonks.com/football/welcome/making-your-first-request
"""

import sys
import os
from datetime import datetime, timedelta
import json

# Add parent directory to path
sys.path.append('/Users/mihaivictor/CascadeProjects/football_data/football_data_v3')

from api.sportmonks import SportMonksAPI

def main():
    # Create API client
    api = SportMonksAPI()
    
    print("Making your first requests to SportMonks API...\n")
    
    # Example 1: Get a list of leagues
    print("Example 1: Getting a list of leagues")
    leagues, success = api.get_leagues()
    
    if success:
        print(f"✅ Success! Found {len(leagues)} leagues.")
        print("First 3 leagues:")
        for league in leagues[:3]:
            print(f"  - {league.get('name')} (ID: {league.get('id')})")
    else:
        print("❌ Failed to get leagues.")
    
    print("\n" + "-" * 50 + "\n")
    
    # Example 2: Get fixtures for the next 7 days
    print("Example 2: Getting fixtures for the next 7 days")
    start_date = datetime.now().strftime("%Y-%m-%d")
    end_date = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")
    
    fixtures, success = api.get_fixtures_between_dates(
        start_date=start_date,
        end_date=end_date
    )
    
    if success:
        print(f"✅ Success! Found {len(fixtures)} fixtures between {start_date} and {end_date}.")
        print("First 3 fixtures:")
        for fixture in fixtures[:3]:
            local_team = fixture.get('localTeam', {}).get('data', {}).get('name', 'Unknown')
            visitor_team = fixture.get('visitorTeam', {}).get('data', {}).get('name', 'Unknown')
            league = fixture.get('league', {}).get('data', {}).get('name', 'Unknown')
            date = fixture.get('starting_at', '').replace('T', ' ').split('.')[0]
            print(f"  - {date}: {local_team} vs {visitor_team} ({league})")
    else:
        print("❌ Failed to get fixtures.")
    
    print("\n" + "-" * 50 + "\n")
    
    # Example 3: Get odds for a specific fixture (if you have odds in your subscription)
    print("Example 3: Getting odds for a specific fixture")
    
    if fixtures and success:
        fixture_id = fixtures[0].get('id')
        
        print(f"Getting odds for fixture ID: {fixture_id}")
        odds, success = api.get_pre_match_odds_by_fixture_id(fixture_id)
        
        if success:
            if odds:
                print(f"✅ Success! Found odds for the fixture.")
                print(f"Number of bookmakers offering odds: {len(odds)}")
                # For brevity, we'll just show the market count for the first bookmaker
                if odds:
                    markets = odds[0].get('markets', [])
                    print(f"Markets offered by first bookmaker: {len(markets)}")
            else:
                print("✅ API call successful, but no odds available for this fixture.")
        else:
            print("❌ Failed to get odds. This might be due to subscription limitations.")
    
    print("\n" + "-" * 50 + "\n")
    
    # Example 4: Get prediction probabilities (if available in your subscription)
    print("Example 4: Getting prediction probabilities")
    
    if fixtures and success:
        fixture_id = fixtures[0].get('id')
        
        print(f"Getting predictions for fixture ID: {fixture_id}")
        predictions, success = api.get_prediction_probabilities_by_fixture(fixture_id)
        
        if success:
            if predictions:
                print(f"✅ Success! Found prediction data.")
                print("Prediction data:")
                if 'predictions' in predictions:
                    # Show a sample of prediction types
                    pred_types = list(predictions['predictions'].keys())
                    print(f"Available prediction types: {', '.join(pred_types[:3])}...")
                else:
                    print("No detailed predictions available.")
            else:
                print("✅ API call successful, but no predictions available for this fixture.")
        else:
            print("❌ Failed to get predictions. This might be due to subscription limitations.")
    
    print("\nAll examples completed!")
    print("\nFor more examples and capabilities, explore the scripts directory or the API documentation.")

if __name__ == "__main__":
    main()
