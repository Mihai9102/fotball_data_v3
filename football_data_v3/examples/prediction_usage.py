#!/usr/bin/env python3
"""
Example script showing how to work with prediction data from SportMonks API
"""

import sys
import os
from datetime import datetime, timedelta
import json

# Add parent directory to path
sys.path.append('/Users/mihaivictor/CascadeProjects/football_data/football_data_v3')

from api.sportmonks import SportMonksAPI
from api.predictions import normalize_prediction_data, get_prediction_type_name

def main():
    # Create API client
    api = SportMonksAPI()
    
    print("Working with SportMonks prediction data...\n")
    
    # Get upcoming fixtures for demo
    start_date = datetime.now().strftime("%Y-%m-%d")
    end_date = (datetime.now() + timedelta(days=3)).strftime("%Y-%m-%d")
    
    fixtures, success = api.get_fixtures_between_dates(
        start_date=start_date,
        end_date=end_date,
        include_predictions=False  # We'll fetch predictions separately
    )
    
    if not success or not fixtures:
        print("❌ Failed to get fixtures. Please check your API subscription.")
        return
    
    # Choose the first fixture for the demo
    fixture = fixtures[0]
    fixture_id = fixture["id"]
    
    # Show match info
    local_team = fixture.get('localTeam', {}).get('data', {}).get('name', 'Unknown')
    visitor_team = fixture.get('visitorTeam', {}).get('data', {}).get('name', 'Unknown')
    league_name = fixture.get('league', {}).get('data', {}).get('name', 'Unknown')
    match_date = fixture.get('starting_at', '').replace('T', ' ').split('.')[0]
    
    print(f"Getting predictions for match: {local_team} vs {visitor_team}")
    print(f"League: {league_name}")
    print(f"Date: {match_date}")
    print(f"Fixture ID: {fixture_id}\n")
    
    # Get predictions
    prediction_data, success = api.get_prediction_probabilities_by_fixture(fixture_id)
    
    if not success:
        print("❌ Failed to get predictions. This feature might not be available in your subscription.")
        return
        
    if not prediction_data or "predictions" not in prediction_data:
        print("❌ No prediction data available for this match.")
        return
    
    # Process prediction data
    print(f"✅ Successfully retrieved predictions! Processing {len(prediction_data['predictions'])} prediction types.")
    
    # Normalize and structure the prediction data
    normalized_predictions = normalize_prediction_data(prediction_data)
    
    print("\n=== PREDICTIONS ANALYSIS ===\n")
    
    # Group predictions by type for analysis
    by_type = {}
    for pred in normalized_predictions:
        dev_name = pred["developer_name"]
        if dev_name not in by_type:
            by_type[dev_name] = []
        by_type[dev_name].append(pred)
    
    # Display the predictions by type
    for pred_type, preds in by_type.items():
        type_name = get_prediction_type_name(pred_type)
        print(f"\n--- {type_name} ({pred_type}) ---")
        
        if pred_type == "CORRECT_SCORE_PROBABILITY":
            # Sort correct scores by probability
            sorted_scores = sorted(preds, key=lambda x: x["probability"], reverse=True)
            print("Top 5 most likely scores:")
            for i, score in enumerate(sorted_scores[:5]):
                print(f"  {score['selection']}: {score['probability']:.2f}%")
                
        elif pred_type == "FULLTIME_RESULT_PROBABILITY":
            # Match result
            for pred in sorted(preds, key=lambda x: x["selection"]):
                result = pred["selection"].capitalize()
                print(f"  {result}: {pred['probability']:.2f}%")
                