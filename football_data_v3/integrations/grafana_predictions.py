"""
Module for preparing SportMonks prediction data for visualization in Grafana dashboards.
Handles the complex structure of different prediction types for optimal display.
"""

import logging
import json
import pandas as pd
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
import sqlalchemy as sa
from sqlalchemy import text

# Project imports
from api.sportmonks import SportMonksAPI
from api.predictions import normalize_prediction_data
from database.models import Session, Match, Prediction

logger = logging.getLogger(__name__)

# Define prediction type categories for grouping in dashboards
PREDICTION_CATEGORIES = {
    "match_result": [
        "FULLTIME_RESULT_PROBABILITY",
        "FIRST_HALF_WINNER_PROBABILITY", 
        "DOUBLE_CHANCE_PROBABILITY",
        "TEAM_TO_SCORE_FIRST_PROBABILITY"
    ],
    "goals": [
        "OVER_UNDER_1_5_PROBABILITY",
        "OVER_UNDER_2_5_PROBABILITY",
        "OVER_UNDER_3_5_PROBABILITY",
        "BTTS_PROBABILITY",
        "HOME_OVER_UNDER_0_5_PROBABILITY",
        "HOME_OVER_UNDER_1_5_PROBABILITY",
        "AWAY_OVER_UNDER_0_5_PROBABILITY",
        "AWAY_OVER_UNDER_1_5_PROBABILITY"
    ],
    "special": [
        "CORRECT_SCORE_PROBABILITY",
        "HTFT_PROBABILITY",
        "CORNERS_OVER_UNDER_10_5_PROBABILITY"
    ],
    "value_bets": ["VALUEBET"]
}

