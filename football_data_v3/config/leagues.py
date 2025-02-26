"""
Configuration file for supported football leagues
"""

# Dictionary of supported leagues: ID -> Name
SUPPORTED_LEAGUES = {
    8: "Premier League",
    9: "Championship",
    24: "FA Cup",
    27: "Carabao Cup",
    72: "Eredivisie",
    82: "Bundesliga",
    181: "Tipico Bundesliga",
    208: "Pro League",
    244: "1. HNL",
    271: "Superliga",
    301: "Ligue 1",
    384: "Serie A",
    387: "Serie B",
    390: "Coppa Italia",
    444: "Eliteserien",
    453: "Ekstraklasa",
    462: "Primeira Liga",
    486: "Premier League",
    501: "Premiership",
    564: "La Liga",
    567: "La Liga 2",
    570: "Copa Del Rey",
    573: "Allsvenskan",
    591: "Super League",
    600: "Super Lig",
    609: "Premier League",
    1371: "UEFA Europa League Play-offs"
}

# List of supported league IDs for easy filtering
SUPPORTED_LEAGUE_IDS = list(SUPPORTED_LEAGUES.keys())

def get_league_name(league_id):
    """
    Get the name of a league by its ID
    
    Args:
        league_id: The league ID
        
    Returns:
        The league name or "Unknown League" if not found
    """
    return SUPPORTED_LEAGUES.get(league_id, "Unknown League")

def is_supported_league(league_id):
    """
    Check if a league ID is supported
    
    Args:
        league_id: The league ID to check
        
    Returns:
        True if the league is supported, False otherwise
    """
    return league_id in SUPPORTED_LEAGUES
