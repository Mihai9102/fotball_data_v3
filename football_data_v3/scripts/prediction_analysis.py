#!/usr/bin/env python3
"""
Script to analyze prediction data from SportMonks API
"""

import sys
import logging
import argparse
import json
from datetime import datetime, timedelta
from tabulate import tabulate
from typing import List, Dict

# Add parent directory to path
sys.path.append('/Users/mihaivictor/CascadeProjects/football_data/football_data_v3')

from api.sportmonks import SportMonksAPI
from config.leagues import SUPPORTED_LEAGUES, get_league_name
from database.operations import DatabaseManager
from processors.odds_processor import OddsProcessor

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def display_probabilities(fixture_id):
    """
    Display prediction probabilities for a specific fixture
    
    Args:
        fixture_id: Fixture ID to get probabilities for
    """
    api = SportMonksAPI()
    
    # First get the fixture details to show match info
    fixture, success = api.get_fixture_by_id(fixture_id)
    if not success or not fixture:
        print(f"Failed to get fixture with ID {fixture_id}")
        return
    
    # Extract match details
    home_team = fixture.get('localTeam', {}).get('data', {}).get('name', 'Home Team')
    away_team = fixture.get('visitorTeam', {}).get('data', {}).get('name', 'Away Team')
    league = fixture.get('league', {}).get('data', {}).get('name', 'Unknown League')
    match_date = fixture.get('starting_at', '').replace('T', ' ').split('.')[0]
    
    print(f"\n=== MATCH: {home_team} vs {away_team} ===")
    print(f"League: {league}")
    print(f"Date: {match_date}")
    
    # Get prediction probabilities
    prob_data, success = api.get_prediction_probabilities_by_fixture(fixture_id)
    
    if not success or not prob_data:
        print("No prediction probabilities available for this fixture")
        return
    
    # Extract and display prediction probabilities
    print("\nPrediction Probabilities:")
    
    # Check if we have predictions data
    if 'predictions' in prob_data and prob_data['predictions']:
        predictions = prob_data['predictions']
        
        # Extract common prediction types
        prediction_types = [
            ('1X2', 'prediction_1x2'),
            ('BTTS', 'prediction_btts'),
            ('Over/Under 2.5', 'prediction_over_under_25'),
            ('Correct Score', 'prediction_correct_score')
        ]
        
        for name, key in prediction_types:
            if key in predictions:
                print(f"\n{name} Predictions:")
                
                pred_data = predictions[key]
                if isinstance(pred_data, dict):
                    for outcome, probability in sorted(pred_data.items()):
                        if isinstance(probability, (int, float)):
                            print(f"  - {outcome}: {probability:.1%}")
                else:
                    print(f"  {pred_data}")
    else:
        print("  No detailed predictions available")
    
    # Display raw prediction accuracy/strength if available
    if 'our_prediction' in prob_data:
        print("\nSportMonks Prediction:")
        print(f"  {prob_data['our_prediction']}")
    
    if 'prediction_strength' in prob_data:
        print(f"Prediction Strength: {prob_data['prediction_strength']}")

def analyze_league_performance(league_id=None):
    """
    Analyze prediction performance for a league or all leagues
    
    Args:
        league_id: Optional league ID to analyze
    """
    api = SportMonksAPI()
    
    if league_id:
        # Get performance for specific league
        performance, success = api.get_prediction_performance_by_league(league_id)
        
        if not success or not performance:
            print(f"No prediction performance data available for league ID {league_id}")
            return
            
        league_name = get_league_name(league_id)
        print(f"\n=== Prediction Performance for {league_name} (ID: {league_id}) ===")
        
        # Display overall performance
        if 'overall' in performance:
            overall = performance['overall']
            print("\nOverall Performance:")
            print(f"Total Predictions: {overall.get('total', 'N/A')}")
            print(f"Correct: {overall.get('correct', 'N/A')}")
            print(f"Accuracy: {overall.get('accuracy', 0):.1%}")
            
        # Display market-specific performance
        if 'markets' in performance:
            markets = performance['markets']
            
            # Prepare table data
            table_data = []
            for market_name, market_stats in markets.items():
                table_data.append([
                    market_name,
                    market_stats.get('total', 'N/A'),
                    market_stats.get('correct', 'N/A'),
                    f"{market_stats.get('accuracy', 0):.1%}"
                ])
                
            # Sort by accuracy (highest first)
            table_data.sort(key=lambda x: float(x[3].replace('%', '')) if x[3] != 'N/A' else 0, reverse=True)
            
            # Display table
            headers = ["Market", "Total Predictions", "Correct", "Accuracy"]
            print("\nPerformance by Market:")
            print(tabulate(table_data, headers=headers, tablefmt="grid"))
            
    else:
        # Get performance for all leagues
        performances, success = api.get_prediction_performances()
        
        if not success or not performances:
            print("No prediction performance data available")
            return
        
        # Prepare table data for leagues
        table_data = []
        for performance in performances:
            league_id = performance.get('league_id')
            league_name = get_league_name(league_id)
            
            overall = performance.get('overall', {})
            
            table_data.append([
                league_id,
                league_name,
                overall.get('total', 'N/A'),
                overall.get('correct', 'N/A'),
                f"{overall.get('accuracy', 0):.1%}"
            ])
            
        # Sort by accuracy (highest first)
        table_data.sort(key=lambda x: float(x[4].replace('%', '')) if x[4] != 'N/A' else 0, reverse=True)
        
        # Display table
        headers = ["League ID", "League Name", "Total Predictions", "Correct", "Accuracy"]
        print("\nPrediction Performance by League:")
        print(tabulate(table_data, headers=headers, tablefmt="grid"))

