#!/usr/bin/env python3
"""
Example script showing how to analyze value betting opportunities by comparing
SportMonks prediction probabilities with bookmaker odds.
"""

import sys
import os
import argparse
from datetime import datetime, timedelta
import json
from tabulate import tabulate
import pandas as pd
import numpy as np

# Add parent directory to path
sys.path.append('/Users/mihaivictor/CascadeProjects/football_data/football_data_v3')

from api.sportmonks import SportMonksAPI
from api.predictions import normalize_prediction_data, TYPE_MATCH_WINNER
from api.odds import normalize_odds_data, filter_best_odds, get_implied_probability
from config.markets import MARKET_1X2, MARKET_BTTS, MARKET_OVER_UNDER
from config.leagues import SUPPORTED_LEAGUE_IDS

def find_value_bets(league_ids=None, days_ahead=7, margin=5.0, min_odds=1.5, show_all=False):
    """
    Find potential value bets by comparing odds with prediction probabilities
    
    Args:
        league_ids: List of league IDs to filter
        days_ahead: Number of days ahead to look
        margin: Minimum percentage difference to consider valuable (e.g., 5%)
        min_odds: Minimum odds value to consider
        show_all: Whether to show all comparisons or just potential value bets
        
    Returns:
        DataFrame with value betting analysis
    """
    print("=== Value Betting Analysis ===\n")
    
    # Create API client
    api = SportMonksAPI()
    
    # Calculate date range
    start_date = datetime.now().strftime("%Y-%m-%d")
    end_date = (datetime.now() + timedelta(days=days_ahead)).strftime("%Y-%m-%d")
    
    # Use default leagues if not specified
    if not league_ids:
        league_ids = SUPPORTED_LEAGUE_IDS
        
    print(f"Analyzing matches from {start_date} to {end_date}")
    print(f"Looking for potential value with minimum {margin}% edge and odds >= {min_odds}")
    print("This may take a few minutes as we need to fetch data for each match...\n")
    
    # Get fixtures
    fixtures, success = api.get_fixtures_between_dates(
        start_date=start_date,
        end_date=end_date,
        league_ids=league_ids
    )
    
    if not success or not fixtures:
        print("❌ No fixtures found for the specified period.")
        return None
    
    print(f"Found {len(fixtures)} fixtures to analyze.")
    
    # Prepare data for analysis
    value_data = []
    counter = 0
    
    for fixture in fixtures[:30]:  # Limit to 30 fixtures to avoid API overuse
        counter += 1
        fixture_id = fixture['id']
        home_team = fixture.get('localTeam', {}).get('data', {}).get('name', 'Home Team')
        away_team = fixture.get('visitorTeam', {}).get('data', {}).get('name', 'Away Team')
        league_name = fixture.get('league', {}).get('data', {}).get('name', 'Unknown League')
        match_time = fixture.get('time', {}).get('starting_at', {}).get('date_time', 'Unknown')
        
        print(f"Processing {counter}/{min(len(fixtures), 30)}: {home_team} vs {away_team}... ", end="", flush=True)
        
        # 1. Get prediction probabilities
        predictions, pred_success = api.get_prediction_probabilities_by_fixture(fixture_id)
        
        if not pred_success or not predictions:
            print("❌ No predictions")
            continue
        
        # Normalize prediction data
        normalized_predictions = normalize_prediction_data({"predictions": predictions})
        
        if not normalized_predictions:
            print("❌ Invalid predictions")
            continue
        
        # Get match result predictions
        match_predictions = {}
        for pred in normalized_predictions:
            if pred["developer_name"] == TYPE_MATCH_WINNER:
                match_predictions[pred["selection"]] = pred["probability"]
        
        if not match_predictions or len(match_predictions) < 3:  # Need home, draw, away
            print("❌ No match result predictions")
            continue
        
        # 2. Get odds
        odds_data, odds_success = api.get_pre_match_odds_by_fixture_id(fixture_id=fixture_id)
        
        if not odds_success or not odds_data:
            print("❌ No odds")
            continue
        
        # Normalize odds data
        normalized_odds = normalize_odds_data({"data": odds_data})
        
        if not normalized_odds:
            print("❌ Invalid odds")
            continue
        
        # Get best odds for 1X2 market
        best_odds = filter_best_odds(normalized_odds, market_filter=MARKET_1X2)
        
        if MARKET_1X2 not in best_odds:
            print("❌ No 1X2 odds")
            continue
        
        match_best_odds = {}
        for selection, data in best_odds[MARKET_1X2].items():
            if data["value"] >= min_odds:  # Apply minimum odds filter
                match_best_odds[selection] = data
        
        if len(match_best_odds) < 3:  # Need home, draw, away
            print("❌ Missing selections")
            continue
            
        print("✅")
        
        # 3. Compare predictions with odds
        for selection in ['home', 'draw', 'away']:
            if selection in match_predictions and selection in match_best_odds:
                # Get prediction probability
                pred_probability = match_predictions[selection]
                
                # Get odds and bookmaker
                odds_value = match_best_odds[selection]["value"]
                bookmaker = match_best_odds[selection]["bookmaker"]
                
                # Calculate implied probability
                implied_prob = get_implied_probability(odds_value) * 100
                
                # Calculate edge (difference between predicted and implied probability)
                edge = pred_probability - implied_prob
                
                # Calculate expected value
                ev = (odds_value * (pred_probability / 100)) - 1
                
                # Calculate Kelly stake
                if pred_probability > implied_prob:
                    kelly = ((pred_probability / 100) * odds_value - 1) / (odds_value - 1)
                    kelly = max(0, kelly)  # Ensure non-negative
                else:
                    kelly = 0
                
                # Add to results
                value_data.append({
                    'Match': f"{home_team} vs {away_team}",
                    'League': league_name,
                    'Time': match_time,
                    'Selection': selection,
                    'Predicted Prob': pred_probability,
                    'Odds': odds_value,
                    'Bookmaker': bookmaker,
                    'Implied Prob': implied_prob,
                    'Edge': edge,
                    'EV': ev * 100,  # Convert to percentage
                    'Kelly %': kelly * 100  # Convert to percentage
                })
    
    if not value_data:
        print("\n❌ No valid comparisons found.")
        return None
    
    # Create DataFrame and sort by edge
    df = pd.DataFrame(value_data)
    df = df.sort_values('Edge', ascending=False)
    
    # Filter for potential value bets
    if not show_all:
        value_bets = df[df['Edge'] >= margin]
        if value_bets.empty:
            print(f"\n❌ No value bets found with minimum {margin}% edge.")
            print("Try lowering the margin requirement or analyzing more leagues.")
            return df  # Return full dataframe anyway
        else:
            return value_bets
    else:
        return df

