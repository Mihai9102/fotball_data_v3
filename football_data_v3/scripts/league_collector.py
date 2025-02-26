#!/usr/bin/env python3
"""
Script to collect and update league data from SportMonks API.
Uses the account API to determine which leagues are available with the current subscription.
"""

import sys
import os
import logging
import argparse
from typing import List, Dict
import json
from datetime import datetime

# Add parent directory to path
sys.path.append('/Users/mihaivictor/CascadeProjects/football_data/football_data_v3')

from api.sportmonks import SportMonksAPI
from api.account import SportMonksAccount
from database.models import Session, League

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def update_leagues(session=None, update_all: bool = False, 
                 save_to_file: bool = False, output_dir: str = "outputs") -> int:
    """
    Update league data based on subscription
    
    Args:
        session: Database session (optional)
        update_all: Whether to update all leagues or just subscription leagues
        save_to_file: Whether to save data to a file
        output_dir: Directory to save output file
        
    Returns:
        Count of leagues updated
    """
    # Create API client and account manager
    api = SportMonksAPI()
    account = SportMonksAccount(api)
    
    # Create session if not provided
    close_session = False
    if not session:
        session = Session()
        close_session = True
    
    try:
        # Get leagues either from subscription or all available
        if update_all:
            logger.info("Fetching all available leagues from API...")
            leagues_data, success = api.get_leagues()
            
            if not success:
                logger.error("Failed to fetch leagues from API")
                return 0
                
        else:
            logger.info("Fetching leagues available in your subscription...")
            leagues_data = account.get_available_leagues(force_refresh=True)
            
        if not leagues_data:
            logger.warning("No leagues found")
            return 0
            
        logger.info(f"Found {len(leagues_data)} leagues")
        
        # Save raw data to file if requested
        if save_to_file:
            os.makedirs(output_dir, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{output_dir}/leagues_{timestamp}.json"
            
            with open(filename, 'w') as f:
                json.dump(leagues_data, f, indent=2)
                
            logger.info(f"Saved raw league data to {filename}")
        
        # Update leagues in database
        leagues_updated = 0
        
        for league_data in leagues_data:
            try:
                league_id = league_data.get("id")
                if not league_id:
                    continue
                
                # Get or create league
                league = session.query(League).filter(League.id == league_id).first()
                if not league:
                    league = League(id=league_id)
                    
                # Update league attributes
                league.name = league_data.get("name")
                league.is_cup = league_data.get("is_cup", False)
                
                # Handle nested objects
                if "country" in league_data and isinstance(league_data["country"], dict):
                    league.country_id = league_data["country"].get("id")
                    league.country_name = league_data["country"].get("name")
                
                # Add flag to indicate if league is in subscription
                league.in_subscription = not update_all or True
                
                # Add to session
                session.add(league)
                leagues_updated += 1
                
            except Exception as e:
                logger.error(f"Error processing league {league_data.get('id')}: {str(e)}")
        
        # Commit changes
        session.commit()
        logger.info(f"Updated {leagues_updated} leagues in database")
        
        return leagues_updated
        
    except Exception as e:
        logger.error(f"Error updating leagues: {str(e)}")
        session.rollback()
        return 0
        
    finally:
        if close_session:
            session.close()

def create_leagues_config_file(output_file: str = None):
    """
    Create a configuration file with subscription leagues
    
    Args:
        output_file: Path to save the configuration file
    """
    # Use default path if not specified
    if not output_file:
        output_file = '/Users/mihaivictor/CascadeProjects/football_data/football_data_v3/config/subscription_leagues.py'
    
    # Get account information
    account = SportMonksAccount()
    leagues = account.get_available_leagues(force_refresh=True)
    
    if not leagues:
        logger.error("No leagues found in subscription")
        return False
    
    # Format leagues as Python dictionary
    leagues_dict = {}
    for league in leagues:
        league_id = league.get("id")
        league_name = league.get("name")
        
        if league_id and league_name:
            leagues_dict[league_id] = league_name
    
    # Create the Python file content
    content = [
        '"""',
        'Auto-generated league configuration from SportMonks subscription',
        f'Generated on {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}',
        '"""',
        '',
        '# Dictionary of supported leagues: ID -> Name',
        'SUBSCRIPTION_LEAGUES = {'
    ]
    
    # Add each league as a line
    for league_id, league_name in sorted(leagues_dict.items()):
        content.append(f'    {league_id}: "{league_name}",')
    
    # Add closing brace and additional code
    content.extend([
        '}',
        '',
        '# List of league IDs for easy filtering',
        'SUBSCRIPTION_LEAGUE_IDS = list(SUBSCRIPTION_LEAGUES.keys())',
        '',
        'def get_league_name(league_id):',
        '    """',
        '    Get league name from ID',
        '    ',
        '    Args:',
        '        league_id: League ID',
        '        ',
        '    Returns:',
        '        League name or "Unknown League" if not found',
        '    """',
        '    return SUBSCRIPTION_LEAGUES.get(league_id, "Unknown League")',
        '',
        'def is_subscription_league(league_id):',
        '    """',
        '    Check if league is in subscription',
        '    ',
        '    Args:',
        '        league_id: League ID',
        '        ',
        '    Returns:',
        '        True if league is in subscription, False otherwise',
        '    """',
        '    return league_id in SUBSCRIPTION_LEAGUES',
    ])
    
    # Write to file
    try:
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        
        with open(output_file, 'w') as f:
            f.write('\n'.join(content))
            
        logger.info(f"Created leagues configuration file: {output_file}")
        return True
        
    except Exception as e:
        logger.error(f"Error creating leagues configuration file: {str(e)}")
        return False

def main():
    parser = argparse.ArgumentParser(description="Update league data from SportMonks API")
    parser.add_argument('--all', action='store_true', help='Update all leagues, not just subscription leagues')
    parser.add_argument('--save', action='store_true', help='Save raw league data to file')
    parser.add_argument('--output-dir', default='outputs', help='Directory to save raw data')
    parser.add_argument('--config', action='store_true', help='Create a leagues configuration file')
    parser.add_argument('--config-file', help='Path for the league configuration file')
    
    args = parser.parse_args()
    
    if args.config:
        create_leagues_config_file(args.config_file)
    else:
        update_leagues(update_all=args.all, save_to_file=args.save, output_dir=args.output_dir)

if __name__ == "__main__":
    main()
