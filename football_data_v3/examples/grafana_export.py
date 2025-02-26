#!/usr/bin/env python3
"""
Example script for exporting SportMonks prediction data in a format ready for Grafana
This helps test how the data will look in Grafana without setting up the full dashboard
"""

import sys
import os
import argparse
import json
from datetime import datetime
import pandas as pd

# Add parent directory to path
sys.path.append('/Users/mihaivictor/CascadeProjects/football_data/football_data_v3')

from database.models import Session
from integrations.grafana_predictions import GrafanaPredictionHelper, get_prediction_distributions
from api.predictions import PREDICTION_TYPE_NAMES

def export_prediction_pivot(days_ahead=7, output_file="prediction_pivot.csv"):
    """Export prediction data as a pivot table CSV file"""
    helper = GrafanaPredictionHelper()
    
    try:
        # Create the pivot table
        print(f"Creating prediction pivot table for the next {days_ahead} days...")
        pivot_df = helper.create_prediction_pivot_table(days_ahead=days_ahead)
        
        if pivot_df.empty:
            print("No prediction data found")
            return False
            
        # Export to CSV
        pivot_df.to_csv(output_file)
        print(f"Exported pivot table to {output_file}")
        
        # Print some stats
        print(f"\nTotal matches: {len(pivot_df)}")
        print(f"Prediction types: {len(pivot_df.columns) - 5}")  # Subtract the index columns
        
        # Show sample of the pivot table (first few rows and columns)
        print("\nSample of the pivot table:")
        sample_cols = list(pivot_df.columns[:10])  # First 10 columns or fewer
        sample_df = pivot_df[sample_cols].head(5)
        print(sample_df)
        
        return True
        
    except Exception as e:
        print(f"Error exporting prediction pivot: {e}")
        return False
    finally:
        helper.close()

def export_prediction_stats(days_ahead=7, output_file="prediction_stats.json"):
    """Export prediction distribution statistics to a JSON file"""
    session = Session()
    
    try:
        print(f"Analyzing prediction distributions for the next {days_ahead} days...")
        stats = get_prediction_distributions(session, days_ahead=days_ahead)
        
        if not stats:
            print("No prediction data found")
            return False
            
        # Add human-readable type names
        for pred_type in stats:
            stats[pred_type]["name"] = PREDICTION_TYPE_NAMES.get(pred_type, pred_type)
        
        # Count total predictions
        total_count = 0
        for pred_type in stats:
            type_count = sum(stats[pred_type]["selections"][sel]["count"] 
                            for sel in stats[pred_type]["selections"])
            stats[pred_type]["total_count"] = type_count
            total_count += type_count
        
        # Export to JSON
        with open(output_file, "w") as f:
            json.dump(stats, f, indent=2)
            
        print(f"Exported prediction statistics to {output_file}")
        
        # Print summary
        print(f"\nTotal predictions: {total_count}")
        print(f"Prediction types: {len(stats)}")
        
        # Show top 5 prediction types by count
        print("\nTop prediction types by frequency:")
        sorted_types = sorted(stats.items(), 
                             key=lambda x: x[1].get("total_count", 0), 
                             reverse=True)
        
        for i, (pred_type, data) in enumerate(sorted_types[:5]):
            print(f"{i+1}. {data.get('name', pred_type)}: {data.get('total_count', 0)} predictions")
            
            # Show selections for this type
            for j, (sel, sel_data) in enumerate(sorted(data["selections"].items(), 
                                                     key=lambda x: x[1]["count"], 
                                                     reverse=True)):
                if j < 3:  # Show top 3 selections
                    print(f"   - {sel}: {sel_data['count']} occurrences, " +
                         f"avg probability: {sel_data['avg']:.2f}%")
        
        return True
        
    except Exception as e:
        print(f"Error exporting prediction statistics: {e}")
        return False
    finally:
        session.close()

def export_grafana_queries(output_file="grafana_queries.json"):
    """Export SQL queries for Grafana dashboard"""
    helper = GrafanaPredictionHelper()
    
    try:
        # Get queries for all prediction types
        queries = helper.get_grafana_sql_queries()
        
        # Get queries for match result predictions only
        match_result_queries = helper.get_grafana_sql_queries([
            "FULLTIME_RESULT_PROBABILITY",
            "FIRST_HALF_WINNER_PROBABILITY",
            "DOUBLE_CHANCE_PROBABILITY"
        ])
        
        # Get queries for goals predictions only
        goals_queries = helper.get_grafana_sql_queries([
            "OVER_UNDER_1_5_PROBABILITY",
            "OVER_UNDER_2_5_PROBABILITY",
            "OVER_UNDER_3_5_PROBABILITY",
            "BTTS_PROBABILITY",
            "HOME_OVER_UNDER_0_5_PROBABILITY",
            "HOME_OVER_UNDER_1_5_PROBABILITY",
            "AWAY_OVER_UNDER_0_5_PROBABILITY",
            "AWAY_OVER_UNDER_1_5_PROBABILITY"
        ])
        
        # Export to JSON
        output = {
            "all_predictions": queries,
            "match_result_predictions": match_result_queries,
            "goals_predictions": goals_queries
        }
        
        with open(output_file, "w") as f:
            json.dump(output, f, indent=2)
            
        print(f"Exported Grafana queries to {output_file}")
        
        # Print sample query
        print("\nSample SQL query for predictions:")
        print(queries["predictions"])
        
        return True
        
    except Exception as e:
        print(f"Error exporting Grafana queries: {e}")
        return False
    finally:
        helper.close()

def main():
    parser = argparse.ArgumentParser(description="Export SportMonks prediction data for Grafana")
    parser.add_argument('--days', type=int, default=7, help='Days to look ahead')
    parser.add_argument('--pivot', action='store_true', help='Export pivot table CSV')
    parser.add_argument('--stats', action='store_true', help='Export prediction statistics JSON')
    parser.add_argument('--queries', action='store_true', help='Export Grafana SQL queries')
    parser.add_argument('--all', action='store_true', help='Export all data types')
    parser.add_argument('--output-dir', default='.', help='Output directory')
    
    args = parser.parse_args()
    
    # Create output directory if it doesn't exist
    os.makedirs(args.output_dir, exist_ok=True)
    
    # Default to all if no specific exports requested
    if not (args.pivot or args.stats or args.queries):
        args.all = True
    
    if args.pivot or args.all:
        output_file = os.path.join(args.output_dir, f"prediction_pivot_{args.days}d.csv")
        export_prediction_pivot(days_ahead=args.days, output_file=output_file)
        
    if args.stats or args.all:
        output_file = os.path.join(args.output_dir, f"prediction_stats_{args.days}d.json")
        export_prediction_stats(days_ahead=args.days, output_file=output_file)
        
    if args.queries or args.all:
        output_file = os.path.join(args.output_dir, "grafana_queries.json")
        export_grafana_queries(output_file=output_file)

if __name__ == "__main__":
    main()
