import requests
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from ..utils.config import Config

logger = logging.getLogger(__name__)

class SportMonksAPI:
    def __init__(self, config: Config):
        self.config = config
        self.base_url = config.get('api.base_url')
        self.token = config.get('api.token')
        self.connect_timeout = config.get('api.timeouts.connect')
        self.read_timeout = config.get('api.timeouts.read')
        self.leagues = config.get('api.leagues')
    
    def _get_headers(self) -> Dict[str, str]:
        """Return headers for API requests."""
        return {
            'Authorization': f'Bearer {self.token}',
            'Accept': 'application/json'
        }
    
    def _make_request(self, endpoint: str, params: Dict[str, Any] = None) -> Dict:
        """Make a request to the SportMonks API."""
        url = f"{self.base_url}/{endpoint}"
        
        try:
            response = requests.get(
                url,
                headers=self._get_headers(),
                params=params,
                timeout=(self.connect_timeout, self.read_timeout)
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"API request failed: {e}")
            raise
    
    def get_fixtures_between_dates(self, start_date: datetime, end_date: datetime) -> Dict:
        """Get fixtures between two dates with predictions and odds."""
        start_date_str = start_date.strftime('%Y-%m-%d')
        end_date_str = end_date.strftime('%Y-%m-%d')
        
        endpoint = f"fixtures/between/{start_date_str}/{end_date_str}"
        
        params = {
            'include': ','.join(self.config.get('extraction.include')),
            'leagues': ','.join(map(str, self.leagues))
        }
        
        logger.info(f"Fetching fixtures between {start_date_str} and {end_date_str}")
        return self._make_request(endpoint, params)
    
    def get_fixtures_for_date_range(self) -> Dict:
        """Get fixtures for the configured date range from today."""
        today = datetime.now()
        
        start_date_offset = self.config.get('extraction.start_date_offset')
        end_date_offset = self.config.get('extraction.end_date_offset')
        
        start_date = today + timedelta(days=start_date_offset)
        end_date = today + timedelta(days=end_date_offset)
        
        return self.get_fixtures_between_dates(start_date, end_date)