class GrafanaPredictionHelper:
    """
    Helper class for preparing SportMonks prediction data for Grafana dashboards
    """
    def __init__(self, db_session=None):
        """Initialize with an optional database session"""
        self.session = db_session or Session()
        self.api = SportMonksAPI()

    def close(self):
        """Close the database session"""
        if self.session:
            self.session.close()

    def get_prediction_data_for_matches(self, match_ids: List[int]) -> pd.DataFrame:
        """
        Get predictions for specified matches in a format ready for Grafana visualization
        
        Args:
            match_ids: List of match/fixture IDs
            
        Returns:
            DataFrame with prediction data ready for pivoting
        """
        if not match_ids:
            return pd.DataFrame()
            
        try:
            # Query for predictions
            query = self.session.query(Prediction).filter(
                Prediction.match_id.in_(match_ids)
            ).all()
            
            # Convert to list of dicts for easier processing
            data = []
            for pred in query:
                data.append({
                    "match_id": pred.match_id,
                    "type": pred.developer_name,
                    "selection": pred.selection,
                    "probability": pred.probability,
                    "bookmaker": pred.bookmaker,
                    "fair_odd": pred.fair_odd,
                    "odd": pred.odd,
                    "is_value": pred.is_value
                })
            
            return pd.DataFrame(data)
        except Exception as e:
            logger.error(f"Error getting prediction data: {e}")
            return pd.DataFrame()

    def get_upcoming_matches_with_predictions(self, days_ahead: int = 7, 
                                            league_ids: Optional[List[int]] = None) -> pd.DataFrame:
        """
        Get upcoming matches with predictions in a format ready for Grafana
        
        Args:
            days_ahead: Number of days ahead to look
            league_ids: Optional list of league IDs to filter by
            
        Returns:
            DataFrame with match and prediction data ready for pivoting
        """
        try:
            # Get upcoming matches
            end_date = datetime.now() + timedelta(days=days_ahead)
            
            # Build the query for matches
            match_query = self.session.query(Match).filter(
                Match.starting_at_timestamp > datetime.now(),
                Match.starting_at_timestamp <= end_date
            )
            
            # Add league filter if specified
            if league_ids:
                match_query = match_query.filter(Match.league_id.in_(league_ids))
            
            # Execute query and get matches
            matches = match_query.all()
            if not matches:
                return pd.DataFrame()
            
            # Get match IDs
            match_ids = [match.id for match in matches]
            
            # Get predictions for these matches
            predictions_df = self.get_prediction_data_for_matches(match_ids)
            if predictions_df.empty:
                return pd.DataFrame()
            
            # Create match data dataframe
            match_data = []
            for match in matches:
                match_data.append({
                    "match_id": match.id,
                    "starting_at": match.starting_at_timestamp,
                    "league_name": match.league_name,
                    "home_team": match.localteam_name,
                    "away_team": match.visitorteam_name,
                    "status": match.status
                })
            
            matches_df = pd.DataFrame(match_data)
            
            # Merge match data with predictions
            merged_df = pd.merge(
                matches_df, 
                predictions_df, 
                on="match_id", 
                how="left"
            )
            
            return merged_df
            
        except Exception as e:
            logger.error(f"Error getting upcoming matches with predictions: {e}")
            return pd.DataFrame()

    def create_prediction_pivot_table(self, days_ahead: int = 7, 
                                    league_ids: Optional[List[int]] = None) -> pd.DataFrame:
        """
        Create a pivot table of predictions for upcoming matches
        Similar to what Grafana would create with its pivot transform
        
        Args:
            days_ahead: Number of days ahead to look
            league_ids: Optional list of league IDs to filter by
            
        Returns:
            Pivot table DataFrame
        """
        # Get the base data
        df = self.get_upcoming_matches_with_predictions(days_ahead, league_ids)
        if df.empty:
            return df
            
        # Create pivot table
        try:
            pivot_df = df.pivot_table(
                index=["match_id", "starting_at", "league_name", "home_team", "away_team"],
                columns=["type", "selection"],
                values="probability",
                aggfunc="first"  # In case of duplicates
            )
            
            # Reset index to make it more usable
            pivot_df = pivot_df.reset_index()
            
            return pivot_df
        except Exception as e:
            logger.error(f"Error creating prediction pivot table: {e}")
            return df

    def export_to_csv(self, days_ahead: int = 7, filepath: str = "prediction_pivot.csv"):
        """
        Export prediction pivot table to CSV
        
        Args:
            days_ahead: Number of days ahead to look
            filepath: Path to save the CSV file
        """
        pivot_df = self.create_prediction_pivot_table(days_ahead)
        if pivot_df.empty:
            logger.warning("No data to export")
            return False
            
        try:
            pivot_df.to_csv(filepath)
            logger.info(f"Exported prediction pivot table to {filepath}")
            return True
        except Exception as e:
            logger.error(f"Error exporting to CSV: {e}")
            return False

    def fetch_and_store_predictions(self, days_ahead: int = 7):
        """
        Fetch new predictions from API and store in database
        
        Args:
            days_ahead: Number of days ahead to fetch
            
        Returns:
            Tuple of (matches_processed, success_count)
        """
        start_date = datetime.now().strftime("%Y-%m-%d")
        end_date = (datetime.now() + timedelta(days=days_ahead)).strftime("%Y-%m-%d")
        
        # Get fixtures from API
        fixtures, success = self.api.get_fixtures_between_dates(
            start_date=start_date,
            end_date=end_date,
            include_predictions=True
        )
        
        if not success or not fixtures:
            logger.warning("No fixtures returned from API")
            return 0, 0
            
        success_count = 0
        for fixture in fixtures:
            fixture_id = fixture.get("id")
            
            # Check if we have predictions
            if "predictions" not in fixture or not fixture["predictions"].get("data"):
                continue
                
            # Normalize prediction data
            prediction_data = {"predictions": fixture["predictions"].get("data", [])}
            normalized_predictions = normalize_prediction_data(prediction_data)
            
            # Store in database
            if normalized_predictions:
                self._store_predictions(fixture_id, normalized_predictions)
                success_count += 1
                
        return len(fixtures), success_count

    def _store_predictions(self, fixture_id: int, predictions: List[Dict]) -> bool:
        """
        Store normalized predictions in the database
        
        Args:
            fixture_id: Match/fixture ID
            predictions: Normalized prediction records
            
        Returns:
            Success flag
        """
        try:
            # Delete existing predictions for this match
            self.session.query(Prediction).filter(Prediction.match_id == fixture_id).delete()
            
            # Store new predictions
            for pred in predictions:
                prediction = Prediction(
                    match_id=fixture_id,
                    prediction_id=pred.get("prediction_id"),
                    type_id=pred.get("type_id"),
                    type_name=pred.get("type_name"),
                    developer_name=pred.get("developer_name"),
                    selection=pred.get("selection"),
                    probability=pred.get("probability"),
                    bookmaker=pred.get("bookmaker"),
                    fair_odd=pred.get("fair_odd"),
                    odd=pred.get("odd"),
                    stake=pred.get("stake"),
                    is_value=pred.get("is_value", False)
                )
                self.session.add(prediction)
                
            self.session.commit()
            return True
            
        except Exception as e:
            logger.error(f"Error storing predictions for fixture {fixture_id}: {e}")
            self.session.rollback()
            return False

    @staticmethod
    def get_grafana_sql_queries(prediction_types: List[str] = None):
        """
        Get SQL queries for a Grafana dashboard with specified prediction types
        
        Args:
            prediction_types: List of prediction types to include (default: all)
            
        Returns:
            Dictionary with SQL queries
        """
        # Default query for matches
        match_query = """
SELECT
    m.id AS "Match ID",
    m.starting_at_timestamp AS "Time",
    l.name AS "League",
    lt.name AS "Home Team",
    vt.name AS "Away Team"
FROM matches m
JOIN teams lt ON m.localteam_id = lt.id
JOIN teams vt ON m.visitorteam_id = vt.id
LEFT JOIN leagues l ON m.league_id = l.id
WHERE m.starting_at_timestamp BETWEEN NOW() AND NOW() + INTERVAL '$days_ahead days'
  AND ($league_id = 'All' OR m.league_id IN ($league_id))
ORDER BY m.starting_at_timestamp;
        """
        
        # Build prediction query with type filter if specified
        pred_query = """
SELECT
    p.match_id AS "Match ID",
    p.developer_name AS tip_predictie,
    CASE
        WHEN p.developer_name = 'CORRECT_SCORE_PROBABILITY' THEN 'scores'
        WHEN p.developer_name = 'VALUEBET' THEN 'bet'
        ELSE p.selection
    END as predictie,
    p.probability AS probabilitate
FROM predictions p
JOIN matches m ON p.match_id = m.id
WHERE m.starting_at_timestamp BETWEEN NOW() AND NOW() + INTERVAL '$days_ahead days'
  AND ($league_id = 'All' OR m.league_id IN ($league_id))
"""

        # Add prediction type filter if specified
        if prediction_types:
            pred_types_str = "', '".join(prediction_types)
            pred_query += f"  AND p.developer_name IN ('{pred_types_str}')\n"
            
        # Default odds query
        odds_query = """
SELECT
   m.id AS "Match ID",
   o.bookmaker_id,
   o.bookmaker_name,
   o.market_name AS tip_pariu,
   o.selection_name AS selectie,
   o.value AS cota
FROM matches m
JOIN odds o on m.id = o.match_id
WHERE m.starting_at_timestamp BETWEEN NOW() AND NOW() + INTERVAL '$days_ahead days'
 AND ($league_id = 'All' OR m.league_id IN ($league_id));
"""
        
        return {
            "matches": match_query,
            "predictions": pred_query,
            "odds": odds_query
        }

