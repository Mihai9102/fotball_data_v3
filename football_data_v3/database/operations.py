import logging
from typing import Dict, List, Optional, Any
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import func, or_, and_
from datetime import datetime

from database.models import Session, Match, Prediction, Odd

logger = logging.getLogger(__name__)

class DatabaseManager:
    """Handles database operations"""
    
    def __init__(self):
        self.session = Session()
        
    def close(self):
        """Close the database session"""
        self.session.close()
        
    def save_match(self, match_data: Dict) -> Optional[Match]:
        """
        Save or update match data
        
        Args:
            match_data: Match data from API
            
        Returns:
            Match object or None if error
        """
        try:
            match_id = match_data.get('id')
            
            # Check if match already exists
            match = self.session.query(Match).filter_by(id=match_id).first()
            
            if not match:
                # Create new match
                match = Match(
                    id=match_id,
                    league_id=match_data.get('league_id'),
                    localteam_id=match_data.get('localteam_id'),
                    visitorteam_id=match_data.get('visitorteam_id'),
                    starting_at_timestamp=datetime.fromisoformat(match_data.get('starting_at').replace('Z', '+00:00'))
                )
                
                # Add team and league names if available
                if 'localTeam' in match_data and 'data' in match_data['localTeam']:
                    match.localteam_name = match_data['localTeam']['data'].get('name')
                    
                if 'visitorTeam' in match_data and 'data' in match_data['visitorTeam']:
                    match.visitorteam_name = match_data['visitorTeam']['data'].get('name')
                    
                if 'league' in match_data and 'data' in match_data['league']:
                    match.league_name = match_data['league']['data'].get('name')
                
                self.session.add(match)
            else:
                # Update existing match
                if 'localTeam' in match_data and 'data' in match_data['localTeam']:
                    match.localteam_name = match_data['localTeam']['data'].get('name')
                    
                if 'visitorTeam' in match_data and 'data' in match_data['visitorTeam']:
                    match.visitorteam_name = match_data['visitorTeam']['data'].get('name')
                
                if 'scores' in match_data:
                    match.score_localteam = match_data['scores'].get('localteam_score')
                    match.score_visitorteam = match_data['scores'].get('visitorteam_score')
                    
                match.status = match_data.get('status')
                
            self.session.commit()
            return match
            
        except SQLAlchemyError as e:
            logger.error(f"Database error saving match: {str(e)}")
            self.session.rollback()
            return None
    
    def save_predictions(self, match_id: int, predictions_data: Dict) -> bool:
        """
        Save or update predictions for a match
        
        Args:
            match_id: Match ID
            predictions_data: Predictions data from API
            
        Returns:
            Success flag
        """
        if not predictions_data:
            logger.info(f"No predictions data for match {match_id}")
            return True
            
        try:
            # Get all existing predictions for this match
            existing_predictions = {
                (p.bet_type, p.prediction_key): p 
                for p in self.session.query(Prediction).filter_by(match_id=match_id).all()
            }
            
            # Process each prediction type
            for prediction_type, predictions in predictions_data.items():
                if isinstance(predictions, dict):
                    for key, value in predictions.items():
                        if isinstance(value, (int, float)):
                            # Check if prediction exists
                            pred_key = (prediction_type, key)
                            if pred_key in existing_predictions:
                                # Update existing
                                existing_predictions[pred_key].probability = float(value)
                                existing_predictions[pred_key].updated_at = datetime.utcnow()
                            else:
                                # Create new
                                new_prediction = Prediction(
                                    match_id=match_id,
                                    bet_type=prediction_type,
                                    prediction_key=key,
                                    probability=float(value)
                                )
                                self.session.add(new_prediction)
            
            self.session.commit()
            return True
            
        except SQLAlchemyError as e:
            logger.error(f"Database error saving predictions: {str(e)}")
            self.session.rollback()
            return False
    
    def save_odds(self, match_id: int, odds_data: List[Dict]) -> bool:
        """
        Save or update odds for a match
        
        Args:
            match_id: Match ID
            odds_data: Odds data from API
            
        Returns:
            Success flag
        """
        try:
            # Get all existing odds for this match
            existing_odds = {
                (o.bookmaker_id, o.market_name, o.selection_name): o 
                for o in self.session.query(Odd).filter_by(match_id=match_id).all()
            }
            
            for bookmaker in odds_data:
                bookmaker_id = bookmaker.get('id')
                bookmaker_name = bookmaker.get('name')
                
                for market in bookmaker.get('markets', []):
                    market_name = market.get('name')
                    
                    for selection in market.get('selections', []):
                        selection_name = selection.get('name')
                        value = selection.get('odds')
                        
                        if value is not None:
                            # Check if odd exists
                            odd_key = (bookmaker_id, market_name, selection_name)
                            if odd_key in existing_odds:
                                # Update existing
                                existing_odds[odd_key].value = float(value)
                                existing_odds[odd_key].updated_at = datetime.utcnow()
                            else:
                                # Create new odd
                                new_odd = Odd(
                                    match_id=match_id,
                                    bookmaker_id=bookmaker_id,
                                    bookmaker_name=bookmaker_name,
                                    market_name=market_name,
                                    selection_name=selection_name,
                                    value=float(value)
                                )
                                self.session.add(new_odd)
            
            self.session.commit()
            return True
            
        except SQLAlchemyError as e:
            logger.error(f"Database error saving odds: {str(e)}")
            self.session.rollback()
            return False
    
    def save_enriched_odds(self, match_id: int, odds_data: List[Dict]) -> bool:
        """
        Save or update enriched odds for a match
        
        Args:
            match_id: Match ID
            odds_data: Processed odds data with normalized fields
            
        Returns:
            Success flag
        """
        try:
            # Get all existing odds for this match
            existing_odds = {
                (o.bookmaker_id, o.market_name, o.selection_name): o 
                for o in self.session.query(Odd).filter_by(match_id=match_id).all()
            }
            
            for odd_record in odds_data:
                odd_key = (
                    odd_record.get('bookmaker_id'), 
                    odd_record.get('market_name'), 
                    odd_record.get('selection_name')
                )
                
                if odd_key in existing_odds:
                    # Update existing odd
                    odd = existing_odds[odd_key]
                    odd.value = odd_record.get('value')
                    odd.normalized_market = odd_record.get('normalized_market')
                    odd.normalized_selection = odd_record.get('normalized_selection')
                    odd.updated_at = datetime.utcnow()
                else:
                    # Create new odd
                    new_odd = Odd(
                        match_id=match_id,
                        bookmaker_id=odd_record.get('bookmaker_id'),
                        bookmaker_name=odd_record.get('bookmaker_name'),
                        market_id=odd_record.get('market_id'),
                        market_name=odd_record.get('market_name'),
                        normalized_market=odd_record.get('normalized_market'),
                        selection_id=odd_record.get('selection_id'),
                        selection_name=odd_record.get('selection_name'),
                        normalized_selection=odd_record.get('normalized_selection'),
                        value=odd_record.get('value')
                    )
                    self.session.add(new_odd)
            
            self.session.commit()
            return True
            
        except SQLAlchemyError as e:
            logger.error(f"Database error saving odds: {str(e)}")
            self.session.rollback()
            return False

    def save_live_odds(self, match_id: int, odds_data: List[Dict]) -> bool:
        """
        Save or update live odds for a match
        For live odds, we overwrite any existing record since we want the latest values
        
        Args:
            match_id: Match ID
            odds_data: Processed live odds data
            
        Returns:
            Success flag
        """
        try:
            # For live odds, we first delete any existing live odds for this match
            self.session.query(Odd).filter_by(match_id=match_id, is_live=True).delete()
            
            # Then insert the new live odds
            for odd_record in odds_data:
                new_odd = Odd(
                    match_id=match_id,
                    bookmaker_id=odd_record.get('bookmaker_id'),
                    bookmaker_name=odd_record.get('bookmaker_name'),
                    market_id=odd_record.get('market_id'),
                    market_name=odd_record.get('market_name'),
                    normalized_market=odd_record.get('normalized_market'),
                    selection_id=odd_record.get('selection_id'),
                    selection_name=odd_record.get('selection_name'),
                    normalized_selection=odd_record.get('normalized_selection'),
                    value=odd_record.get('value'),
                    implied_probability=odd_record.get('implied_probability', None),
                    is_live=True  # Always marked as live
                )
                self.session.add(new_odd)
            
            self.session.commit()
            return True
            
        except SQLAlchemyError as e:
            logger.error(f"Database error saving live odds: {str(e)}")
            self.session.rollback()
            return False
    
    def get_matches(self, start_date=None, end_date=None, league_ids=None) -> List[Match]:
        """
        Get matches filtered by date range and/or leagues
        
        Args:
            start_date: Optional start date
            end_date: Optional end date
            league_ids: Optional list of league IDs
            
        Returns:
            List of matches
        """
        query = self.session.query(Match)
        
        # Apply date filters
        if start_date:
            query = query.filter(Match.starting_at_timestamp >= start_date)
        
        if end_date:
            query = query.filter(Match.starting_at_timestamp <= end_date)
        
        # Apply league filter
        if league_ids:
            query = query.filter(Match.league_id.in_(league_ids))
        
        # Order by date
        query = query.order_by(Match.starting_at_timestamp)
        
        return query.all()
        
    def get_predictions_for_match(self, match_id: int) -> List[Prediction]:
        """
        Get all predictions for a specific match
        
        Args:
            match_id: Match ID
            
        Returns:
            List of Prediction objects
        """
        return self.session.query(Prediction).filter_by(match_id=match_id).all()
        
    def get_odds_for_match(self, match_id: int, bookmaker_id: Optional[int] = None) -> List[Odd]:
        """
        Get all odds for a specific match, optionally filtered by bookmaker
        
        Args:
            match_id: Match ID
            bookmaker_id: Optional bookmaker ID filter
            
        Returns:
            List of Odd objects
        """
        query = self.session.query(Odd).filter_by(match_id=match_id)
        
        if bookmaker_id is not None:
            query = query.filter_by(bookmaker_id=bookmaker_id)
            
        return query.all()
    
    def get_odds_for_market(self, match_id: int, market: str) -> List[Odd]:
        """
        Get all odds for a specific match and market
        
        Args:
            match_id: Match ID
            market: Market name (can be original or normalized)
            
        Returns:
            List of Odd objects
        """
        return self.session.query(Odd).filter(
            Odd.match_id == match_id,
            or_(
                Odd.market_name == market,
                Odd.normalized_market == market
            )
        ).all()
    
    def get_odds_for_market_selection(self, match_id: int, market: str, selection: str) -> List[Odd]:
        """
        Get odds for a specific match, market, and selection
        
        Args:
            match_id: Match ID
            market: Market name (can be original or normalized)
            selection: Selection name (can be original or normalized)
            
        Returns:
            List of Odd objects
        """
        return self.session.query(Odd).filter(
            and_(
                Odd.match_id == match_id,
                or_(
                    Odd.market_name == market,
                    Odd.normalized_market == market
                ),
                or_(
                    Odd.selection_name == selection,
                    Odd.normalized_selection == selection
                )
            )
        ).all()
