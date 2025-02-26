#!/usr/bin/env python3
"""
Example script showing how to work with odds data from SportMonks API
Demonstrates fetching and analyzing both pre-match and in-play odds
"""

import sys
import os
from datetime import datetime, timedelta
import json
import argparse
from tabulate import tabulate
import pandas as pd

# Add parent directory to path
sys.path.append('/Users/mihaivictor/CascadeProjects/football_data/football_data_v3')

from api.sportmonks import SportMonksAPI
from api.odds import (
    normalize_odds_data, 
    filter_best_odds, 
    get_1x2_probabilities,
    get_btts_probabilities,
    get_over_under_probabilities,
    analyze_market_efficiency,
    get_market_summary,
    PREFERRED_BOOKMAKERS
)
from config.markets import MARKET_1X2, MARKET_BTTS, MARKET_OVER_UNDER

def fetch_pre_match_odds_example(league_id=None, days_ahead=3):
    """Example of fetching and analyzing pre-match odds"""
    print("\n=== Pre-match Odds Example ===\n")
    
    # Create API client
    api = SportMonksAPI()
    
    # Get upcoming fixtures
    start_date = datetime.now().strftime("%Y-%m-%d")
    end_date = (datetime.now() + timedelta(days=days_ahead)).strftime("%Y-%m-%d")
    
    print(f"Fetching fixtures from {start_date} to {end_date}...")
    
    # Filter by league if specified
    league_ids = [league_id] if league_id else None
    
    fixtures, success = api.get_fixtures_between_dates(
        start_date=start_date,
        end_date=end_date,
        league_ids=league_ids
    )
    
    if not success or not fixtures:
        print("❌ No fixtures found for the specified period.")
        return
    
    print(f"✅ Found {len(fixtures)} fixtures.\n")
    
    # Select a fixture to analyze in detail
    fixture = fixtures[0]  # Use the first fixture
    fixture_id = fixture['id']
    home_team = fixture.get('localTeam', {}).get('data', {}).get('name', 'Home Team')
    away_team = fixture.get('visitorTeam', {}).get('data', {}).get('name', 'Away Team')
    league_name = fixture.get('league', {}).get('data', {}).get('name', 'Unknown League')
    match_time = fixture.get('time', {}).get('starting_at', {}).get('date_time', 'Unknown')
    
    print(f"Selected Fixture: {home_team} vs {away_team}")
    print(f"League: {league_name}")
    print(f"Time: {match_time}")
    print(f"Fixture ID: {fixture_id}\n")
    
    # Get odds for this fixture
    print(f"Fetching odds for {home_team} vs {away_team}...")
    odds_data, odds_success = api.get_pre_match_odds_by_fixture_id(fixture_id=fixture_id)
    
    if not odds_success or not odds_data:
        print("❌ No odds data available for this fixture.")
        return
    
    # Normalize the odds data
    normalized_odds = normalize_odds_data({"data": odds_data})
    print(f"✅ Found {len(normalized_odds)} odds entries.\n")
    
    # Get market summary
    market_summary = get_market_summary(normalized_odds)
    print(f"Available Markets: {len(market_summary)}")
    
    # Show top 5 markets
    market_table = []
    for i, (market_name, data) in enumerate(market_summary.items()):
        if i >= 5:  # Limit to top 5 markets
            break
        market_table.append([
            market_name,
            len(data['selections']),
            len(data['bookmakers'])
        ])
    
    print("\n== Top 5 Markets ==")
    print(tabulate(market_table, headers=["Market", "Selections", "Bookmakers"]))
    
    # Calculate probabilities for common markets
    print("\n== Market Probabilities ==")
    
    # 1X2 Market
    match_probs = get_1x2_probabilities(normalized_odds)
    if match_probs:
        print("\n1X2 Market:")
        print(f"Home Win: {match_probs.get('home', 0):.1f}%")
        print(f"Draw: {match_probs.get('draw', 0):.1f}%")
        print(f"Away Win: {match_probs.get('away', 0):.1f}%")
    
    # BTTS Market
    btts_probs = get_btts_probabilities(normalized_odds)
    if btts_probs:
        print("\nBoth Teams To Score:")
        print(f"Yes: {btts_probs.get('yes', 0)::.1f}%")
        print(f"No: {btts_probs.get('no', 0)::.1f}%")
    
    # Over/Under 2.5 Goals
    ou_probs = get_over_under_probabilities(normalized_odds, goals=2.5)
    if ou_probs:
        print("\nOver/Under 2.5 Goals:")
        print(f"Over: {ou_probs.get('over', 0):.1f}%")
        print(f"Under: {ou_probs.get('under', 0):.1f}%")
    
    # Get best odds by bookmaker
    best_odds = filter_best_odds(normalized_odds)
    
    print("\n== Best Available Odds ==")
    best_table = []
    for market, selections in best_odds.items():
        if market in [MARKET_1X2, MARKET_BTTS, MARKET_OVER_UNDER]:
            for selection, data in selections.items():
                best_table.append([
                    market,
                    selection,
                    data['value'],
                    data['bookmaker']
                ])
    
    print(tabulate(best_table, headers=["Market", "Selection", "Odds", "Bookmaker"]))
    
    # Analyze market efficiency
    market_efficiency = analyze_market_efficiency(normalized_odds, MARKET_1X2)
    
    if market_efficiency["has_data"]:
        print("\n== Market Efficiency Analysis (1X2) ==")
        print(f"Average Overround: {market_efficiency.get('avg_overround', 0):.2f}%")
        
        # Show bookmaker comparison
        if "bookmakers" in market_efficiency:
            bm_table = []
            for bm in market_efficiency["bookmakers"]:
                bm_table.append([
                    bm["name"],
                    f"{bm['overround']:.2f}%",
                    f"{bm['margin']:.2f}%"
                ])
            
            print("\nBookmaker Comparison:")
            print(tabulate(bm_table, headers=["Bookmaker", "Overround", "Margin"]))

