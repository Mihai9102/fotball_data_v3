import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

from database.operations import DatabaseManager
from config.markets import (TRACKED_MARKETS, normalize_market_name, get_selection_name,
                           get_implied_probability, get_market_by_id)

logger = logging.getLogger(__name__)

class OddsProcessor:
    """Process odds data from SportMonks API"""
    
    def __init__(self, db_manager=None):
        """
        Initialize the odds processor
        
        Args:
            db_manager: Optional database manager (will create one if not provided)
        """
        self.db_manager = db_manager or DatabaseManager()
        
    def close(self):
        """Close resources"""
        if self.db_manager:
            self.db_manager.close()
        
    def process_match_odds(self, match_id: int, odds_data: List[Dict]) -> int:
        """
        Process odds data for a match
        
        Args:
            match_id: Match ID
            odds_data: Odds data from API
            
        Returns:
            Number of odds processed
        """
        if not odds_data:
            logger.info(f"No odds data for match {match_id}")
            return 0
            
        count = 0
        processed_odds = []
        
        # Process each bookmaker
        for bookmaker in odds_data:
            bookmaker_id = bookmaker.get('id')
            bookmaker_name = bookmaker.get('name')
            
            if not bookmaker_id or not bookmaker_name:
                logger.warning(f"Invalid bookmaker data for match {match_id}")
                continue
                
            # Process markets for this bookmaker
            markets = bookmaker.get('markets', [])
            
            # SportMonks can return markets in different formats
            if isinstance(markets, dict):
                # Convert dict to list for consistent processing
                markets_list = []
                for market_id, market_data in markets.items():
                    market_data['id'] = market_id
                    markets_list.append(market_data)
                markets = markets_list
                
            for market_data in markets:
                market_id = market_data.get('id')
                market_name = market_data.get('name')
                
                if not market_name:
                    # Try to resolve market name from ID
                    market_type = get_market_by_id(market_id)
                    if market_type:
                        market_name = market_type
                    else:
                        continue
                    
                # Normalize market name
                normalized_market = normalize_market_name(market_name)
                
                # Skip if not in our tracked markets
                if normalized_market not in TRACKED_MARKETS:
                    logger.debug(f"Skipping untracked market: {market_name} ({normalized_market})")
                    continue
                    
                # Process selections within the market
                selections = market_data.get('selections', [])
                
                # Selections might also be a dict in some responses
                if isinstance(selections, dict):
                    # Convert dict to list for consistent processing
                    selections_list = []
                    for selection_id, selection_data in selections.items():
                        selection_data['id'] = selection_id
                        selections_list.append(selection_data)
                    selections = selections_list
                
                for selection in selections:
                    selection_id = selection.get('id')
                    selection_name = selection.get('name')
                    value = selection.get('odds')
                    
                    if not selection_name or value is None:
                        continue
                        
                    # Try to normalize the selection name
                    normalized_selection = get_selection_name(normalized_market, selection_name)
                    
                    # Calculate implied probability
                    implied_probability = get_implied_probability(float(value))
                    
                    # Create a record that includes both original and normalized data
                    odd_record = {
                        'match_id': match_id,
                        'bookmaker_id': bookmaker_id,
                        'bookmaker_name': bookmaker_name,
                        'market_id': market_id,
                        'market_name': market_name,
                        'normalized_market': normalized_market,
                        'selection_id': selection_id,
                        'selection_name': selection_name,
                        'normalized_selection': normalized_selection,
                        'value': float(value),
                        'implied_probability': implied_probability
                    }
                    
                    processed_odds.append(odd_record)
                    count += 1
        
        # Save to database
        if processed_odds:
            success = self.db_manager.save_enriched_odds(match_id, processed_odds)
            if not success:
                logger.error(f"Failed to save odds for match {match_id}")
                return 0
            
            logger.info(f"Processed {count} odds across {len(set(o['normalized_market'] for o in processed_odds))} different markets")
        
        return count
    
    def process_live_odds(self, match_id: int, odds_data: List[Dict]) -> int:
        """
        Process live in-play odds data for a match
        
        Args:
            match_id: Match ID
            odds_data: Live odds data from API
            
        Returns:
            Number of odds processed
        """
        if not odds_data:
            logger.info(f"No live odds data for match {match_id}")
            return 0
        
        # Use the same processing logic as for pre-match odds, but mark as live
        count = 0
        processed_odds = []
        
        # Process each bookmaker
        for bookmaker in odds_data:
            bookmaker_id = bookmaker.get('id')
            bookmaker_name = bookmaker.get('name')
            
            if not bookmaker_id or not bookmaker_name:
                logger.warning(f"Invalid bookmaker data for match {match_id}")
                continue
                
            # Process markets for this bookmaker
            markets = bookmaker.get('markets', [])
            
            # SportMonks can return markets in different formats
            if isinstance(markets, dict):
                markets_list = []
                for market_id, market_data in markets.items():
                    market_data['id'] = market_id
                    markets_list.append(market_data)
                markets = markets_list
                
            for market_data in markets:
                market_id = market_data.get('id')
                market_name = market_data.get('name')
                
                if not market_name:
                    market_type = get_market_by_id(market_id)
                    if market_type:
                        market_name = market_type
                    else:
                        continue
                    
                # Normalize market name
                normalized_market = normalize_market_name(market_name)
                
                # For live odds, we don't filter by tracked markets
                
                # Process selections
                selections = market_data.get('selections', [])
                
                if isinstance(selections, dict):
                    selections_list = []
                    for selection_id, selection_data in selections.items():
                        selection_data['id'] = selection_id
                        selections_list.append(selection_data)
                    selections = selections_list
                
                for selection in selections:
                    selection_id = selection.get('id')
                    selection_name = selection.get('name')
                    value = selection.get('odds')
                    
                    if not selection_name or value is None:
                        continue
                        
                    # Normalize the selection name
                    normalized_selection = get_selection_name(normalized_market, selection_name)
                    
                    # Calculate implied probability
                    implied_probability = get_implied_probability(float(value))
                    
                    # Create record - mark as live
                    odd_record = {
                        'match_id': match_id,
                        'bookmaker_id': bookmaker_id,
                        'bookmaker_name': bookmaker_name,
                        'market_id': market_id,
                        'market_name': market_name,
                        'normalized_market': normalized_market,
                        'selection_id': selection_id,
                        'selection_name': selection_name,
                        'normalized_selection': normalized_selection,
                        'value': float(value),
                        'implied_probability': implied_probability,
                        'is_live': True  # Mark as live odds
                    }
                    
                    processed_odds.append(odd_record)
                    count += 1
        
        # Save to database - use a special method for live odds that overwrites existing records
        if processed_odds:
            success = self.db_manager.save_live_odds(match_id, processed_odds)
            if not success:
                logger.error(f"Failed to save live odds for match {match_id}")
                return 0
            
            logger.info(f"Processed {count} live odds across {len(set(o['normalized_market'] for o in processed_odds))} different markets")
        
        return count
    
    def get_best_odds(self, match_id: int, market: str, selection: str) -> Optional[float]:
        """
        Get the best (highest) odds for a specific market and selection
        
        Args:
            match_id: Match ID
            market: Market name (normalized)
            selection: Selection name or code
            
        Returns:
            Best odds value or None if not found
        """
        odds = self.db_manager.get_odds_for_market_selection(
            match_id=match_id,
            market=market,
            selection=selection
        )
        
        if not odds:
            return None
            
        # Return the highest value
        return max(o.value for o in odds)
    
    def get_market_probabilities(self, match_id: int, market: str) -> Dict[str, float]:
        """
        Calculate implied probabilities for a market
        
        Args:
            match_id: Match ID
            market: Market name (normalized)
            
        Returns:
            Dictionary of selection -> probability
        """
        # Get all odds for this market
        odds = self.db_manager.get_odds_for_market(match_id, market)
        
        if not odds:
            return {}
            
        # Group by selection and find best odds for each
        best_odds = {}
        for odd in odds:
            selection = odd.normalized_selection or odd.selection_name
            if selection not in best_odds or odd.value > best_odds[selection]:
                best_odds[selection] = odd.value
                
        # Convert odds to probabilities
        probabilities = {}
        for selection, odd_value in best_odds.items():
            probabilities[selection] = 1.0 / odd_value
            
        return probabilities
    
    def get_value_bets(self, match_id: int, threshold: float = 0.05) -> List[Dict]:
        """
        Find potential value bets by comparing bookmaker odds with predictions
        
        Args:
            match_id: Match ID
            threshold: Minimum difference in probability to be considered value
            
        Returns:
            List of potential value bet opportunities
        """
        # Get predictions for this match
        predictions = self.db_manager.get_predictions_for_match(match_id)
        
        # Get all odds for this match
        all_odds = self.db_manager.get_odds_for_match(match_id)
        
        value_bets = []
        
        # Check each prediction against corresponding odds
        for prediction in predictions:
            # Find odds for this market and selection
            market = normalize_market_name(prediction.bet_type)
            odds = [
                o for o in all_odds 
                if o.normalized_market == market and o.normalized_selection == prediction.prediction_key
            ]
            
            if not odds:
                continue
                
            # Find best odds (highest value)
            best_odd = max(odds, key=lambda o: o.value)
            
            # Calculate implied probability from odds
            implied_prob = get_implied_probability(best_odd.value)
            
            # Compare with prediction probability
            if prediction.probability > implied_prob + threshold:
                # This is a value bet - prediction probability is higher
                value_bets.append({
                    'match_id': match_id,
                    'market': market,
                    'selection': prediction.prediction_key,
                    'bookmaker': best_odd.bookmaker_name,
                    'odds': best_odd.value,
                    'implied_probability': implied_prob,
                    'prediction_probability': prediction.probability,
                    'edge': prediction.probability - implied_prob
                })
        
        return sorted(value_bets, key=lambda x: x['edge'], reverse=True)
