#!/usr/bin/env python3
"""
Script to collect prediction data from SportMonks API and store in database.
Designed to handle the complex prediction structure from the API.
"""

import sys
import os
import logging
import argparse
from datetime import datetime, timedelta
import json
from typing import Dict, List, Tuple

# Add parent directory to path
sys.path.append('/Users/mihaivictor/CascadeProjects/football_data/football_data_v3')

from api.sportmonks import SportMonksAPI
from api.predictions import normalize_prediction_data, convert_predictions_for_db, get_prediction_json_for_db
from database.models import Session, Match, Prediction
from config.settings import get_start_date, get_end_date
from config.leagues import SUPPORTED_LEAGUE_IDS

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def collect_predictions(start_date: str = None, end_date: str = None, league_ids: List[int] = None, 
                       save_to_db: bool = True, save_raw: bool = False, output_dir: str = "outputs"):
    """
    Collect prediction data from SportMonks API
    
    Args:
        start_date: Start date for fixture search (YYYY-MM-DD)
        end_date: End date for fixture search (YYYY-MM-DD)
        league_ids: List of league IDs to filter
        save_to_db: Whether to save data to the database
        save_raw: Whether to save raw API responses
        output_dir: Directory to save raw data
    
    Returns:
        Tuple of (success count, total count)
    """
    # Use default date range if not provided
    if not start_date:
        start_date = get_start_date()
    if not end_date:
        end_date = get_end_date()
        
    # Use default leagues if not provided
    if not league_ids:
        league_ids = SUPPORTED_LEAGUE_IDS
    
    # Initialize API client
    api = SportMonksAPI()
    
    logger.info(f"Collecting predictions for matches from {start_date} to {end_date}")
    logger.info(f"Leagues: {league_ids}")
    
    # Step 1: Get fixtures in the date range
    fixtures, success = api.get_fixtures_between_dates(
        start_date=start_date,
        end_date=end_date,
        league_ids=league_ids
    )
    
    if not success or not fixtures:
        logger.warning("Failed to fetch fixtures or no fixtures found")
        return 0, 0
    
    logger.info(f"Found {len(fixtures)} fixtures. Fetching predictions...")
    
    # Step 2: Collect fixture IDs
    fixture_ids = [fixture["id"] for fixture in fixtures]
    
    # Step 3: Get predictions in batches
    success_count = 0
    batch_size = 10  # Process 10 fixtures at a time to avoid API limits
    total_matches = len(fixture_ids)
    
    for i in range(0, total_matches, batch_size):
        batch_ids = fixture_ids[i:i+batch_size]
        logger.info(f"Processing batch {i//batch_size + 1}/{(total_matches + batch_size - 1)//batch_size} ({len(batch_ids)} fixtures)")
        
        # Get predictions for this batch
        for fixture_id in batch_ids:
            # Get prediction data for this fixture
            prediction_data, pred_success = api.get_prediction_probabilities_by_fixture(fixture_id)
            
            if not pred_success or not prediction_data:
                logger.warning(f"Failed to fetch predictions for fixture {fixture_id}")
                continue
            
            # Save raw data if requested
            if save_raw:
                os.makedirs(output_dir, exist_ok=True)
                with open(f"{output_dir}/prediction_{fixture_id}.json", "w") as f:
                    json.dump(prediction_data, f, indent=2)
            
            # Process and normalize the prediction data
            normalized_predictions = normalize_prediction_data(prediction_data)
            
            if not normalized_predictions:
                logger.warning(f"No valid predictions found for fixture {fixture_id}")
                continue
                
            logger.info(f"Found {len(normalized_predictions)} predictions for fixture {fixture_id}")
            
            # Save to database if requested
            if save_to_db:
                db_records = convert_predictions_for_db(normalized_predictions)
                success_count += save_predictions_to_db(db_records, fixture_id)
    
    logger.info(f"Prediction collection complete. Processed {success_count} of {total_matches} matches.")
    return success_count, total_matches

def save_predictions_to_db(prediction_records: List[Dict], fixture_id: int) -> int:
    """
    Save prediction records to the database
    
    Args:
        prediction_records: List of prediction records
        fixture_id: Associated fixture ID
        
    Returns:
        1 if successful, 0 if not
    """
    session = Session()
    try:
        # Check if match exists
        match = session.query(Match).filter(Match.id == fixture_id).first()
        if not match:
            logger.warning(f"Match with ID {fixture_id} not found in database")
            return 0
        
        # Delete existing predictions for this match to avoid duplicates
        session.query(Prediction).filter(Prediction.match_id == fixture_id).delete()
        
        # Create prediction objects and add to session
        for record in prediction_records:
            prediction = Prediction(
                match_id=record["match_id"],
                prediction_id=record.get("prediction_id"),
                type_id=record.get("type_id"),
                type_name=record["type_name"],
                developer_name=record["developer_name"],
                selection=record["selection"],
                probability=record["probability"],
                bookmaker=record.get("bookmaker"),
                fair_odd=record.get("fair_odd"),
                odd=record.get("odd"),
                stake=record.get("stake"),
                is_value=record.get("is_value"),
                json_data=json.dumps({
                    "type": record["developer_name"],
                    "selection": record["selection"],
                    "probability": record["probability"]
                })
            )
            session.add(prediction)
        
        # Commit the changes
        session.commit()
        return 1
        
    except Exception as e:
        logger.error(f"Error saving predictions for match {fixture_id}: {str(e)}")
        session.rollback()
        return 0
        
    finally:
        session.close()

def main():
    parser = argparse.ArgumentParser(description="Collect prediction data from SportMonks API")
    parser.add_argument('--start-date', help='Start date (YYYY-MM-DD) for fixture search')
    parser.add_argument('--end-date', help='End date (YYYY-MM-DD) for fixture search')
    parser.add_argument('--league', type=int, action='append', help='League ID (can be specified multiple times)')
    parser.add_argument('--save-raw', action='store_true', help='Save raw API responses')
    parser.add_argument('--output-dir', default='outputs', help='Directory to save raw data')
    parser.add_argument('--no-db', action='store_true', help='Skip saving to database')
    
    args = parser.parse_args()
    
    collect_predictions(
        start_date=args.start_date,
        end_date=args.end_date,
        league_ids=args.league,
        save_to_db=not args.no_db,
        save_raw=args.save_raw,
        output_dir=args.output_dir
    )

if __name__ == "__main__":
    main()
