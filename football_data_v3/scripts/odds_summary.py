#!/usr/bin/env python3
"""
Script to generate summaries of odds data stored in the database
"""

import sys
import logging
import argparse
from datetime import datetime, timedelta
from tabulate import tabulate
from collections import defaultdict

# Add parent directory to path
sys.path.append('/Users/mihaivictor/CascadeProjects/football_data/football_data_v3')

from database.operations import DatabaseManager
from config.markets import get_market_display_name, normalize_market_name, MARKET_1X2

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def show_matches_with_most_odds(db, days_ahead=3, limit=20):
    """Show matches with the most odds available"""
    start_date = datetime.now()
    end_date = start_date + timedelta(days=days_ahead)
    
    # Get upcoming matches
    matches = db.get_matches(start_date=start_date, end_date=end_date)
    
    if not matches:
        print(f"No matches found in the next {days_ahead} days")
        return
    
    # Count odds for each match
    match_odds_counts = []
    for match in matches:
        odds = db.get_odds_for_match(match.id)
        bookmakers = set(o.bookmaker_id for o in odds)
        markets = set(o.normalized_market for o in odds if o.normalized_market)
        
        match_odds_counts.append({
            'id': match.id,
            'match': f"{match.localteam_name} vs {match.visitorteam_name}",
            'league': match.league_name,
            'date': match.starting_at_timestamp.strftime("%Y-%m-%d %H:%M"),
            'odds_count': len(odds),
            'bookmakers': len(bookmakers),
            'markets': len(markets)
        })
    
    # Sort by odds count (most first)
    match_odds_counts.sort(key=lambda x: x['odds_count'], reverse=True)
    
    # Display table
    table_data = []
    for i, match in enumerate(match_odds_counts[:limit]):
        table_data.append([
            i+1,
            match['match'],
            match['league'],
            match['date'],
            match['odds_count'],
            match['bookmakers'],
            match['markets']
        ])
    
    headers = ["#", "Match", "League", "Date", "Odds", "Bookmakers", "Markets"]
    print("\nMatches with Most Odds Available:")
    print(tabulate(table_data, headers=headers, tablefmt="grid"))

def show_market_coverage(db, days_ahead=3):
    """Show coverage statistics for different markets"""
    start_date = datetime.now()
    end_date = start_date + timedelta(days=days_ahead)
    
    # Get upcoming matches
    matches = db.get_matches(start_date=start_date, end_date=end_date)
    
    if not matches:
        print(f"No matches found in the next {days_ahead} days")
        return
    
    # Count markets across all matches
    market_stats = defaultdict(lambda: {'matches': 0, 'total_odds': 0, 'bookmakers': set()})
    
    for match in matches:
        odds = db.get_odds_for_match(match.id)
        
        # Group by market
        markets_in_match = defaultdict(set)
        for odd in odds:
            if odd.normalized_market:
                markets_in_match[odd.normalized_market].add(odd.bookmaker_id)
        
        # Update stats
        for market, bookmakers in markets_in_match.items():
            market_stats[market]['matches'] += 1
            market_stats[market]['total_odds'] += len(bookmakers)
            market_stats[market]['bookmakers'].update(bookmakers)
    
    # Build table data
    table_data = []
    for market, stats in sorted(market_stats.items(), 
                                key=lambda x: len(x[1]['bookmakers']), 
                                reverse=True):
        coverage_pct = (stats['matches'] / len(matches)) * 100
        table_data.append([
            get_market_display_name(market),
            stats['matches'],
            f"{coverage_pct:.1f}%",
            len(stats['bookmakers']),
            stats['total_odds'],
            f"{stats['total_odds'] / stats['matches']:.1f}" if stats['matches'] > 0 else "0"
        ])
    
    headers = ["Market", "Matches", "Coverage", "Bookmakers", "Total Odds", "Avg Odds/Match"]
    print(f"\nMarket Coverage (next {days_ahead} days, {len(matches)} matches):")
    print(tabulate(table_data, headers=headers, tablefmt="grid"))

def show_1x2_odds_comparison(db, match_id):
    """Show 1X2 odds comparison for a specific match"""
    match = db.session.query(db.Match).filter_by(id=match_id).first()
    
    if not match:
        print(f"Match ID {match_id} not found")
        return
    
    print(f"\n=== {match.localteam_name} vs {match.visitorteam_name} ===")
    print(f"League: {match.league_name}")
    print(f"Date: {match.starting_at_timestamp.strftime('%Y-%m-%d %H:%M')}")
    
    # Get 1X2 odds
    odds = db.get_odds_for_market(match_id, MARKET_1X2)
    
    if not odds:
        print("No 1X2 odds found for this match")
        return
    
    # Group by bookmaker
    bookmaker_odds = defaultdict(dict)
    for odd in odds:
        if odd.normalized_selection:
            bookmaker_odds[odd.bookmaker_name][odd.normalized_selection] = odd.value
    
    # Build table
    table_data = []
    for bookmaker, selections in sorted(bookmaker_odds.items()):
        home = selections.get('Home', '')
        draw = selections.get('Draw', '')
        away = selections.get('Away', '')
        
        # Calculate margin if all odds are available
        margin = 0
        if home and draw and away:
            margin = (1/home + 1/draw + 1/away - 1) * 100
        
        table_data.append([bookmaker, home, draw, away, f"{margin:.1f}%" if margin else ""])
    
    # Sort by margin (lowest first)
    table_data.sort(key=lambda x: float(x[4].replace('%', '')) if x[4] else 999)
    
    headers = ["Bookmaker", "Home", "Draw", "Away", "Margin"]
    print("\n1X2 Odds Comparison:")
    print(tabulate(table_data, headers=headers, tablefmt="grid"))

def main():
    parser = argparse.ArgumentParser(description="Generate odds data summaries")
    parser.add_argument("--days", type=int, default=3, help="Number of days ahead to analyze")
    parser.add_argument("--top", type=int, default=20, help="Number of matches to show in top list")
    parser.add_argument("--markets", action="store_true", help="Show market coverage statistics")
    parser.add_argument("--match", type=int, help="Show 1X2 odds comparison for specific match ID")
    
    args = parser.parse_args()
    
    db = DatabaseManager()
    
    try:
        if args.match:
            show_1x2_odds_comparison(db, args.match)
        elif args.markets:
            show_market_coverage(db, args.days)
        else:
            show_matches_with_most_odds(db, args.days, args.top)
    finally:
        db.close()

if __name__ == "__main__":
    main()
