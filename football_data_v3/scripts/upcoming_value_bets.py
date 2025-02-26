#!/usr/bin/env python3
"""
Script to find value betting opportunities using SportMonks prediction probabilities
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
from config.markets import get_market_display_name, normalize_market_name
from database.operations import DatabaseManager
from processors.odds_processor import OddsProcessor

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def find_value_bets(days_ahead=3, min_value=0.05, market_type="1X2"):
    """
    Find value bets by comparing prediction probabilities with bookmaker odds
    
    Args:
        days_ahead: Number of days ahead to search
        min_value: Minimum value difference (predicted probability - implied probability)
        market_type: Type of market to analyze (1X2, BTTS, Over/Under)
    """
    api = SportMonksAPI()
    
    # Define start and end dates
    start_date = datetime.now().strftime("%Y-%m-%d")
    end_date = (datetime.now() + timedelta(days=days_ahead)).strftime("%Y-%m-%d")
    
    logger.info(f"Finding value bets from {start_date} to {end_date} (market: {market_type})")
    
    # Get fixtures with odds in the date range
    fixtures, success = api.get_fixtures_with_odds(
        start_date=start_date,
        end_date=end_date
    )
    
    if not success or not fixtures:
        logger.warning(f"No fixtures with odds found in the next {days_ahead} days")
        return
    
    logger.info(f"Analyzing {len(fixtures)} fixtures for value bets...")
    
    # Value bets container
    value_bets = []
    
    # Configure market-specific settings
    normalized_market = normalize_market_name(market_type)
    prediction_key = None
    
    # Set the right prediction key based on market type
    if normalized_market == "1X2":
        prediction_key = "prediction_1x2"
        market_id = 1
        outcomes = {'1': 'Home', 'X': 'Draw', '2': 'Away'}
    elif normalized_market == "btts":
        prediction_key = "prediction_btts"
        market_id = 3
        outcomes = {'yes': 'Yes', 'no': 'No'}
    elif normalized_market == "over_under":
        prediction_key = "prediction_over_under_25"  # Default to 2.5 goals
        market_id = 2
        outcomes = {'over': 'Over 2.5', 'under': 'Under 2.5'}
    else:
        logger.error(f"Unsupported market type: {market_type}")
        return
    
    # Process each fixture
    for idx, fixture in enumerate(fixtures):
        logger.debug(f"Processing fixture {idx+1}/{len(fixtures)}")
        
        fixture_id = fixture.get('id')
        if not fixture_id:
            continue
        
        # Extract match details
        home_team = fixture.get('localTeam', {}).get('data', {}).get('name', 'Home')
        away_team = fixture.get('visitorTeam', {}).get('data', {}).get('name', 'Away')
        league_name = fixture.get('league', {}).get('data', {}).get('name', 'Unknown')
        match_date = fixture.get('starting_at', '').replace('T', ' ').split('.')[0]
        
        # Get prediction probabilities
        probabilities, success = api.get_prediction_probabilities_by_fixture(fixture_id)
        
        if not success or not probabilities:
            logger.debug(f"No prediction data for fixture {fixture_id}")
            continue
        
        # Check if we have predictions for the requested market
        if (not 'predictions' in probabilities or 
            not prediction_key in probabilities['predictions']):
            logger.debug(f"No {market_type} predictions for fixture {fixture_id}")
            continue
            
        predictions = probabilities['predictions'][prediction_key]
        
        # Get odds for this fixture and market
        odds_data, success = api.get_odds_by_fixture_and_market(fixture_id, market_id)
        
        if not success or not odds_data:
            logger.debug(f"No odds data for fixture {fixture_id}")
            continue
            
        # Process odds: group by selection and find best odds
        best_odds = {}
        for odd in odds_data:
            selection = odd.get('selection_name', '')
            normalized_selection = normalize_market_name(selection)
            
            # Reverse map selection to API outcome
            api_selection = None
            for api_outcome, sel_name in outcomes.items():
                if sel_name.lower() in selection.lower():
                    api_selection = api_outcome
                    break
            
            if not api_selection:
                continue
                
            value = odd.get('value', 0)
            
            if api_selection not in best_odds or value > best_odds[api_selection]['value']:
                best_odds[api_selection] = {
                    'value': value,
                    'bookmaker': odd.get('bookmaker_name', 'Unknown')
                }
        
        # Check each outcome for value
        for api_outcome, selection_name in outcomes.items():
            # Skip if no prediction or odds for this outcome
            if api_outcome not in predictions or api_outcome not in best_odds:
                continue
                
            # Calculate probabilities and value
            pred_prob = float(predictions[api_outcome])
            odd_value = best_odds[api_outcome]['value']
            implied_prob = 1.0 / odd_value
            value_edge = pred_prob - implied_prob
            
            # If the predicted probability is significantly higher than implied by odds
            if value_edge >= min_value:
                value_bets.append({
                    'fixture_id': fixture_id,
                    'match': f"{home_team} vs {away_team}",
                    'league': league_name,
                    'date': match_date,
                    'market': market_type,
                    'selection': selection_name,
                    'bookmaker': best_odds[api_outcome]['bookmaker'],
                    'odds': odd_value,
                    'implied_prob': implied_prob,
                    'pred_prob': pred_prob,
                    'value': value_edge
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
                f"{bet['market']} - {bet['selection']}",
                bet['bookmaker'],
                f"{bet['odds']:.2f}",
                f"{bet['implied_prob']:.1%}",
                f"{bet['pred_prob']:.1%}",
                f"{bet['value']:.1%}"
            ])
            
        # Display table
        headers = ["Date", "Match", "League", "Bet", "Bookmaker", "Odds", 
                  "Implied Prob", "Predicted Prob", "Edge"]
        print("\nValue Betting Opportunities:")
        print(tabulate(table_data, headers=headers, tablefmt="grid"))
        print(f"\nFound {len(value_bets)} potential value bets with {min_value*100:.1f}%+ edge")
    else:
        print(f"No value bets found for {market_type} with {min_value*100:.1f}%+ edge")

def main():
    parser = argparse.ArgumentParser(description="Find value bets using prediction probabilities")
    parser.add_argument("--days", type=int, default=3, help="Number of days ahead to analyze")
    parser.add_argument("--market", choices=["1X2", "BTTS", "OVER_UNDER"], default="1X2",
                       help="Market to analyze for value")
    parser.add_argument("--min-value", type=float, default=0.05,
                       help="Minimum edge/value in decimal (default: 0.05 = 5%)")
    
    args = parser.parse_args()
    
    find_value_bets(
        days_ahead=args.days,
        min_value=args.min_value,
        market_type=args.market
    )

if __name__ == "__main__":
    main()
