"""
Module for handling API authentication with SportMonks
Based on https://docs.sportmonks.com/football/welcome/authentication
"""

import logging
import os
from datetime import datetime
from typing import Dict, Optional, Tuple

from config.settings import SPORTMONKS_API_TOKEN, SPORTMONKS_API_KEY_PATH

logger = logging.getLogger(__name__)

class AuthManager:
    """Manage API authentication for SportMonks"""
    
    def __init__(self, api_token: str = None):
        """
        Initialize the authentication manager
        
        Args:
            api_token: Optional API token to use (will use from settings if None)
        """
        self.api_token = api_token or SPORTMONKS_API_TOKEN
        self._validate_token()
        
    def _validate_token(self):
        """
        Validate that the API token is properly set
        
        Raises:
            ValueError: If the token is missing or looks invalid
        """
        if not self.api_token:
            raise ValueError("SportMonks API token is required. Set SPORTMONKS_API_TOKEN in .env file or pass to AuthManager.")
        
        # Basic validation - tokens should be a certain length and not look like placeholders
        if len(self.api_token) < 20 or self.api_token.startswith("your_") or self.api_token.endswith("_here"):
            logger.warning("API token may be invalid. Please check your SPORTMONKS_API_TOKEN.")
    
    def get_auth_headers(self) -> Dict[str, str]:
        """
        Get the authentication headers for API requests
        
        Returns:
            Dictionary of headers including authorization
        """
        return {
            "Authorization": f"Bearer {self.api_token}",
            "Accept": "application/json"
        }
    
    @staticmethod
    def load_token_from_file(file_path: str = None) -> Optional[str]:
        """
        Load API token from a file
        
        Args:
            file_path: Path to the file containing the API token
            
        Returns:
            API token string if successful, None otherwise
        """
        path = file_path or SPORTMONKS_API_KEY_PATH
        if not path:
            logger.warning("No API key file path specified")
            return None
        
        try:
            if os.path.exists(path):
                with open(path, 'r') as f:
                    token = f.read().strip()
                    if token:
                        return token
            else:
                logger.warning(f"API key file not found: {path}")
        except Exception as e:
            logger.error(f"Error loading API token from file: {str(e)}")
        
        return None
    
    @staticmethod
    def save_token_to_file(token: str, file_path: str = None) -> bool:
        """
        Save API token to a file
        
        Args:
            token: API token to save
            file_path: Path to save the token
            
        Returns:
            Success flag
        """
        path = file_path or SPORTMONKS_API_KEY_PATH
        if not path:
            logger.warning("No API key file path specified")
            return False
        
        try:
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(path), exist_ok=True)
            
            # Write token to file
            with open(path, 'w') as f:
                f.write(token)
            
            # Set appropriate permissions - readable only by owner
            os.chmod(path, 0o600)
            
            return True
        except Exception as e:
            logger.error(f"Error saving API token to file: {str(e)}")
            return False
            
    def handle_auth_error(self, error_data: Dict) -> Tuple[str, bool]:
        """
        Process authentication errors from the API
        
        Args:
            error_data: Error data from API response
            
        Returns:
            Tuple of (error message, is_terminal)
            is_terminal indicates whether the error is terminal or might be resolved by retrying
        """
        error_message = error_data.get('message', 'Unknown authentication error')
        error_code = error_data.get('code', 0)
        
        # Handle specific error codes based on SportMonks documentation
        if error_code == 401:
            return "API key is invalid or expired. Please check your SportMonks API token.", True
        elif error_code == 403:
            return "API key doesn't have permission for this endpoint. Upgrade your subscription.", True
        elif error_code == 429:
            return "Rate limit exceeded. Try again later.", False
        
        return error_message, True
