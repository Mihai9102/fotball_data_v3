"""
Module for processing odds data from SportMonks API
Provides functions to normalize and transform odds data
"""

import logging
import json
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime

from config.markets import (
    normalize_market_name, 
    get_selection_name, 
    get_implied_probability,
    MARKET_1X2, MARKET_BTTS, MARKET_OVER_UNDER, 
    MARKET_EXACT_SCORE, MARKET_DOUBLE_CHANCE
)

logger = logging.getLogger(__name__)

# Define common bookmaker IDs
BOOKMAKER_PINNACLE = 1  # Pinnacle Sports
BOOKMAKER_BET365 = 2  # Bet365
BOOKMAKER_BETFAIR = 8  # Betfair
BOOKMAKER_WILLIAM_HILL = 3  # William Hill
BOOKMAKER_UNIBET = 28  # Unibet

# Define favorite bookmakers in order of preference
PREFERRED_BOOKMAKERS = [
    BOOKMAKER_PINNACLE,
    BOOKMAKER_BET365,
    BOOKMAKER_BETFAIR,
    BOOKMAKER_WILLIAM_HILL,
    BOOKMAKER_UNIBET
]

def normalize_odds_data(odds_data: Dict) -> List[Dict]:
    """
    Normalize odds data from SportMonks API into a standardized format
    
    Args:
        odds_data: Raw odds data from the API
        
    Returns:
        List of normalized odds records
    """
    normalized_records = []
    
    # Handle pre-match odds format
    if "data" in odds_data:
        odds_list = odds_data["data"]
    # Handle direct odds object
    elif isinstance(odds_data, dict) and "fixture_id" in odds_data:
        odds_list = [odds_data]
    # Handle list of odds
    elif isinstance(odds_data, list):
        odds_list = odds_data
    else:
        logger.warning("Invalid odds data format")
        return []
    
    for odds_obj in odds_list:
        # Extract fixture ID
        fixture_id = odds_obj.get("fixture_id")
        if not fixture_id:
            logger.warning("Missing fixture_id in odds data")
            continue
        
        # Extract bookmakers and markets
        if "bookmakers" in odds_obj and "data" in odds_obj["bookmakers"]:
            bookmakers_data = odds_obj["bookmakers"]["data"]
        elif "bookmakers" in odds_obj:
            bookmakers_data = odds_obj["bookmakers"]
        else:
            continue
        
        # Process each bookmaker
        for bookmaker in bookmakers_data:
            bookmaker_id = bookmaker.get("id")
            bookmaker_name = bookmaker.get("name", "Unknown")
            
            if "markets" not in bookmaker or "data" not in bookmaker["markets"]:
                continue
                
            # Process each market
            for market in bookmaker["markets"]["data"]:
                market_id = market.get("id")
                market_name = market.get("name", "Unknown")
                
                # Normalize market name
                normalized_market = normalize_market_name(market_name)
                
                # Get outcome data
                if "odds" not in market or "data" not in market["odds"]:
                    continue
                
                # Process each selection/outcome
                for selection in market["odds"]["data"]:
                    selection_id = selection.get("id")
                    selection_name = selection.get("name", "Unknown")
                    selection_value = selection.get("value")
                    
                    if selection_value is None:
                        continue
                    
                    # Compute implied probability
                    implied_probability = get_implied_probability(selection_value)
                    
                    # Create normalized record
                    record = {
                        "match_id": fixture_id,
                        "bookmaker_id": bookmaker_id,
                        "bookmaker_name": bookmaker_name,
                        "market_id": market_id,
                        "market_name": market_name,
                        "normalized_market": normalized_market,
                        "selection_id": selection_id,
                        "selection_name": selection_name,
                        "normalized_selection": get_selection_name(normalized_market, selection_name),
                        "value": selection_value,
                        "implied_probability": implied_probability,
                        "is_live": odds_obj.get("is_live", False),
                        "timestamp": datetime.utcnow().isoformat()
                    }
                    
                    normalized_records.append(record)
    
    return normalized_records

def convert_odds_for_db(normalized_odds: List[Dict]) -> List[Dict]:
    """
    Convert normalized odds to database-ready format
    
    Args:
        normalized_odds: List of normalized odds records
        
    Returns:
        List of records ready for database insertion
    """
    return normalized_odds  # Already in the right format

