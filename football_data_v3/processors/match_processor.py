import logging
from datetime import datetime
from typing import Dict, List, Optional

from api.sportmonks import SportMonksAPI
from database.operations import DatabaseManager
from processors.odds_processor import OddsProcessor
from config.settings import get_start_date, get_end_date, API_CACHE_ENABLED
from config.leagues import SUPPORTED_LEAGUE_IDS

logger = logging.getLogger(__name__)

class MatchProcessor:
    """Process matches from SportMonks API"""
    
    def __init__(self):
        # Initialize API client with cache according to settings
        self.api_client = SportMonksAPI(use_cache=API_CACHE_ENABLED)
        self.db_manager = DatabaseManager()
        self.odds_processor = OddsProcessor(db_manager=self.db_manager)
        
    def close(self):
        """Close resources"""
        self.db_manager.close()
        
    def process_matches_in_date_range(self, start_date: Optional[str] = None, end_date: Optional[str] = None) -> int:
        """
        Process all matches in a date range
        
        Args:
            start_date: Optional start date (YYYY-MM-DD)
            end_date: Optional end date (YYYY-MM-DD)
            
        Returns:
            Number of processed matches
        """
        # Use default dates if not provided
        if start_date is None:
            start_date = get_start_date()
        if end_date is None:
            end_date = get_end_date()
            
        logger.info(f"Processing matches between {start_date} and {end_date}")
        
        # Get fixtures from API
        fixtures, success = self.api_client.get_fixtures_between_dates(
            start_date=start_date,
            end_date=end_date,
            include_predictions=True,
            include_odds=True
        )
        
        if not success:
            logger.error("Failed to get fixtures from API")
            return 0
            
        # Process each fixture, filtering for supported leagues
        match_count = 0
        for fixture in fixtures:
            league_id = fixture.get('league_id')
            
            # Skip matches from unsupported leagues
            if league_id not in SUPPORTED_LEAGUE_IDS:
                logger.debug(f"Skipping match {fixture.get('id')} from unsupported league {league_id}")
                continue
                
            if self._process_single_match(fixture):
                match_count += 1
                
        logger.info(f"Successfully processed {match_count} matches from {len(SUPPORTED_LEAGUE_IDS)} supported leagues")
        return match_count
        
    def _process_single_match(self, match_data: Dict) -> bool:
        """
        Process a single match
        
        Args:
            match_data: Match data from API
            
        Returns:
            Success flag
        """
        match_id = match_data.get('id')
        if not match_id:
            logger.error("Match data missing ID")
            return False
            
        try:
            # Save match data
            match = self.db_manager.save_match(match_data)
            if not match:
                logger.error(f"Failed to save match {match_id}")
                return False
                
            # Process predictions if available
            if 'predictions' in match_data and 'data' in match_data['predictions']:
                predictions_data = match_data['predictions']['data']
                success = self.db_manager.save_predictions(match_id, predictions_data)
                if not success:
                    logger.error(f"Failed to save predictions for match {match_id}")
                    
            # Process odds if available using the dedicated odds processor
            if 'odds' in match_data and 'data' in match_data['odds']:
                odds_data = match_data['odds']['data']
                processed_count = self.odds_processor.process_match_odds(match_id, odds_data)
                logger.info(f"Processed {processed_count} odds for match {match_id}")
                    
            return True
                
        except Exception as e:
            logger.error(f"Error processing match {match_id}: {str(e)}")
            return False
            
    def process_single_match_by_id(self, match_id: int) -> bool:
        """
        Process a single match by ID
        
        Args:
            match_id: Match ID
            
        Returns:
            Success flag
        """
        # Get fixture from API
        match_data, success = self.api_client.get_fixture_by_id(
            fixture_id=match_id,
            include_predictions=True,
            include_odds=True
        )
        
        if not success:
            logger.error(f"Failed to get fixture {match_id} from API")
            return False
            
        # Process the match
        return self._process_single_match(match_data)
