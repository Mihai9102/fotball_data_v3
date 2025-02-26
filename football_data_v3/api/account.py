"""
Module for managing SportMonks account information and subscription details.
Provides utility functions to check account status, available resources,
rate limits, and subscription details.
"""

import logging
from typing import Dict, List, Tuple, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class SportMonksAccount:
    """
    Class for interacting with SportMonks account endpoints and
    managing subscription information.
    """
    
    def __init__(self, api_client=None):
        """
        Initialize with an optional API client
        
        Args:
            api_client: SportMonksAPI instance (will create one if not provided)
        """
        # Import here to avoid circular imports
        from api.sportmonks import SportMonksAPI
        
        self.api = api_client or SportMonksAPI()
        self._subscription_info = None
        self._available_leagues = None
        self._available_filters = None
        self._enrichments = None
        
    def get_subscription_info(self, force_refresh: bool = False) -> Dict[str, Any]:
        """
        Get information about the current API subscription
        
        Args:
            force_refresh: Whether to force a refresh from the API
            
        Returns:
            Dictionary containing subscription details
        """
        if self._subscription_info is None or force_refresh:
            data, success = self.api._make_request("my/resources")
            
            if not success or "data" not in data:
                logger.error("Failed to retrieve subscription information")
                return {}
                
            self._subscription_info = data
            
        return self._subscription_info
    
    def get_available_resources(self) -> List[Dict]:
        """
        Get list of endpoints/resources available with current subscription
        
        Returns:
            List of resource dictionaries
        """
        info = self.get_subscription_info()
        if not info or "data" not in info:
            return []
            
        return info.get("data", [])
        
    def check_resource_access(self, resource_name: str) -> bool:
        """
        Check if a particular API resource is available with current subscription
        
        Args:
            resource_name: Name of the API resource/endpoint
            
        Returns:
            Boolean indicating if the resource is accessible
        """
        resources = self.get_available_resources()
        return any(r.get("name") == resource_name for r in resources)
    
    def get_enrichments(self) -> List[Dict]:
        """
        Get available enrichments (includes) for the current subscription
        
        Returns:
            List of available enrichment dictionaries
        """
        if self._enrichments is None:
            data, success = self.api._make_request("my/enrichments")
            
            if not success or "data" not in data:
                logger.error("Failed to retrieve enrichment information")
                return []
                
            self._enrichments = data.get("data", [])
            
        return self._enrichments
    
    def check_enrichment_access(self, enrichment_name: str) -> bool:
        """
        Check if a particular enrichment is available with current subscription
        
        Args:
            enrichment_name: Name of the enrichment
            
        Returns:
            Boolean indicating if the enrichment is accessible
        """
        enrichments = self.get_enrichments()
        return any(e.get("name") == enrichment_name for e in enrichments)
    
    def get_available_leagues(self, force_refresh: bool = False) -> List[Dict]:
        """
        Get leagues available with current subscription
        
        Args:
            force_refresh: Whether to force a refresh from the API
            
        Returns:
            List of available league dictionaries
        """
        if self._available_leagues is None or force_refresh:
            data, success = self.api._make_request("my/leagues")
            
            if not success or "data" not in data:
                logger.error("Failed to retrieve available leagues")
                return []
                
            self._available_leagues = data.get("data", [])
            
        return self._available_leagues
    
    def get_available_league_ids(self) -> List[int]:
        """
        Get IDs of leagues available with current subscription
        
        Returns:
            List of league IDs
        """
        leagues = self.get_available_leagues()
        return [league.get("id") for league in leagues if "id" in league]
    
    def get_available_filters(self) -> Dict[str, List[str]]:
        """
        Get available filters for each entity type
        
        Returns:
            Dictionary mapping entity names to available filters
        """
        if self._available_filters is None:
            data, success = self.api._make_request("filters")
            
            if not success or "data" not in data:
                logger.error("Failed to retrieve filter information")
                return {}
                
            # Process the filters into a more usable format
            filters = {}
            for entity in data.get("data", []):
                entity_name = entity.get("name")
                if entity_name:
                    filters[entity_name] = entity.get("filters", [])
                    
            self._available_filters = filters
            
        return self._available_filters
    
    def get_entity_filters(self, entity_name: str) -> List[str]:
        """
        Get available filters for a specific entity
        
        Args:
            entity_name: Name of the entity (e.g., fixtures, leagues)
            
        Returns:
            List of filter names
        """
        filters = self.get_available_filters()
        return filters.get(entity_name, [])
    
    def get_api_usage(self) -> Dict[str, Any]:
        """
        Get API usage statistics for current billing period
        
        Returns:
            Dictionary containing usage details
        """
        data, success = self.api._make_request("my/usage")
        
        if not success or "data" not in data:
            logger.error("Failed to retrieve API usage information")
            return {}
            
        return data.get("data", {})
    
    def get_rate_limit_info(self) -> Dict[str, Any]:
        """
        Get rate limit information based on subscription tier
        
        Returns:
            Dictionary with rate limit details
        """
        usage = self.get_api_usage()
        if not usage:
            return {}
            
        # Extract rate limit information
        rate_limit = {}
        
        if "rate_limit" in usage:
            rate_limit.update({
                "limit": usage["rate_limit"].get("limit"),
                "remaining": usage["rate_limit"].get("remaining"),
                "reset_at": usage["rate_limit"].get("reset_at")
            })
            
        # Add overall usage info
        if "requests" in usage:
            rate_limit["usage"] = usage["requests"]
            
        return rate_limit
    
    def has_predictions_access(self) -> bool:
        """
        Check if the current subscription has access to predictions
        
        Returns:
            Boolean indicating predictions access
        """
        return self.check_resource_access("predictions/probabilities")
    
    def has_odds_access(self) -> bool:
        """
        Check if the current subscription has access to odds
        
        Returns:
            Boolean indicating odds access
        """
        return self.check_resource_access("odds/pre-match")
        
    def has_valuebet_access(self) -> bool:
        """
        Check if the current subscription has access to value bets
        
        Returns:
            Boolean indicating value bet access
        """
        return self.check_resource_access("predictions/valuebet")
    
    def create_subscription_report(self) -> Dict:
        """
        Create a comprehensive report about the current subscription
        
        Returns:
            Dictionary with subscription details and capabilities
        """
        report = {
            "status": "success",
            "timestamp": datetime.now().isoformat(),
            "subscription": {},
            "capabilities": {},
            "rate_limits": {},
            "leagues": {
                "count": 0,
                "list": []
            }
        }
        
        try:
            # Get subscription info
            resources = self.get_available_resources()
            if resources:
                report["subscription"]["active"] = True
                report["subscription"]["resources_count"] = len(resources)
                
                # Get top-level resource categories
                categories = set()
                for resource in resources:
                    parts = resource.get("name", "").split("/")
                    if parts:
                        categories.add(parts[0])
                
                report["subscription"]["categories"] = list(categories)
            else:
                report["subscription"]["active"] = False
            
            # Check capabilities
            report["capabilities"]["has_predictions"] = self.has_predictions_access()
            report["capabilities"]["has_odds"] = self.has_odds_access()
            report["capabilities"]["has_valuebet"] = self.has_valuebet_access()
            
            # Add enrichments
            enrichments = self.get_enrichments()
            report["capabilities"]["enrichments"] = [e.get("name") for e in enrichments]
            report["capabilities"]["enrichments_count"] = len(enrichments)
            
            # Add rate limit info
            report["rate_limits"] = self.get_rate_limit_info()
            
            # Add leagues
            leagues = self.get_available_leagues()
            report["leagues"]["count"] = len(leagues)
            report["leagues"]["list"] = [
                {"id": l.get("id"), "name": l.get("name")}
                for l in leagues
            ]
            
            return report
            
        except Exception as e:
            logger.error(f"Error creating subscription report: {str(e)}")
            return {
                "status": "error",
                "message": str(e)
            }

# Helper functions for external use

def get_available_league_ids() -> List[int]:
    """
    Helper function to quickly get available league IDs
    
    Returns:
        List of league IDs
    """
    account = SportMonksAccount()
    return account.get_available_league_ids()

def check_subscription_tier() -> Dict:
    """
    Helper function to check subscription tier and available features
    
    Returns:
        Dictionary with subscription information
    """
    account = SportMonksAccount()
    return account.create_subscription_report()