def analyze_specific_league(league_id, days_ahead=7):
    """
    Analyze prediction accuracy for a specific league
    
    Args:
        league_id: League ID to analyze
        days_ahead: Number of days ahead to look
    """
    print(f"=== League-Specific Value Analysis (ID: {league_id}) ===\n")
    
    # Find value bets for this league
    value_bets = find_value_bets(
        league_ids=[league_id],
        days_ahead=days_ahead,
        margin=3.0,  # Lower margin for league-specific analysis
        show_all=True
    )
    
    if value_bets is None or value_bets.empty:
        print("No data available for analysis.")
        return
    
    # Analyze by selection type
    selection_analysis = value_bets.groupby('Selection').agg({
        'Edge': ['mean', 'max', 'count'],
        'EV': ['mean', 'max']
    })
    
    print("\n=== Selection Analysis ===")
    print("Average edge by selection type:")
    print(selection_analysis.round(2))
    
    # Find patterns in the data
    print("\n=== Pattern Analysis ===")
    
    # Are home teams overvalued or undervalued?
    home_edge = value_bets[value_bets['Selection'] == 'home']['Edge'].mean()
    if home_edge > 0:
        print(f"Home teams appear to be UNDERVALUED by {home_edge:.2f}% on average")
    else:
        print(f"Home teams appear to be OVERVALUED by {abs(home_edge):.2f}% on average")
    
    # Are draws systematically mispriced?
    draw_edge = value_bets[value_bets['Selection'] == 'draw']['Edge'].mean()
    if abs(draw_edge) > 2:
        direction = "undervalued" if draw_edge > 0 else "overvalued"
        print(f"Draws appear to be systematically {direction} by {abs(draw_edge):.2f}%")
    
    # Which bookmaker offers the best odds most frequently?
    bookmaker_counts = value_bets['Bookmaker'].value_counts()
    if not bookmaker_counts.empty:
        most_common = bookmaker_counts.idxmax()
        print(f"Most generous bookmaker: {most_common} (best odds in {bookmaker_counts.max()} cases)")
    
    # Show top 10 value opportunities
    top_value = value_bets.sort_values('Edge', ascending=False).head(10)
    
    print("\n=== Top 10 Value Opportunities ===")
    display_table = top_value[['Match', 'Selection', 'Predicted Prob', 'Odds', 
                               'Implied Prob', 'Edge', 'Bookmaker']]
    
    print(tabulate(display_table, headers='keys', showindex=False))
    
    # Save results to file if needed
    # top_value.to_csv(f"league_{league_id}_value_bets.csv", index=False)

