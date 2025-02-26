#!/usr/bin/env python3
"""
Script to analyze odds data and find value betting opportunities
"""

import sys
import logging
import argparse
from datetime import datetime, timedelta
from tabulate import tabulate  # You may need to install this: pip install tabulate

# Add parent directory to path
sys.path.append('/Users/mihaivictor/CascadeProjects/football_data/football_data_v3')

from processors.odds_processor import OddsProcessor
from database.operations import DatabaseManager

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def find_value_bets(days_ahead=3, threshold=0.05):
    """Find value bets for upcoming matches"""
    db = DatabaseManager()
    odds_processor = OddsProcessor(db_manager=db)
    
    try:
        # Find upcoming matches
        start_date = datetime.now()
        end_date = start_date + timedelta(days=days_ahead)
        
        matches = db.get_matches(start_date=start_date, end_date=end_date)
        
        if not matches:
            print("No upcoming matches found.")
            return
            
        print(f"Analyzing {len(matches)} upcoming matches...")
        
        all_value_bets = []
        
        # Find value bets for each match
        for match in matches:
            value_bets = odds_processor.get_value_bets(match.id, threshold=threshold)
            
            if value_bets:
                # Add match info to each value bet
                for bet in value_bets:
                    bet['match'] = f"{match.localteam_name} vs {match.visitorteam_name}"
                    bet['league'] = match.league_name
                    bet['date'] = match.starting_at_timestamp.strftime("%Y-%m-%d %H:%M")
                
                all_value_bets.extend(value_bets)
                
        # Sort by edge (value)
        all_value_bets.sort(key=lambda x: x['edge'], reverse=True)
        
        if all_value_bets:
            # Print table of value bets
            table_data = []
            for bet in all_value_bets:
                # Format numbers as percentages
                implied_pct = f"{bet['implied_probability'] * 100:.1f}%"
                prediction_pct = f"{bet['prediction_probability'] * 100:.1f}%"
                edge_pct = f"{bet['edge'] * 100:.1f}%"
                
                table_data.append([
                    bet['date'],
                    bet['match'],
                    bet['league'],
                    bet['market'],
                    bet['selection'],
                    bet['bookmaker'],
                    f"{bet['odds']:.2f}",
                    implied_pct,
                    prediction_pct,
                    edge_pct
                ])
            
            headers = ["Date", "Match", "League", "Market", "Selection", 
                      "Bookmaker", "Odds", "Implied", "Predicted", "Edge"]
            
            print("\n" + tabulate(table_data, headers=headers, tablefmt="grid"))
            print(f"\nFound {len(all_value_bets)} potential value bets with {threshold*100:.1f}%+ edge")
        else:
            print("No value betting opportunities found.")
    
    finally:
        odds_processor.close()

def main():
    parser = argparse.ArgumentParser(description="Analyze odds data and find value bets")
    parser.add_argument("--days", type=int, default=3, help="Number of days ahead to analyze")
    parser.add_argument("--threshold", type=float, default=0.05, 
                       help="Minimum edge threshold (as decimal, default: 0.05 = 5%)")
    
    args = parser.parse_args()
    
    find_value_bets(days_ahead=args.days, threshold=args.threshold)

if __name__ == "__main__":
    main()
