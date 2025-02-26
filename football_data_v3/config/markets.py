"""
Configuration file for betting markets supported by SportMonks API
Based on: https://docs.sportmonks.com/football/tutorials-and-guides/tutorials/odds-and-predictions/markets
"""

# Main Market Types (as defined in SportMonks documentation)
MARKET_1X2 = "1X2"  # Home (1), Draw (X), Away (2)
MARKET_BTTS = "btts"  # Both Teams To Score - Yes/No
MARKET_OVER_UNDER = "over_under"  # Over/Under Total Goals
MARKET_DNB = "dnb"  # Draw No Bet - Home/Away
MARKET_DOUBLE_CHANCE = "double_chance"  # Double Chance - 1X, 12, X2
MARKET_HANDICAP = "handicap"  # Handicap - Various formats
MARKET_EXACT_SCORE = "exact_score"  # Exact Score - Various score combinations
MARKET_HT_FT = "ht_ft"  # Halftime/Fulltime - Various combinations
MARKET_CORRECT_SCORE = "correct_score"  # Alternative name for Exact Score
MARKET_FIRST_SCORER = "first_scorer"  # First Goalscorer
MARKET_TEAM_GOALS = "team_goals"  # Team Goals - Home/Away goals
MARKET_CLEAN_SHEET = "clean_sheet"  # Clean Sheet - Yes/No
MARKET_TOTAL_CORNERS = "corners"  # Total Corners - Over/Under
MARKET_TOTAL_CARDS = "cards"  # Total Cards - Over/Under
MARKET_WINNER = "winner"  # Winner (typically for tournaments)
MARKET_TO_QUALIFY = "to_qualify"  # Team to Qualify (knockout stages)

# Market ID mappings (as used by SportMonks in some contexts)
MARKET_IDS = {
    1: MARKET_1X2,
    2: MARKET_OVER_UNDER,
    3: MARKET_BTTS,
    5: MARKET_EXACT_SCORE,
    6: MARKET_HANDICAP,
    8: MARKET_DNB,
    10: MARKET_DOUBLE_CHANCE,
    15: MARKET_CLEAN_SHEET,
    21: MARKET_TO_QUALIFY,
}

# Market Selection Mappings (standardized names for selections)
SELECTIONS = {
    MARKET_1X2: {
        "1": "Home",
        "X": "Draw",
        "2": "Away"
    },
    MARKET_BTTS: {
        "yes": "Yes",
        "no": "No"
    },
    MARKET_DNB: {
        "1": "Home",
        "2": "Away"
    },
    MARKET_DOUBLE_CHANCE: {
        "1X": "Home/Draw",
        "12": "Home/Away",
        "X2": "Draw/Away"
    },
    MARKET_CLEAN_SHEET: {
        "home": "Home Team",
        "away": "Away Team",
        "yes": "Yes",
        "no": "No"
    },
    MARKET_HANDICAP: {
        # Generic handlers - specific values will be normalized in the get_selection_name function
    },
    MARKET_TO_QUALIFY: {
        "1": "Home Team",
        "2": "Away Team"
    }
}

# Markets we want to track (add or remove as needed)
TRACKED_MARKETS = [
    MARKET_1X2,
    MARKET_BTTS,
    MARKET_OVER_UNDER,
    MARKET_DNB,
    MARKET_DOUBLE_CHANCE,
    MARKET_HANDICAP,
    MARKET_EXACT_SCORE,
    MARKET_CLEAN_SHEET
]

