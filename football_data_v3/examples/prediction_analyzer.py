#!/usr/bin/env python3
"""
Example script showing how to analyze prediction data from SportMonks API
Specifically designed to handle the complex prediction structure with various types
"""

import sys
import os
import json
import argparse
import pandas as pd
from datetime import datetime
from tabulate import tabulate

# Add parent directory to path
sys.path.append('/Users/mihaivictor/CascadeProjects/football_data/football_data_v3')

from api.sportmonks import SportMonksAPI
from api.predictions import normalize_prediction_data, get_prediction_type_name

def load_sample_data(file_path=None):
    """Load sample prediction data either from file or use embedded example"""
    if file_path and os.path.exists(file_path):
        with open(file_path, 'r') as f:
            return json.load(f)
    
    # Use the embedded example
    sample_data = {
        "predictions": [
            # This is just a sample entry - the full data is quite large
            {
                "id": 5015701,
                "fixture_id": 18535264,
                "predictions": {
                    "yes": 39.25,
                    "no": 60.75
                },
                "type_id": 332,
                "type": {
                    "id": 332,
                    "name": "Away Over/Under 1.5 Probability",
                    "code": "away-over-under-1_5_probability",
                    "developer_name": "AWAY_OVER_UNDER_1_5_PROBABILITY",
                    "model_type": "prediction",
                    "stat_group": None
                }
            },
            # More prediction entries would follow...
        ]
    }
    return sample_data

def analyze_predictions(prediction_data):
    """
    Analyze prediction data from SportMonks API
    Display various useful views of the data for analysis
    """
    print("\n===== PREDICTION DATA ANALYSIS =====\n")

    if not prediction_data or "predictions" not in prediction_data:
        print("Invalid prediction data format!")
        return
    
    fixture_id = None
    if prediction_data["predictions"]:
        fixture_id = prediction_data["predictions"][0].get("fixture_id")
        print(f"Match/Fixture ID: {fixture_id}")
    
    print(f"Total prediction types: {len(prediction_data['predictions'])}")
    
    # Normalize the data for easier analysis
    normalized_predictions = normalize_prediction_data(prediction_data)
    
    # Group by type
    types = {}
    for pred in normalized_predictions:
        type_name = pred["developer_name"]
        if type_name not in types:
            types[type_name] = []
        types[type_name].append(pred)
    
    print(f"\nPrediction types found: {len(types)}")
    
    # Display all prediction types and their formats
    print("\n----- PREDICTION TYPES SUMMARY -----")
    type_summary = []
    for type_name, preds in types.items():
        human_name = get_prediction_type_name(type_name)
        selections = [p["selection"] for p in preds]
        selections_str = ", ".join(selections[:3]) + ("..." if len(selections) > 3 else "")
        type_summary.append([type_name, human_name, len(preds), selections_str])
    
    print(tabulate(type_summary, headers=["Type Code", "Human Name", "Values", "Sample Selections"]))
        
    # Show detailed breakdown of common prediction types
    print("\n----- COMMON PREDICTION DETAILS -----")
    
    # Match Winner
    if "FULLTIME_RESULT_PROBABILITY" in types:
        print("\n* Match Result Probabilities:")
        match_preds = {p["selection"]: p["probability"] for p in types["FULLTIME_RESULT_PROBABILITY"]}
        print(f"  Home: {match_preds.get('home', 0):.2f}% | Draw: {match_preds.get('draw', 0):.2f}% | Away: {match_preds.get('away', 0):.2f}%")
    
    # BTTS
    if "BTTS_PROBABILITY" in types:
        print("\n* Both Teams To Score:")
        btts_preds = {p["selection"]: p["probability"] for p in types["BTTS_PROBABILITY"]}
        print(f"  Yes: {btts_preds.get('yes', 0):.2f}% | No: {btts_preds.get('no', 0):.2f}%")
    
    # Over/Under
    for ou_type in ["OVER_UNDER_1_5_PROBABILITY", "OVER_UNDER_2_5_PROBABILITY", "OVER_UNDER_3_5_PROBABILITY"]:
        if ou_type in types:
            print(f"\n* {get_prediction_type_name(ou_type)}:")
            ou_preds = {p["selection"]: p["probability"] for p in types[ou_type]}
            print(f"  Over: {ou_preds.get('yes', 0):.2f}% | Under: {ou_preds.get('no', 0):.2f}%")
    
    # Correct Score
    if "CORRECT_SCORE_PROBABILITY" in types:
        print("\n* Correct Score Predictions:")
        # Sort by probability (most likely first)
        score_preds = sorted(types["CORRECT_SCORE_PROBABILITY"], key=lambda x: x["probability"], reverse=True)
        
        # Show top 5 most likely scores
        for i, pred in enumerate(score_preds[:5]):
            print(f"  {i+1}. {pred['selection']}: {pred['probability']:.2f}%")
    
    # Show how to format this data for Grafana
    print("\n----- GRAFANA INTEGRATION -----")
    print("Data format for Grafana pivot table:")
    
    # Create a simplified dataframe for demonstration
    data = []
    for pred in normalized_predictions[:10]:  # Limit to first 10 for simplicity
        data.append({
            "match_id": pred["fixture_id"],
            "type": pred["developer_name"],
            "selection": pred["selection"],
            "probability": pred["probability"]
        })
    
    df = pd.DataFrame(data)
    print(df)
    
    print("\nPivot table transformation:")
    pivot_df = df.pivot_table(index="match_id", columns=["type", "selection"], values="probability")
    print(pivot_df)

def get_predictions_from_api(fixture_id):
    """Get predictions directly from the API for a specific match"""
    api = SportMonksAPI()
    prediction_data, success = api.get_prediction_probabilities_by_fixture(fixture_id)
    
    if not success:
        print("Failed to retrieve prediction data from API")
        return None
        
    return prediction_data

def main():
    parser = argparse.ArgumentParser(description="Analyze prediction data from SportMonks API")
    parser.add_argument('--file', help='Path to JSON file with prediction data')
    parser.add_argument('--fixture', type=int, help='Fixture ID to fetch predictions from API')
    parser.add_argument('--save', action='store_true', help='Save retrieved data to file')
    
    args = parser.parse_args()
    
    # Get prediction data from API or file
    if args.fixture:
        print(f"Fetching prediction data for fixture ID {args.fixture} from API...")
        prediction_data = get_predictions_from_api(args.fixture)
        if args.save and prediction_data:
            output_file = f"prediction_{args.fixture}_{datetime.now().strftime('%Y%m%d')}.json"
            with open(output_file, 'w') as f:
                json.dump(prediction_data, f, indent=2)
            print(f"Saved prediction data to {output_file}")
    else:
        prediction_data = load_sample_data(args.file)
    
    if not prediction_data:
        print("No prediction data available. Exiting.")
        return
    
    # Analyze the predictions
    analyze_predictions(prediction_data)

if __name__ == "__main__":
    main()