def filter_best_odds(odds_data: List[Dict], market_filter: str = None, 
                   bookmaker_ids: List[int] = None) -> Dict[str, Dict]:
    """
    Filter odds data to get the best odds for each market/selection
    
    Args:
        odds_data: List of normalized odds records
        market_filter: Optional market name to filter by
        bookmaker_ids: Optional list of preferred bookmaker IDs
        
    Returns:
        Dictionary of {market_key: {selection: best_odd_value}}
    """
    if not odds_data:
        return {}
    
    # Use default preferred bookmakers if not specified
    if bookmaker_ids is None:
        bookmaker_ids = PREFERRED_BOOKMAKERS
    
    # Group odds by market and selection
    market_odds = {}
    
    for odd in odds_data:
        # Apply market filter if specified
        if market_filter and odd["normalized_market"] != market_filter:
            continue
        
        market = odd["normalized_market"] or odd["market_name"]
        selection = odd["normalized_selection"] or odd["selection_name"]
        
        # Create market key if needed
        market_key = f"{market}"
        if market_key not in market_odds:
            market_odds[market_key] = {}
        
        # Create selection key if needed
        if selection not in market_odds[market_key]:
            market_odds[market_key][selection] = {
                "highest": 0.0,
                "lowest": float('inf'),
                "bookmakers": {}
            }
        
        # Store odds by bookmaker
        bookmaker_id = odd["bookmaker_id"]
        market_odds[market_key][selection]["bookmakers"][bookmaker_id] = {
            "value": odd["value"],
            "name": odd["bookmaker_name"]
        }
        
        # Update highest/lowest values
        if odd["value"] > market_odds[market_key][selection]["highest"]:
            market_odds[market_key][selection]["highest"] = odd["value"]
            
        if odd["value"] < market_odds[market_key][selection]["lowest"]:
            market_odds[market_key][selection]["lowest"] = odd["value"]
    
    # Find the best odds (highest value) for each selection, preferring specified bookmakers
    best_odds = {}
    
    for market_key, selections in market_odds.items():
        best_odds[market_key] = {}
        
        for selection, data in selections.items():
            # Try to find odds from preferred bookmakers first
            best_value = None
            used_bookmaker = None
            
            for bookmaker_id in bookmaker_ids:
                if bookmaker_id in data["bookmakers"]:
                    best_value = data["bookmakers"][bookmaker_id]["value"]
                    used_bookmaker = data["bookmakers"][bookmaker_id]["name"]
                    break
            
            # If no preferred bookmaker, use the highest value from any bookmaker
            if best_value is None:
                best_value = data["highest"]
                # Find which bookmaker provided this value
                for bm_id, bm_data in data["bookmakers"].items():
                    if bm_data["value"] == best_value:
                        used_bookmaker = bm_data["name"]
                        break
            
            best_odds[market_key][selection] = {
                "value": best_value,
                "bookmaker": used_bookmaker
            }
    
    return best_odds

def get_market_probabilities(odds_data: List[Dict], market_name: str) -> Dict[str, float]:
    """
    Calculate probabilities from odds for a specific market
    
    Args:
        odds_data: List of normalized odds records
        market_name: Market name to calculate probabilities for
        
    Returns:
        Dictionary of {selection: probability}
    """
    best_odds = filter_best_odds(odds_data, market_filter=market_name)
    
    if not best_odds or market_name not in best_odds:
        return {}
    
    selections = best_odds[market_name]
    probabilities = {}
    
    for selection, data in selections.items():
        if data["value"] > 0:
            probabilities[selection] = get_implied_probability(data["value"]) * 100  # Convert to percentage
    
    return probabilities

def get_1x2_probabilities(odds_data: List[Dict]) -> Dict[str, float]:
    """
    Calculate 1X2 (match result) probabilities
    
    Args:
        odds_data: List of normalized odds records
        
    Returns:
        Dictionary of {home: prob, draw: prob, away: prob}
    """
    return get_market_probabilities(odds_data, MARKET_1X2)

