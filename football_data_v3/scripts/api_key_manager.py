#!/usr/bin/env python3
"""
Script to manage API keys for SportMonks
"""

import sys
import os
import logging
import argparse
import getpass
from datetime import datetime
import requests

# Add parent directory to path
sys.path.append('/Users/mihaivictor/CascadeProjects/football_data/football_data_v3')

from api.auth import AuthManager
from config.settings import SPORTMONKS_API_KEY_PATH

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def save_api_token():
    """Prompt the user for an API token and save it"""
    print("\n=== SportMonks API Token Setup ===")
    print("\nYou can find your API token at: https://www.sportmonks.com/account/api")
    print("\nIMPORTANT: Your API token is sensitive information. It will be saved securely.")
    
    # Get API token from user
    api_token = getpass.getpass("\nEnter your SportMonks API token: ")
    
    if not api_token:
        print("No token entered. Aborting.")
        return False
    
    # Basic validation
    if len(api_token) < 20:
        print("Token seems too short. Please check and try again.")
        return False
    
    # Save token
    success = AuthManager.save_token_to_file(api_token, SPORTMONKS_API_KEY_PATH)
    
    if success:
        print(f"\nAPI token saved successfully to {SPORTMONKS_API_KEY_PATH}")
        print("File permissions have been set to be readable only by the current user.")
        return True
    else:
        print("\nFailed to save API token. Please try again.")
        return False

def test_api_token():
    """Test the API token by making a simple API call"""
    print("\n=== Testing SportMonks API Token ===")
    
    # Load token
    token = AuthManager.load_token_from_file(SPORTMONKS_API_KEY_PATH)
    
    if not token:
        print("No API token found. Please set up your token first.")
        return False
    
    # Create auth manager with the token
    auth = AuthManager(token)
    
    try:
        # Make test request to a simple endpoint
        headers = auth.get_auth_headers()
        response = requests.get(
            "https://api.sportmonks.com/v3/football/leagues",
            headers=headers,
            params={"per_page": 1}
        )
        
        if response.status_code == 200:
            print("\nAPI token is valid! Test request successful.")
            return True
        elif response.status_code == 401:
            print("\nAPI token is invalid. Please check your token and try again.")
            return False
        elif response.status_code == 403:
            print("\nAPI token is valid but doesn't have permission for the test endpoint.")
            print("This might be due to your subscription plan.")
            return True
        else:
            print(f"\nTest request failed with status code: {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"\nError testing API token: {str(e)}")
        return False

def view_api_token():
    """View the saved API token (masked)"""
    token = AuthManager.load_token_from_file(SPORTMONKS_API_KEY_PATH)
    
    if not token:
        print("\nNo API token found.")
        return
    
    # Mask the token, showing only first 4 and last 4 characters
    if len(token) > 10:
        masked = token[:4] + '*' * (len(token) - 8) + token[-4:]
    else:
        masked = '********'
    
    print(f"\nSaved API token: {masked}")
    
    # Show when the token file was last modified
    try:
        mod_time = os.path.getmtime(SPORTMONKS_API_KEY_PATH)
        mod_date = datetime.fromtimestamp(mod_time).strftime('%Y-%m-%d %H:%M:%S')
        print(f"Last updated: {mod_date}")
    except:
        pass

def main():
    parser = argparse.ArgumentParser(description="Manage SportMonks API keys")
    parser.add_argument('--setup', action='store_true', help='Set up a new API token')
    parser.add_argument('--test', action='store_true', help='Test the current API token')
    parser.add_argument('--view', action='store_true', help='View the current API token (masked)')
    
    args = parser.parse_args()
    
    if args.setup:
        save_api_token()
    elif args.test:
        test_api_token()
    elif args.view:
        view_api_token()
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
