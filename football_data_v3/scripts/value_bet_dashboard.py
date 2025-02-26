#!/usr/bin/env python3
"""
Script to create an interactive dashboard for value betting
This script generates an HTML dashboard with value bet recommendations
"""

import sys
import logging
import argparse
from datetime import datetime, timedelta
import json
import os
import webbrowser
from typing import Dict, List

# Add parent directory to path
sys.path.append('/Users/mihaivictor/CascadeProjects/football_data/football_data_v3')

from api.sportmonks import SportMonksAPI
from config.leagues import SUPPORTED_LEAGUES, get_league_name
from config.markets import MARKET_IDS, get_market_display_name

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def generate_html_dashboard(value_bets, min_edge=0.05, output_file=None):
    """
    Generate an HTML dashboard with value bet recommendations
    
    Args:
        value_bets: List of processed value bet recommendations
        min_edge: Minimum edge to display
        output_file: Optional output file path
    
    Returns:
        Path to the generated HTML file
    """
    # Filter by minimum edge
    filtered_bets = [bet for bet in value_bets if bet['edge'] >= min_edge]
    
    # Group bets by league
    bets_by_league = {}
    for bet in filtered_bets:
        league = bet['league']
        if league not in bets_by_league:
            bets_by_league[league] = []
        bets_by_league[league].append(bet)
    
    # Sort leagues by number of bets
    sorted_leagues = sorted(bets_by_league.items(), key=lambda x: len(x[1]), reverse=True)
    
    # Generate HTML
    html = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Value Bet Dashboard</title>
        <style>
            body {{
                font-family: Arial, sans-serif;
                margin: 0;
                padding: 20px;
                background-color: #f5f5f5;
            }}
            .header {{
                background-color: #2c3e50;
                color: white;
                padding: 15px;
                margin-bottom: 20px;
                border-radius: 5px;
                display: flex;
                justify-content: space-between;
                align-items: center;
            }}
            .header h1 {{
                margin: 0;
            }}
            .summary {{
                background-color: white;
                padding: 15px;
                margin-bottom: 20px;
                border-radius: 5px;
                box-shadow: 0 2px 5px rgba(0,0,0,0.1);
            }}
            .league-section {{
                background-color: white;
                padding: 15px;
                margin-bottom: 20px;
                border-radius: 5px;
                box-shadow: 0 2px 5px rgba(0,0,0,0.1);
            }}
            .league-header {{
                display: flex;
                justify-content: space-between;
                align-items: center;
                background-color: #3498db;
                color: white;
                padding: 10px;
                border-radius: 5px;
                margin-bottom: 10px;
            }}
            .league-header h2 {{
                margin: 0;
                font-size: 18px;
            }}
            table {{
                width: 100%;
                border-collapse: collapse;
            }}
            th, td {{
                padding: 10px;
                border-bottom: 1px solid #ddd;
                text-align: left;
            }}
            th {{
                background-color: #f2f2f2;
            }}
            tr:hover {{
                background-color: #f5f5f5;
            }}
            .high-value {{
                background-color: #d5f5e3;
            }}
            .controls {{
                display: flex;
                gap: 10px;
                margin-bottom: 20px;
            }}
            .controls select, .controls input {{
                padding: 5px;
                border-radius: 3px;
                border: 1px solid #ddd;
            }}
            .market-type {{
                background-color: #eaf2f8;
                padding: 3px 7px;
                border-radius: 10px;
                font-size: 12px;
            }}
            .dashboard-date {{
                font-size: 14px;
                color: #7f8c8d;
            }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>Value Bet Dashboard</h1>
            <div class="dashboard-date">Generated on {datetime.now().strftime('%Y-%m-%d %H:%M')}</div>
        </div>
        
        <div class="controls">
            <label for="min-edge">Minimum Edge:</label>
            <input type="range" id="min-edge" min="0" max="0.2" step="0.01" value="{min_edge}">
            <span id="edge-value">{min_edge:.0%}</span>
            
            <select id="market-filter">
                <option value="all">All Markets</option>
                <option value="1X2">1X2</option>
                <option value="Over/Under">Over/Under</option>
                <option value="BTTS">BTTS</option>
            </select>
            
            <select id="sort-by">
                <option value="edge">Sort by Edge</option>
                <option value="date">Sort by Date</option>
                <option value="odds">Sort by Odds</option>
            </select>
        </div>
        
        <div class="summary">
            <h2>Summary</h2>
            <p>Total value bets found: <strong>{len(filtered_bets)}</strong></p>
            <p>Leagues with value bets: <strong>{len(bets_by_league)}</strong></p>
            <p>Average edge: <strong>{sum(bet['edge'] for bet in filtered_bets) / len(filtered_bets):.1%}</strong></p>
        </div>
        
        <div id="bets-container">
    """
    
    # Add league sections
    for league, bets in sorted_leagues:
        # Sort bets by edge
        bets_sorted = sorted(bets, key=lambda x: x['edge'], reverse=True)
        
        html += f"""
        <div class="league-section" data-league="{league}">
            <div class="league-header">
                <h2>{league}</h2>
                <span>{len(bets)} value bets</span>
            </div>
            <table>
                <thead>
                    <tr>
                        <th>Date</th>
                        <th>Match</th>
                        <th>Bet</th>
                        <th>Bookmaker</th>
                        <th>Odds</th>
                        <th>Predicted Prob</th>
                        <th>Edge</th>
                    </tr>
                </thead>
                <tbody>
        """
        
        for bet in bets_sorted:
            high_value_class = "high-value" if bet['edge'] >= 0.1 else ""
            html += f"""
                <tr class="{high_value_class}" data-market="{bet['market']}">
                    <td>{bet['date']}</td>
                    <td>{bet['match']}</td>
                    <td><span class="market-type">{bet['market']}</span> {bet['selection']}</td>
                    <td>{bet['bookmaker']}</td>
                    <td>{bet['odds']:.2f}</td>
                    <td>{bet['prob']:.1%}</td>
                    <td>{bet['edge']:.1%}</td>
                </tr>
            """
        
        html += """
                </tbody>
            </table>
        </div>
        """
    
    # Add JavaScript for interactivity
    html += """
        </div>
        
        <script>
            // Interactive filtering
            document.getElementById('min-edge').addEventListener('input', function() {
                const value = parseFloat(this.value);
                document.getElementById('edge-value').textContent = (value * 100).toFixed(0) + '%';
                filterBets();
            });
            
            document.getElementById('market-filter').addEventListener('change', filterBets);
            document.getElementById('sort-by').addEventListener('change', sortBets);
            
            function filterBets() {
                const minEdge = parseFloat(document.getElementById('min-edge').value);
                const marketFilter = document.getElementById('market-filter').value;
                
                const rows = document.querySelectorAll('table tbody tr');
                
                rows.forEach(row => {
                    const edgeText = row.querySelector('td:last-child').textContent;
                    const edge = parseFloat(edgeText) / 100;
                    const market = row.getAttribute('data-market');
                    
                    let showRow = edge >= minEdge;
                    
                    if (marketFilter !== 'all' && !market.includes(marketFilter)) {
                        showRow = false;
                    }
                    
                    row.style.display = showRow ? '' : 'none';
                });
                
                // Update league sections visibility
                document.querySelectorAll('.league-section').forEach(section => {
                    const visibleRows = section.querySelectorAll('tbody tr[style=""]').length;
                    section.style.display = visibleRows > 0 ? '' : 'none';
                });
                
                // Update summary
                const visibleBets = document.querySelectorAll('tbody tr[style=""]').length;
                const visibleLeagues = document.querySelectorAll('.league-section[style=""]').length;
                
                // Calculate average edge of visible bets
                let edgeSum = 0;
                document.querySelectorAll('tbody tr[style=""]').forEach(row => {
                    const edgeText = row.querySelector('td:last-child').textContent;
                    edgeSum += parseFloat(edgeText) / 100;
                });
                
                const avgEdge = visibleBets > 0 ? (edgeSum / visibleBets) : 0;
                
                document.querySelector('.summary').innerHTML = `
                    <h2>Summary</h2>
                    <p>Total value bets found: <strong>${visibleBets}</strong></p>
                    <p>Leagues with value bets: <strong>${visibleLeagues}</strong></p>
                    <p>Average edge: <strong>${(avgEdge * 100).toFixed(1)}%</strong></p>
                `;
            }
            
            function sortBets() {
                const sortBy = document.getElementById('sort-by').value;
                
                document.querySelectorAll('.league-section').forEach(section => {
                    const table = section.querySelector('table');
                    const rows = Array.from(table.querySelectorAll('tbody tr'));
                    
                    rows.sort((a, b) => {
                        if (sortBy === 'edge') {
                            const edgeA = parseFloat(a.querySelector('td:last-child').textContent) / 100;
                            const edgeB = parseFloat(b.querySelector('td:last-child').textContent) / 100;
                            return edgeB - edgeA;
                        } else if (sortBy === 'date') {
                            const dateA = a.querySelector('td:first-child').textContent;
                            const dateB = b.querySelector('td:first-child').textContent;
                            return dateA.localeCompare(dateB);
                        } else if (sortBy === 'odds') {
                            const oddsA = parseFloat(a.querySelector('td:nth-child(5)').textContent);
                            const oddsB = parseFloat(b.querySelector('td:nth-child(5)').textContent);
                            return oddsB - oddsA;
                        }
                        return 0;
                    });
                    
                    const tbody = table.querySelector('tbody');
                    tbody.innerHTML = '';
                    rows.forEach(row => tbody.appendChild(row));
                });
            }
        </script>
    </body>
    </html>
    """
    
    # Write to file
    if not output_file:
        output_dir = 'outputs'
        os.makedirs(output_dir, exist_ok=True)
        output_file = f"{output_dir}/value_bet_dashboard_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
    
    with open(output_file, 'w') as f:
        f.write(html)
    
    return output_file

def get_and_process_value_bets(league_id=None, min_edge=0.05, min_odds=1.5):
    """
    Fetch and process value bets from SportMonks API
    
    Args:
        league_id: Optional league ID to filter
        min_edge: Minimum edge/value (probability difference)
        min_odds: Minimum odds to consider
        
    Returns:
        List of processed value bet recommendations
    """
    api = SportMonksAPI()
    
    # Prepare league filter
    league_ids = None
    if league_id:
        league_ids = [league_id]
        
    # Get value bets
    value_bets, success = api.get_value_bets(
        league_ids=league_ids,
        min_odds=min_odds
    )
    
    if not success or not value_bets:
        logger.warning("No value bets found")
        return []
    
    # Process and enrich data
    processed_bets = []
    for bet in value_bets:
        # Calculate edge
        edge = bet.get('probability', 0) - (1.0 / bet.get('odds', 999))
        if edge < min_edge:
            continue
            
        # Extract fixture info
        fixture = bet.get('fixture', {}).get('data', {})
        fixture_id = fixture.get('id')
        match_date = fixture.get('starting_at', '').replace('T', ' ').split('.')[0] if 'starting_at' in fixture else 'Unknown'
        
        # Get team names
        participants = fixture.get('participants', {}).get('data', [])
        home_team = 'Home'
        away_team = 'Away'
        
        for participant in participants:
            if participant.get('position') ==