def get_btts_probabilities(odds_data: List[Dict]) -> Dict[str, float]:
    """
    Calculate BTTS (both teams to score) probabilities
    
    Args:
        odds_data: List of normalized odds records
        
    Returns:
        Dictionary of {Yes: prob, No: prob}
    """
    return get_market_probabilities(odds_data, MARKET_BTTS)

def get_over_under_probabilities(odds_data: List[Dict], goals: float = 2.5) -> Dict[str, float]:
    """
    Calculate Over/Under probabilities for specified goals
    
    Args:
        odds_data: List of normalized odds records
        goals: Goal line (default: 2.5)
        
    Returns:
        Dictionary of {Over: prob, Under: prob}
    """
    filtered_odds = []
    
    # Filter odds for the correct goal line
    for odd in odds_data:
        if odd["normalized_market"] == MARKET_OVER_UNDER:
            selection = odd["selection_name"]
            if f"{goals}" in selection:
                filtered_odds.append(odd)
    
    return get_market_probabilities(filtered_odds, MARKET_OVER_UNDER)

def analyze_market_efficiency(odds_data: List[Dict], market_name: str) -> Dict[str, Any]:
    """
    Analyze the efficiency of a market by calculating overround and margins
    
    Args:
        odds_data: List of normalized odds records
        market_name: Market to analyze
        
    Returns:
        Dictionary with efficiency metrics
    """
    # Get all odds for the specified market
    market_odds = [odd for odd in odds_data if odd["normalized_market"] == market_name]
    
    if not market_odds:
        return {
            "market": market_name,
            "has_data": False
        }
    
    # Group by bookmaker
    bookmakers = {}
    for odd in market_odds:
        bookmaker_id = odd["bookmaker_id"]
        if bookmaker_id not in bookmakers:
            bookmakers[bookmaker_id] = {
                "id": bookmaker_id,
                "name": odd["bookmaker_name"],
                "selections": {}
            }
        
        selection = odd["normalized_selection"] or odd["selection_name"]
        bookmakers[bookmaker_id]["selections"][selection] = {
            "odd": odd["value"],
            "probability": odd["implied_probability"]
        }
    
    # Calculate overround for each bookmaker
    results = {
        "market": market_name,
        "has_data": True,
        "bookmakers": []
    }
    
    for bm_id, data in bookmakers.items():
        # Skip if not all selections are available
        if not data["selections"]:
            continue
        
        # Calculate total implied probability
        total_probability = sum(sel["probability"] for sel in data["selections"].values())
        overround = (total_probability - 1) * 100  # Convert to percentage
        
        # Calculate theoretical margin
        margin = (overround / total_probability) * 100 if total_probability > 0 else 0
        
        # Add to results
        results["bookmakers"].append({
            "id": bm_id,
            "name": data["name"],
            "overround": round(overround, 2),
            "margin": round(margin, 2),
            "selection_count": len(data["selections"])
        })
    
    # Calculate average market efficiency
    if results["bookmakers"]:
        results["avg_overround"] = sum(bm["overround"] for bm in results["bookmakers"]) / len(results["bookmakers"])
    
    return results

def get_market_summary(odds_data: List[Dict]) -> Dict[str, Any]:
    """
    Get a summary of available markets and their details
    
    Args:
        odds_data: List of normalized odds records
        
    Returns:
        Dictionary with market summary information
    """
    if not odds_data:
        return {}
    
    # Group by market
    markets = {}
    for odd in odds_data:
        market = odd["normalized_market"] or odd["market_name"]
        if market not in markets:
            markets[market] = {
                "name": market,
                "original_name": odd["market_name"],
                "selections": set(),
                "bookmakers": set()
            }
        
        markets[market]["selections"].add(odd["normalized_selection"] or odd["selection_name"])
        markets[market]["bookmakers"].add(odd["bookmaker_name"])
    
    # Convert to JSON serializable format
    result = {}
    for market, data in markets.items():
        result[market] = {
            "name": data["name"],
            "original_name": data["original_name"],
            "selections": list(data["selections"]),
            "bookmaker_count": len(data["bookmakers"]),
            "selection_count": len(data["selections"]),
            "bookmakers": list(data["bookmakers"])
        }
    
    return result