def get_market_display_name(market_name):
    """Get a human-readable market name"""
    market_display_names = {
        MARKET_1X2: "1X2 (Match Result)",
        MARKET_BTTS: "Both Teams To Score",
        MARKET_OVER_UNDER: "Over/Under Goals",
        MARKET_DNB: "Draw No Bet",
        MARKET_DOUBLE_CHANCE: "Double Chance",
        MARKET_HANDICAP: "Handicap",
        MARKET_EXACT_SCORE: "Exact Score",
        MARKET_HT_FT: "Halftime/Fulltime",
        MARKET_CORRECT_SCORE: "Correct Score",
        MARKET_FIRST_SCORER: "First Goalscorer",
        MARKET_TEAM_GOALS: "Team Goals",
        MARKET_CLEAN_SHEET: "Clean Sheet",
        MARKET_TOTAL_CORNERS: "Total Corners",
        MARKET_TOTAL_CARDS: "Total Cards",
        MARKET_WINNER: "Tournament Winner",
        MARKET_TO_QUALIFY: "To Qualify"
    }
    return market_display_names.get(market_name, market_name)

def get_market_by_id(market_id):
    """Get market type from market ID"""
    return MARKET_IDS.get(market_id)

def get_selection_name(market, code):
    """Get the human-readable selection name for a market and code"""
    if market in SELECTIONS and code in SELECTIONS[market]:
        return SELECTIONS[market][code]
    
    # Handle Over/Under goals which have dynamic values
    if market == MARKET_OVER_UNDER and isinstance(code, str):
        if code.startswith("over_"):
            value = code.replace("over_", "")
            return f"Over {value}"
        elif code.startswith("under_"):
            value = code.replace("under_", "")
            return f"Under {value}"
    
    # Handle handicap which can have various formats
    if market == MARKET_HANDICAP and isinstance(code, str):
        # Asian handicap format: "home_-1.5" means "Home -1.5"
        if code.startswith("home_"):
            value = code.replace("home_", "")
            return f"Home {value}"
        elif code.startswith("away_"):
            value = code.replace("away_", "")
            return f"Away {value}"
    
    # Handle exact scores in format "2-1", "0-0", etc.
    if market in (MARKET_EXACT_SCORE, MARKET_CORRECT_SCORE):
        # Return as is, it's already readable
        return code
    
    # Return the code if no mapping is found
    return code

def normalize_market_name(name):
    """
    Normalize market names from various formats used in the API
    to our standard internal format
    """
    if not name:
        return None
        
    name_lower = name.lower()
    
    # Common market formats in SportMonks API
    if "1x2" in name_lower or "match winner" in name_lower:
        return MARKET_1X2
    elif "btts" in name_lower or "both teams to score" in name_lower or "both teams score" in name_lower:
        return MARKET_BTTS
    elif "over/under" in name_lower or "over under" in name_lower or "total goals" in name_lower:
        return MARKET_OVER_UNDER
    elif "draw no bet" in name_lower:
        return MARKET_DNB
    elif "double chance" in name_lower:
        return MARKET_DOUBLE_CHANCE
    elif "handicap" in name_lower or "asian handicap" in name_lower:
        return MARKET_HANDICAP
    elif "exact score" in name_lower or "correct score" in name_lower:
        return MARKET_EXACT_SCORE
    elif "halftime/fulltime" in name_lower or "ht/ft" in name_lower:
        return MARKET_HT_FT
    elif "first goalscorer" in name_lower or "first scorer" in name_lower:
        return MARKET_FIRST_SCORER
    elif "clean sheet" in name_lower:
        return MARKET_CLEAN_SHEET
    elif "corner" in name_lower:
        return MARKET_TOTAL_CORNERS
    elif "card" in name_lower:
        return MARKET_TOTAL_CARDS
    elif "to qualify" in name_lower:
        return MARKET_TO_QUALIFY
    
    # Attempt to match SportMonks market IDs
    for market_id, market_type in MARKET_IDS.items():
        if f"id:{market_id}" in name_lower:
            return market_type
    
    # Return original if no mapping found
    return name

def get_implied_probability(odd_value):
    """
    Calculate implied probability from decimal odds
    
    Args:
        odd_value: Decimal odds value
        
    Returns:
        Implied probability as a value between 0.0 and 1.0
    """
    if not odd_value or odd_value <= 0:
        return 0
    
    return 1.0 / odd_value