def fetch_inplay_odds_example():
    """Example of fetching and analyzing in-play odds"""
    print("\n=== In-play Odds Example ===\n")
    
    # Create API client
    api = SportMonksAPI()
    
    # Get live matches
    print("Fetching live matches...")
    live_matches, success = api.get_live_matches_with_odds()
    
    if not success or not live_matches:
        print("❌ No live matches found at the moment.")
        return
    
    print(f"✅ Found {len(live_matches)} live matches.\n")
    
    # Select a match to analyze
    match = live_matches[0]  # Use the first match
    match_id = match['id']
    
    # Extract team names (structure might vary)
    home_team = "Home Team"
    away_team = "Away Team"
    
    if 'localTeam' in match and 'data' in match['localTeam']:
        home_team = match['localTeam']['data'].get('name', 'Home Team')
    
    if 'visitorTeam' in match and 'data' in match['visitorTeam']:
        away_team = match['visitorTeam']['data'].get('name', 'Away Team')
    
    print(f"Selected Match: {home_team} vs {away_team}")
    print(f"Match ID: {match_id}")
    
    # Get current score if available
    if 'scores' in match:
        home_score = match['scores'].get('localteam_score', 0)
        away_score = match['scores'].get('visitorteam_score', 0)
        minute = match.get('minute', 0)
        print(f"Current Score: {home_team} {home_score} - {away_score} {away_team} ({minute}')")
    
    # Get in-play odds
    print(f"\nFetching in-play odds...")
    odds_data, odds_success = api.get_inplay_odds_by_fixture_id(fixture_id=match_id)
    
    if not odds_success or not odds_data:
        print("❌ No in-play odds data available for this match.")
        return
    
    # Normalize the odds data
    normalized_odds = normalize_odds_data({"data": odds_data})
    print(f"✅ Found {len(normalized_odds)} in-play odds entries.\n")
    
    # Get market summary
    market_summary = get_market_summary(normalized_odds)
    print(f"Available Live Markets: {len(market_summary)}")
    
    # Show available in-play markets
    market_table = []
    for market_name, data in list(market_summary.items())[:7]:  # Limit to 7 markets
        market_table.append([
            market_name,
            len(data['selections']),
            len(data['bookmakers'])
        ])
    
    print("\n== Available In-play Markets ==")
    print(tabulate(market_table, headers=["Market", "Selections", "Bookmakers"]))
    
    # Get best in-play odds
    best_odds = filter_best_odds(normalized_odds)
    
    print("\n== Best Available In-play Odds ==")
    best_table = []
    
    # Show odds for next goal and match result markets if available
    next_goal_odds = []
    match_result_odds = []
    
    for market, selections in best_odds.items():
        if "next goal" in market.lower():
            for selection, data in selections.items():
                next_goal_odds.append([
                    "Next Goal",
                    selection,
                    data['value'],
                    data['bookmaker']
                ])
        elif market == MARKET_1X2:
            for selection, data in selections.items():
                match_result_odds.append([
                    "Match Result",
                    selection,
                    data['value'],
                    data['bookmaker']
                ])
    
    # Display next goal odds if available
    if next_goal_odds:
        print("\nNext Goal Market:")
        print(tabulate(next_goal_odds, headers=["Market", "Selection", "Odds", "Bookmaker"]))
    
    # Display match result odds if available
    if match_result_odds:
        print("\nMatch Result Market:")
        print(tabulate(match_result_odds, headers=["Market", "Selection", "Odds", "Bookmaker"]))
    
    print("\nNote: In-play odds change rapidly. These values might be outdated by the time you see them.")