def find_value_bets(days_ahead=3):
    """
    Find potential value bets using prediction probabilities vs. market odds
    
    Args:
        days_ahead: Number of days ahead to analyze
    """
    api = SportMonksAPI()
    db = DatabaseManager()
    odds_processor = OddsProcessor(db_manager=db)
    
    try:
        # Get upcoming fixtures
        start_date = datetime.now().strftime("%Y-%m-%d")
        end_date = (datetime.now() + timedelta(days=days_ahead)).strftime("%Y-%m-%d")
        
        # Get fixtures with odds in the date range
        fixtures, success = api.get_fixtures_with_odds(
            start_date=start_date,
            end_date=end_date
        )
        
        if not success or not fixtures:
            print(f"No fixtures with odds found in the next {days_ahead} days")
            return
        
        print(f"Analyzing {len(fixtures)} fixtures for value bets...")
        
        # Prepare to store value bets
        value_bets = []
        
        # Set threshold for value (difference between probability and implied odds)
        value_threshold = 0.05  # 5% difference
        
        # Process each fixture
        for fixture in fixtures:
            fixture_id = fixture.get('id')
            
            # Skip if no ID
            if not fixture_id:
                continue
            
            # Get prediction probabilities
            probabilities, success = api.get_prediction_probabilities_by_fixture(fixture_id)
            
            if not success or not probabilities:
                continue
                
            # Check if we have 1X2 predictions
            if 'predictions' in probabilities and 'prediction_1x2' in probabilities['predictions']:
                pred_1x2 = probabilities['predictions']['prediction_1x2']
                
                # Get 1X2 odds from the database
                match = db.save_match(fixture)  # Save/update match in DB
                if not match:
                    continue
                    
                # Get odds for this match
                odds = db.get_odds_for_market(match.id, "1X2")
                
                if not odds:
                    # If no odds in DB, try to fetch from API
                    odds_data, success = api.get_odds_by_fixture_and_market(fixture_id, 1)  # 1 = 1X2 market
                    if success and odds_data:
                        # Process and save odds
                        odds_processor.process_match_odds(fixture_id, odds_data)
                        # Try to get odds again
                        odds = db.get_odds_for_market(match.id, "1X2")
                
                # Only continue if we have odds
                if not odds:
                    continue
                
                # Group odds by selection and find best odds for each
                best_odds = {'Home': 0, 'Draw': 0, 'Away': 0}
                for odd in odds:
                    selection = odd.normalized_selection
                    if selection in best_odds and odd.value > best_odds[selection]:
                        best_odds[selection] = odd.value
                
                # Check for value bets
                outcome_map = {'1': 'Home', 'X': 'Draw', '2': 'Away'}
                
                for api_outcome, selection in outcome_map.items():
                    # Skip if no odds or no prediction for this outcome
                    if best_odds[selection] <= 1 or api_outcome not in pred_1x2:
                        continue
                        
                    # Get prediction probability and implied odds probability
                    pred_prob = pred_1x2.get(api_outcome, 0)
                    implied_prob = 1.0 / best_odds[selection]
                    
                    # Check for value
                    if pred_prob > implied_prob + value_threshold:
                        value_bets.append({
                            'fixture_id': fixture_id,
                            'match': f"{match.localteam_name} vs {match.visitorteam_name}",
                            'league': match.league_name,
                            'date': match.starting_at_timestamp.strftime("%Y-%m-%d %H:%M"),
                            'selection': selection,
                            'odds': best_odds[selection],
                            'implied_prob': implied_prob,
                            'predicted_prob': pred_prob,
                            'value': pred_prob - implied_prob
                        })
        
        # Sort by value (highest first)
        value_bets.sort(key=lambda x: x['value'], reverse=True)
        
        # Display results
        if value_bets:
            # Prepare table data
            table_data = []
            for bet in value_bets:
                table_data.append([
                    bet['date'],
                    bet['match'],
                    bet['league'],
                    bet['selection'],
                    f"{bet['odds']:.2f}",
                    f"{bet['implied_prob']:.1%}",
                    f"{bet['predicted_prob']:.1%}",
                    f"{bet['value']:.1%}"
                ])
                
            # Display table
            headers = ["Date", "Match", "League", "Selection", "Odds", "Implied Prob", "Predicted Prob", "Value"]
            print("\nPotential Value Bets:")
            print(tabulate(table_data, headers=headers, tablefmt="grid"))
            print(f"\nFound {len(value_bets)} potential value bets")
        else:
            print("\nNo value bets found")
            
    finally:
        db.close()
        odds_processor.close()

def main():
    parser = argparse.ArgumentParser(description="Analyze prediction data from SportMonks API")
    parser.add_argument("--fixture", type=int, help="Get prediction probabilities for a specific fixture")
    parser.add_argument("--league", type=int, help="Get prediction performance for a specific league")
    parser.add_argument("--performances", action="store_true", help="Show prediction performances for all leagues")
    parser.add_argument("--value", action="store_true", help="Find value bets using predictions")
    parser.add_argument("--days", type=int, default=3, help="Number of days ahead for value bet search")
    
    args = parser.parse_args()
    
    if args.fixture:
        display_probabilities(args.fixture)
    elif args.performances or args.league:
        analyze_league_performance(args.league)
    elif args.value:
        find_value_bets(args.days)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
