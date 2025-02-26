"""
Module for processing SportMonks prediction data
Based on the prediction data structure from SportMonks API v3
"""

import logging
import json
from typing import Dict, List, Any, Optional, Tuple

logger = logging.getLogger(__name__)

# Prediction type constants
TYPE_BTTS = "BTTS_PROBABILITY"
TYPE_MATCH_WINNER = "FULLTIME_RESULT_PROBABILITY"
TYPE_FIRST_HALF_WINNER = "FIRST_HALF_WINNER_PROBABILITY"
TYPE_OVER_UNDER_15 = "OVER_UNDER_1_5_PROBABILITY"
TYPE_OVER_UNDER_25 = "OVER_UNDER_2_5_PROBABILITY"
TYPE_OVER_UNDER_35 = "OVER_UNDER_3_5_PROBABILITY"
TYPE_DOUBLE_CHANCE = "DOUBLE_CHANCE_PROBABILITY"
TYPE_HTFT = "HTFT_PROBABILITY"
TYPE_CORRECT_SCORE = "CORRECT_SCORE_PROBABILITY"
TYPE_TEAM_SCORE_FIRST = "TEAM_TO_SCORE_FIRST_PROBABILITY"
TYPE_HOME_OVER_UNDER_05 = "HOME_OVER_UNDER_0_5_PROBABILITY"
TYPE_HOME_OVER_UNDER_15 = "HOME_OVER_UNDER_1_5_PROBABILITY"
TYPE_AWAY_OVER_UNDER_05 = "AWAY_OVER_UNDER_0_5_PROBABILITY"
TYPE_AWAY_OVER_UNDER_15 = "AWAY_OVER_UNDER_1_5_PROBABILITY"
TYPE_CORNERS_OVER_UNDER = "CORNERS_OVER_UNDER_10_5_PROBABILITY"
TYPE_VALUEBET = "VALUEBET"

# Map of prediction types to human-readable names
PREDICTION_TYPE_NAMES = {
    TYPE_BTTS: "Both Teams To Score",
    TYPE_MATCH_WINNER: "Match Result",
    TYPE_FIRST_HALF_WINNER: "First Half Result",
    TYPE_OVER_UNDER_15: "Over/Under 1.5 Goals",
    TYPE_OVER_UNDER_25: "Over/Under 2.5 Goals",
    TYPE_OVER_UNDER_35: "Over/Under 3.5 Goals",
    TYPE_DOUBLE_CHANCE: "Double Chance",
    TYPE_HTFT: "Half-Time/Full-Time",
    TYPE_CORRECT_SCORE: "Correct Score",
    TYPE_TEAM_SCORE_FIRST: "Team To Score First",
    TYPE_HOME_OVER_UNDER_05: "Home Team Over/Under 0.5 Goals",
    TYPE_HOME_OVER_UNDER_15: "Home Team Over/Under 1.5 Goals",
    TYPE_AWAY_OVER_UNDER_05: "Away Team Over/Under 0.5 Goals",
    TYPE_AWAY_OVER_UNDER_15: "Away Team Over/Under 1.5 Goals",
    TYPE_CORNERS_OVER_UNDER: "Corners Over/Under 10.5",
    TYPE_VALUEBET: "Value Bet"
}

def get_prediction_type_name(developer_name: str) -> str:
    """Get the human-readable name for a prediction type"""
    return PREDICTION_TYPE_NAMES.get(developer_name, developer_name)