def get_prediction_distributions(session, days_ahead=7, league_ids=None):
    """
    Get distribution statistics for different prediction types
    Useful for setting up Grafana thresholds
    
    Args:
        session: Database session
        days_ahead: Days to look ahead
        league_ids: Optional list of league IDs
        
    Returns:
        Dictionary with statistics for each prediction type
    """
    try:
        # Build base query
        query = """
        SELECT 
            p.developer_name, 
            p.selection, 
            COUNT(*) as count, 
            MIN(p.probability) as min_prob, 
            AVG(p.probability) as avg_prob, 
            MAX(p.probability) as max_prob
        FROM predictions p
        JOIN matches m ON p.match_id = m.id
        WHERE m.starting_at_timestamp BETWEEN NOW() AND NOW() + INTERVAL :days DAY
        """
        
        # Add league filter if specified
        params = {"days": days_ahead}
        if league_ids:
            query += " AND m.league_id IN :league_ids"
            params["league_ids"] = tuple(league_ids)
        
        # Group by prediction type and selection
        query += " GROUP BY p.developer_name, p.selection"
        
        # Execute query
        result = session.execute(text(query), params)
        
        # Process results into a structured format
        stats = {}
        for row in result:
            dev_name = row.developer_name
            selection = row.selection
            
            if dev_name not in stats:
                stats[dev_name] = {"selections": {}}
                
            stats[dev_name]["selections"][selection] = {
                "count": row.count,
                "min": float(row.min_prob),
                "avg": float(row.avg_prob),
                "max": float(row.max_prob)
            }
            
        return stats
        
    except Exception as e:
        logger.error(f"Error getting prediction distributions: {e}")
        return {}

def generate_thresholds_config(stats, prediction_type, selection):
    """
    Generate Grafana threshold configuration based on statistics
    
    Args:
        stats: Statistics dictionary from get_prediction_distributions
        prediction_type: Prediction type to generate thresholds for
        selection: Specific selection/outcome
        
    Returns:
        List of threshold configurations
    """
    try:
        if prediction_type not in stats or "selections" not in stats[prediction_type]:
            return []
            
        if selection not in stats[prediction_type]["selections"]:
            return []
            
        selection_stats = stats[prediction_type]["selections"][selection]
        
        # Generate thresholds based on quartiles
        min_val = selection_stats["min"]
        avg_val = selection_stats["avg"]
        max_val = selection_stats["max"]
        
        q1 = min_val + (avg_val - min_val) / 2
        q3 = avg_val + (max_val - avg_val) / 2
        
        thresholds = [
            {"color": "green", "value": None},  # Default color
            {"color": "yellow", "value": q1},
            {"color": "orange", "value": avg_val},
            {"color": "red", "value": q3}
        ]
        
        return thresholds
        
    except Exception as e:
        logger.error(f"Error generating thresholds: {e}")
        return []
