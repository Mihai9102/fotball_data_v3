#!/usr/bin/env python3
"""
Script to test the SportMonks API connection and verify subscription features.
This is a helpful starting point for users of the football_data module.
"""

import sys
import os
import logging
import argparse
import json
from datetime import datetime
import textwrap

# Add parent directory to path
sys.path.append('/Users/mihaivictor/CascadeProjects/football_data/football_data_v3')

from api.sportmonks import SportMonksAPI
from api.auth import AuthManager
from config.settings import SPORTMONKS_API_TOKEN, SPORTMONKS_API_KEY_PATH

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def wrap_text(text, width=80, indent=0):
    """Wrap text with optional indent"""
    indent_str = ' ' * indent
    return textwrap.fill(text, width=width, initial_indent=indent_str, subsequent_indent=indent_str)

def test_api_connection(token=None):
    """Test the API connection and display helpful information"""
    print("\n===== SportMonks API Connection Test =====\n")
    
    # Create API instance with the token if provided
    api = SportMonksAPI(api_token=token)
    
    # Test the basic connection
    success, message = api.test_connection()
    
    if success:
        print("✅ API Connection: SUCCESSFUL")
        print(f"   {message}\n")
    else:
        print("❌ API Connection: FAILED")
        print(f"   {message}\n")
        print_troubleshooting_tips()
        return False
    
    # Get detailed API status
    print("Testing API endpoints based on your subscription...\n")
    status = api.get_api_status()
    
    # Display endpoint access information
    print("API Endpoint Access:")
    for endpoint, info in status["endpoints"].items():
        if info["accessible"]:
            print(f"  ✅ {endpoint:<25} - Available")
        else:
            print(f"  ❌ {endpoint:<25} - Not available with your subscription")
    
    # Display subscription features
    print("\nDetected Subscription Features:")
    features = status["subscription"]["includes"]
    
    if "odds" in features:
        print("  ✅ Odds data: Available")
    else:
        print("  ❌ Odds data: Not available with your subscription")
        
    if "predictions" in features:
        print("  ✅ Predictions: Available")
    else:
        print("  ❌ Predictions: Not available with your subscription")
        
    if "value_bets" in features:
        print("  ✅ Value Bets: Available")
    else:
        print("  ❌ Value Bets: Not available with your subscription")
    
    # Display rate limit info
    if api.rate_limiter.limit:
        print(f"\nRate Limit: {api.rate_limiter.limit} requests per minute")
    else:
        print("\nRate Limit: Unknown (make more requests to determine)")
        
    print("\nAPI Integration Status: Ready to use! 🚀\n")
    return True

def print_troubleshooting_tips():
    """Print troubleshooting tips for API connection issues"""
    print("\n===== Troubleshooting Tips =====\n")
    
    print(wrap_text("1. Check your API token: Ensure your SportMonks API token is valid and correctly configured."))
    print(wrap_text("   You can set it in your .env file as SPORTMONKS_API_TOKEN or use the api_key_manager.py script."))
    print()
    
    print(wrap_text("2. Verify your subscription: Make sure your SportMonks subscription is active and not expired."))
    print(wrap_text("   Log in to your SportMonks account to check your subscription status."))
    print()
    
    print(wrap_text("3. Network connectivity: Check that your network can connect to external APIs."))
    print(wrap_text("   Try running: curl -I https://api.sportmonks.com/v3/football/leagues"))
    print()
    
    print(wrap_text("4. API status: Check if the SportMonks API is experiencing any issues."))
    print(wrap_text("   Visit: https://status.sportmonks.com/"))
    print()

def make_sample_request(endpoint, params=None):
    """Make a sample request to a specific endpoint and display the response"""
    if params is None:
        params = {"per_page": 1}
        
    print(f"\n===== Sample Request: {endpoint} =====\n")
    
    api = SportMonksAPI()
    data, success = api._make_request(endpoint, params)
    
    if success:
        print(f"✅ Request to '{endpoint}' successful!\n")
        print("Sample response data:")
        print(json.dumps(data, indent=2)[:1000] + "...\n" if len(json.dumps(data)) > 1000 else json.dumps(data, indent=2))
    else:
        print(f"❌ Request to '{endpoint}' failed.\n")
    
def main():
    parser = argparse.ArgumentParser(description="Test SportMonks API connection and verify subscription features")
    parser.add_argument('--token', '-t', help="API token to use for testing (optional)")
    parser.add_argument('--sample', '-s', help="Make a sample request to a specific endpoint", 
                       choices=["leagues", "fixtures", "livescores", "odds", "predictions"])
    
    args = parser.parse_args()
    
    if args.sample:
        # Map user-friendly names to actual endpoints
        endpoint_map = {
            "leagues": "leagues",
            "fixtures": "fixtures",
            "livescores": "livescores",
            "odds": "odds/pre-match",
            "predictions": "predictions/probabilities"
        }
        make_sample_request(endpoint_map[args.sample])
    else:
        test_api_connection(args.token)

if __name__ == "__main__":
    main()