def odds_comparison_example(league_id=None, days_ahead=3):
    """Example of comparing odds across different bookmakers"""
    print("\n=== Odds Comparison Example ===\n")
    
    # Create API client
    api = SportMonksAPI()
    
    # Get upcoming fixtures
    start_date = datetime.now().strftime("%Y-%m-%d")
    end_date = (datetime.now() + timedelta(days=days_ahead)).strftime("%Y-%m-%d")
    
    # Filter by league if specified
    league_ids = [league_id] if league_id else None
    
    fixtures, success = api.get_fixtures_between_dates(
        start_date=start_date,
        end_date=end_date,
        league_ids=league_ids
    )
    
    if not success or not fixtures:
        print("❌ No fixtures found for the specified period.")
        return
    
    # Process first 3 fixtures
    fixtures_to_process = fixtures[:3]
    
    print(f"Comparing odds for {len(fixtures_to_process)} upcoming fixtures:\n")
    
    comparison_data = []
    
    for fixture in fixtures_to_process:
        fixture_id = fixture['id']
        home_team = fixture.get('localTeam', {}).get('data', {}).get('name', 'Home Team')
        away_team = fixture.get('visitorTeam', {}).get('data', {}).get('name', 'Away Team')
        match_time = fixture.get('time', {}).get('starting_at', {}).get('date_time', 'Unknown')
        
        print(f"Processing: {home_team} vs {away_team} ({match_time})")
        
        # Get odds for this fixture
        odds_data, _ = api.get_pre_match_odds_by_fixture_id(fixture_id=fixture_id)
        
        if not odds_data:
            print(f"  No odds available for this match.")
            continue
        
        # Normalize the odds data
        normalized_odds = normalize_odds_data({"data": odds_data})
        
        # Filter for 1X2 market
        match_odds = [odd for odd in normalized_odds if odd["normalized_market"] == MARKET_1X2]
        
        if not match_odds:
            print(f"  No 1X2 odds available for this match.")
            continue
        
        # Group by bookmaker and selection
        bookmaker_odds = {}
        
        for odd in match_odds:
            bookmaker = odd["bookmaker_name"]
            selection = odd["normalized_selection"]
            
            if bookmaker not in bookmaker_odds:
                bookmaker_odds[bookmaker] = {}
            
            bookmaker_odds[bookmaker][selection] = odd["value"]
        
        # Add to comparison data
        for bookmaker, selections in bookmaker_odds.items():
            if 'home' in selections and 'draw' in selections and 'away' in selections:
                comparison_data.append({
                    'Match': f"{home_team} vs {away_team}",
                    'Time': match_time,
                    'Bookmaker': bookmaker,
                    'Home': selections['home'],
                    'Draw': selections['draw'],
                    'Away': selections['away'],
                    'Margin': calculate_margin(selections)
                })
    
    # Create DataFrame for easy comparison
    if comparison_data:
        df = pd.DataFrame(comparison_data)
        
        # Group by match and calculate min, max, and average odds
        grouped = df.groupby('Match')
        
        for match, group in grouped:
            print(f"\n=== {match} ===")
            
            # Calculate best odds
            best_home = group['Home'].max()
            best_draw = group['Draw'].max()
            best_away = group['Away'].max()
            
            # Get bookmakers offering the best odds
            best_home_bookie = group[group['Home'] == best_home]['Bookmaker'].values[0]
            best_draw_bookie = group[group['Draw'] == best_draw]['Bookmaker'].values[0]
            best_away_bookie = group[group['Away'] == best_away]['Bookmaker'].values[0]
            
            # Calculate average odds
            avg_home = group['Home'].mean()
            avg_draw = group['Draw'].mean()
            avg_away = group['Away'].mean()
            
            print(f"Home win: Best {best_home} ({best_home_bookie}), Avg {avg_home:.2f}")
            print(f"Draw: Best {best_draw} ({best_draw_bookie}), Avg {avg_draw:.2f}")
            print(f"Away win: Best {best_away} ({best_away_bookie}), Avg {avg_away:.2f}")
            
            # Calculate potential profit using best odds
            arb_margin = (1/best_home + 1/best_draw + 1/best_away) * 100 - 100
            print(f"Sharp line margin: {arb_margin:.2f}%")
            
            # Show lowest margins
            lowest_margin = group.loc[group['Margin'].idxmin()]
            print(f"\nLowest margin: {lowest_margin['Margin']:.2f}% ({lowest_margin['Bookmaker']})")
            
            # Show detailed comparison table
            odds_table = group[['Bookmaker', 'Home', 'Draw', 'Away', 'Margin']].sort_values('Margin')
            print("\nDetailed comparison:")
            print(tabulate(odds_table, headers='keys', showindex=False))