def compare_prediction_services():
    """
    Compare SportMonks predictions with other prediction services
    This is a placeholder function - extend as needed
    """
    print("\n=== Prediction Service Comparison ===")
    print("This feature is not yet implemented.")
    print("It would allow comparison of SportMonks predictions with:")
    print("- Historical accuracy")
    print("- Other prediction services")
    print("- Betting market consensus")

def analyze_value_bet_edge_distribution(days_ahead=7):
    """
    Analyze the distribution of prediction edges to find systematic mispricings
    
    Args:
        days_ahead: Number of days ahead to look
    """
    print("\n=== Edge Distribution Analysis ===")
    
    # Get all comparisons (not just value bets)
    comparisons = find_value_bets(days_ahead=days_ahead, margin=0.0, show_all=True)
    
    if comparisons is None or comparisons.empty:
        print("No data available for analysis.")
        return
    
    # Basic statistics
    print("\n== Basic Edge Statistics ==")
    edge_stats = comparisons['Edge'].describe()
    print(f"Mean edge: {edge_stats['mean']:.2f}%")
    print(f"Median edge: {edge_stats['50%']:.2f}%")
    print(f"Standard deviation: {edge_stats['std']:.2f}%")
    print(f"Min edge: {edge_stats['min']:.2f}%")
    print(f"Max edge: {edge_stats['max']:.2f}%")
    
    # Count of positive vs negative edges
    positive_edges = (comparisons['Edge'] > 0).sum()
    negative_edges = (comparisons['Edge'] <= 0).sum()
    total_edges = len(comparisons)
    
    print(f"\nPositive edges: {positive_edges} ({positive_edges/total_edges*100:.1f}%)")
    print(f"Negative edges: {negative_edges} ({negative_edges/total_edges*100:.1f}%)")
    
    # League analysis
    print("\n== League Analysis ==")
    league_edges = comparisons.groupby('League')['Edge'].agg(['mean', 'count'])
    league_edges = league_edges.sort_values('mean', ascending=False)
    
    print("Leagues with highest average edge:")
    print(tabulate(league_edges.head(5), headers=['League', 'Avg Edge', 'Count'], 
                  showindex=True, floatfmt='.2f'))
    
    # Selection type analysis
    print("\n== Selection Type Analysis ==")
    selection_edges = comparisons.groupby('Selection')['Edge'].agg(['mean', 'count'])
    
    print("Average edge by selection type:")
    print(tabulate(selection_edges, headers=['Selection', 'Avg Edge', 'Count'], 
                  showindex=True, floatfmt='.2f'))

def main():
    parser = argparse.ArgumentParser(description="SportMonks value betting analysis")
    parser.add_argument('--days', '-d', type=int, default=7, 
                      help='Number of days ahead to look')
    parser.add_argument('--league', '-l', type=int, 
                      help='Analyze a specific league ID')
    parser.add_argument('--margin', '-m', type=float, default=5.0, 
                      help='Minimum percentage edge to consider a value bet')
    parser.add_argument('--min-odds', type=float, default=1.5, 
                      help='Minimum odds to consider')
    parser.add_argument('--show-all', '-a', action='store_true', 
                      help='Show all bets, not just value bets')
    parser.add_argument('--distribution', action='store_true', 
                      help='Analyze edge distribution')
    parser.add_argument('--compare', '-c', action='store_true', 
                      help='Compare prediction services')
    
    args = parser.parse_args()
    
    if args.league:
        analyze_specific_league(args.league, args.days)
    elif args.distribution:
        analyze_value_bet_edge_distribution(args.days)
    elif args.compare:
        compare_prediction_services()
    else:
        value_bets = find_value_bets(
            days_ahead=args.days,
            margin=args.margin,
            min_odds=args.min_odds,
            show_all=args.show_all
        )
        
        if value_bets is not None and not value_bets.empty:
            print("\n=== Value Betting Opportunities ===")
            print(tabulate(value_bets[['Match', 'Selection', 'Predicted Prob', 'Odds', 
                                      'Implied Prob', 'Edge', 'Bookmaker', 'Kelly %']], 
                          headers='keys', showindex=False, floatfmt='.2f'))
            
            print(f"\nFound {len(value_bets)} potential value bets out of {len(find_value_bets(days_ahead=args.days, margin=0, show_all=True))} total comparisons.")
            
            # Suggested stakes based on Kelly criterion
            print("\n=== Suggested Stakes (Kelly) ===")
            print("These are *maximum* suggested stakes as a percentage of your bankroll:")
            
            kelly_bets = value_bets.sort_values('Kelly %', ascending=False)
            print(tabulate(kelly_bets[['Match', 'Selection', 'Odds', 'Edge', 'Kelly %']], 
                          headers='keys', showindex=False, floatfmt='.2f'))

if __name__ == "__main__":
    main()