def normalize_prediction_data(prediction_data: Dict) -> List[Dict]:
    """
    Transform prediction data from the SportMonks API to a flattened format
    
    Args:
        prediction_data: Raw prediction data from the API
        
    Returns:
        List of normalized prediction records
    """
    if not prediction_data or "predictions" not in prediction_data:
        logger.warning("Invalid prediction data format")
        return []
    
    normalized_records = []
    
    for prediction in prediction_data["predictions"]:
        try:
            fixture_id = prediction.get("fixture_id")
            prediction_id = prediction.get("id")
            
            if not fixture_id:
                logger.warning(f"Missing fixture_id in prediction: {prediction_id}")
                continue
                
            # Get the prediction type (important for interpreting the values)
            prediction_type = prediction.get("type", {})
            developer_name = prediction_type.get("developer_name", "UNKNOWN")
            type_name = prediction_type.get("name", "Unknown Prediction")
            type_id = prediction_type.get("id")
            
            # Get the prediction values (structure depends on type)
            predictions_obj = prediction.get("predictions", {})
            
            # Create base record
            base_record = {
                "prediction_id": prediction_id,
                "fixture_id": fixture_id,
                "type_id": type_id,
                "type_name": type_name,
                "developer_name": developer_name
            }
            
            # Handle different prediction types
            if developer_name == TYPE_CORRECT_SCORE:
                # Correct score has a nested structure with many possibilities
                if "scores" in predictions_obj:
                    scores = predictions_obj["scores"]
                    for score, probability in scores.items():
                        record = base_record.copy()
                        record["selection"] = score
                        record["probability"] = probability
                        normalized_records.append(record)
            
            elif developer_name == TYPE_VALUEBET:
                # Value bet has a special structure
                record = base_record.copy()
                record["selection"] = predictions_obj.get("bet", "unknown")
                record["bookmaker"] = predictions_obj.get("bookmaker")
                record["fair_odd"] = predictions_obj.get("fair_odd")
                record["odd"] = predictions_obj.get("odd")
                record["stake"] = predictions_obj.get("stake")
                record["is_value"] = predictions_obj.get("is_value", False)
                normalized_records.append(record)
                
            elif developer_name in [TYPE_MATCH_WINNER, TYPE_FIRST_HALF_WINNER, TYPE_TEAM_SCORE_FIRST]:
                # Three-way predictions (home, away, draw)
                for outcome in ["home", "away", "draw"]:
                    if outcome in predictions_obj:
                        record = base_record.copy()
                        record["selection"] = outcome
                        record["probability"] = predictions_obj[outcome]
                        normalized_records.append(record)
            
            elif developer_name == TYPE_DOUBLE_CHANCE:
                # Double chance predictions
                for outcome in ["draw_home", "draw_away", "home_away"]:
                    if outcome in predictions_obj:
                        record = base_record.copy()
                        record["selection"] = outcome
                        record["probability"] = predictions_obj[outcome]
                        normalized_records.append(record)
            
            elif developer_name == TYPE_HTFT:
                # Half time/full time predictions
                for ht in ["home", "away", "draw"]:
                    for ft in ["home", "away", "draw"]:
                        key = f"{ht}_{ft}"
                        if key in predictions_obj:
                            record = base_record.copy()
                            record["selection"] = key
                            record["probability"] = predictions_obj[key]
                            normalized_records.append(record)
            
            else:
                # Binary predictions (yes/no) and others
                for key, value in predictions_obj.items():
                    # Skip nested objects (handled separately)
                    if isinstance(value, (dict, list)):
                        continue
                        
                    record = base_record.copy()
                    record["selection"] = key
                    record["probability"] = value
                    normalized_records.append(record)
                    
        except Exception as e:
            logger.error(f"Error processing prediction: {str(e)}")
            continue
            
    return normalized_records

def convert_predictions_for_db(normalized_predictions: List[Dict]) -> List[Dict]:
    """
    Convert normalized predictions to database-ready format
    
    Args:
        normalized_predictions: List of normalized prediction records
        
    Returns:
        List of records ready for database insertion
    """
    db_records = []
    
    for pred in normalized_predictions:
        # Create DB record
        db_record = {
            "match_id": pred["fixture_id"],
            "prediction_id": pred["prediction_id"],
            "type_id": pred["type_id"],
            "type_name": pred["type_name"],
            "developer_name": pred["developer_name"],
            "selection": pred["selection"],
            "probability": pred["probability"]
        }
        
        # Add extra fields for value bets
        if pred["developer_name"] == TYPE_VALUEBET:
            db_record["bookmaker"] = pred.get("bookmaker")
            db_record["fair_odd"] = pred.get("fair_odd")
            db_record["odd"] = pred.get("odd")
            db_record["stake"] = pred.get("stake")
            db_record["is_value"] = pred.get("is_value", False)
        
        db_records.append(db_record)
    
    return db_records

def get_prediction_json_for_db(normalized_predictions: List[Dict]) -> Dict[int, Dict]:
    """
    Create JSON representations of predictions for PostgreSQL JSONB columns
    
    Args:
        normalized_predictions: List of normalized prediction records
        
    Returns:
        Dictionary of {fixture_id: {prediction data}}
    """
    predictions_by_match = {}
    
    for pred in normalized_predictions:
        fixture_id = pred["fixture_id"]
        
        if fixture_id not in predictions_by_match:
            predictions_by_match[fixture_id] = {
                "match_id": fixture_id,
                "predictions": {}
            }
            
        dev_name = pred["developer_name"]
        selection = pred["selection"]
        
        # Initialize type if needed
        if dev_name not in predictions_by_match[fixture_id]["predictions"]:
            predictions_by_match[fixture_id]["predictions"][dev_name] = {}
            
        # Special case for correct score
        if dev_name == TYPE_CORRECT_SCORE:
            if "scores" not in predictions_by_match[fixture_id]["predictions"][dev_name]:
                predictions_by_match[fixture_id]["predictions"][dev_name]["scores"] = {}
                
            predictions_by_match[fixture_id]["predictions"][dev_name]["scores"][selection] = pred["probability"]
        
        # Special case for value bet
        elif dev_name == TYPE_VALUEBET:
            predictions_by_match[fixture_id]["predictions"][dev_name] = {
                "bet": pred.get("selection"),
                "bookmaker": pred.get("bookmaker"),
                "fair_odd": pred.get("fair_odd"),
                "odd": pred.get("odd"), 
                "stake": pred.get("stake"),
                "is_value": pred.get("is_value", False)
            }
        
        # Regular case
        else:
            predictions_by_match[fixture_id]["predictions"][dev_name][selection] = pred["probability"]
    
    return predictions_by_match