def calculate_margin(odds_dict):
    """Calculate bookmaker margin from odds"""
    probabilities = sum(1/odds for odds in odds_dict.values())
    return (probabilities - 1) * 100  # Return as percentage

def save_odds_to_file(odds_data, filename="odds_example.json"):
    """Save odds data to file"""
    try:
        with open(filename, 'w') as f:
            json.dump(odds_data, f, indent=2)
        print(f"\nSaved odds data to {filename}")
    except Exception as e:
        print(f"Error saving odds data: {e}")

def main():
    parser = argparse.ArgumentParser(description="Examples of working with SportMonks odds data")
    parser.add_argument('--league', '-l', type=int, help='League ID to filter fixtures')
    parser.add_argument('--days', '-d', type=int, default=3, help='Days ahead to look for fixtures')
    parser.add_argument('--prematch', action='store_true', help='Show pre-match odds example')
    parser.add_argument('--inplay', action='store_true', help='Show in-play odds example')
    parser.add_argument('--compare', action='store_true', help='Show odds comparison example')
    parser.add_argument('--all', action='store_true', help='Show all examples')
    
    args = parser.parse_args()
    
    # If no specific example is requested, show all
    show_all = args.all or not (args.prematch or args.inplay or args.compare)
    
    if args.prematch or show_all:
        fetch_pre_match_odds_example(args.league, args.days)
    
    if args.inplay or show_all:
        fetch_inplay_odds_example()
    
    if args.compare or show_all:
        odds_comparison_example(args.league, args.days)
        
if __name__ == "__main__":
    main()