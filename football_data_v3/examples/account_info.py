#!/usr/bin/env python3
"""
Example script showing how to use the SportMonks account API
to retrieve information about your subscription and available resources.
"""

import sys
import os
import json
import argparse
from tabulate import tabulate
from datetime import datetime

# Add parent directory to path
sys.path.append('/Users/mihaivictor/CascadeProjects/football_data/football_data_v3')

from api.account import SportMonksAccount, check_subscription_tier
from api.sportmonks import SportMonksAPI

def display_account_info():
    """Display basic account and subscription information"""
    print("==== SportMonks Account Information ====\n")
    
    # Initialize API and account manager
    api = SportMonksAPI()
    account = SportMonksAccount(api)
    
    # Test API connection first
    success, message = api.test_connection()
    if not success:
        print(f"❌ API Connection Error: {message}")
        return
        
    print(f"✅ API Connection: {message}\n")
    
    # Get API usage information
    usage = account.get_api_usage()
    if not usage:
        print("❌ Could not retrieve API usage information.")
    else:
        print("=== API Usage ===")
        if "requests" in usage:
            requests = usage["requests"]
            print(f"Current Period: {requests.get('current_period_start')} to {requests.get('current_period_end')}")
            print(f"Total Requests: {requests.get('count', 0):,}")
        
        if "rate_limit" in usage:
            rate = usage["rate_limit"]
            print(f"Rate Limit: {rate.get('limit', 'Unknown')} requests per minute")
            print(f"Remaining: {rate.get('remaining', 'Unknown')} requests")
            print(f"Reset At: {rate.get('reset_at', 'Unknown')}")
    
    # Check available resources
    print("\n=== Available Resources ===")
    resources = account.get_available_resources()
    if not resources:
        print("❌ Could not retrieve resource information.")
    else:
        resource_table = []
        for resource in resources[:20]:  # Limit to first 20 for display
            resource_table.append([
                resource.get("name", "Unknown"),
                resource.get("type", "Unknown"),
                "✓" if resource.get("enabled", False) else "✗"
            ])
            
        print(tabulate(resource_table, headers=["Resource", "Type", "Enabled"]))
        
        if len(resources) > 20:
            print(f"... and {len(resources) - 20} more resources.")
    
    # Check available leagues
    print("\n=== Available Leagues ===")
    leagues = account.get_available_leagues()
    if not leagues:
        print("❌ Could not retrieve league information.")
    else:
        league_table = []
        for league in leagues[:15]:  # Limit to first 15 for display
            league_table.append([
                league.get("id", "Unknown"),
                league.get("name", "Unknown"),
                league.get("country", {}).get("name", "Unknown")
            ])
            
        print(tabulate(league_table, headers=["ID", "League", "Country"]))
        
        if len(leagues) > 15:
            print(f"... and {len(leagues) - 15} more leagues.")
    
    # Check capabilities
    print("\n=== Subscription Capabilities ===")
    capabilities = {
        "Predictions": account.has_predictions_access(),
        "Odds": account.has_odds_access(),
        "Value Bets": account.has_valuebet_access()
    }
    
    for feature, has_access in capabilities.items():
        status = "✅ Available" if has_access else "❌ Not Available"
        print(f"{feature}: {status}")
    
    # Check available enrichments
    print("\n=== Available Enrichments (includes) ===")
    enrichments = account.get_enrichments()
    if not enrichments:
        print("❌ Could not retrieve enrichment information.")
    else:
        enrichment_table = []
        for enrichment in enrichments[:20]:  # Limit to first 20 for display
            enrichment_table.append([
                enrichment.get("name", "Unknown"),
                enrichment.get("type", "Unknown")
            ])
            
        print(tabulate(enrichment_table, headers=["Enrichment", "Type"]))

def export_subscription_report(output_file: str = None):
    """Generate and export a full subscription report"""
    report = check_subscription_tier()
    
    # Set default filename if not provided
    if not output_file:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"sportmonks_subscription_{timestamp}.json"
    
    # Export to file
    with open(output_file, 'w') as f:
        json.dump(report, f, indent=2)
    
    print(f"📝 Subscription report exported to: {output_file}")
    
    # Print summary
    if report.get("status") == "success":
        print("\n=== Subscription Summary ===")
        print(f"Active: {report.get('subscription', {}).get('active', False)}")
        print(f"Resource Categories: {', '.join(report.get('subscription', {}).get('categories', []))}")
        print(f"Available Leagues: {report.get('leagues', {}).get('count', 0)}")
        print(f"Rate Limit: {report.get('rate_limits', {}).get('limit', 'Unknown')} requests per minute")
        
        # Print capabilities
        capabilities = report.get("capabilities", {})
        print("\n=== Feature Access ===")
        for feature, has_access in capabilities.items():
            if feature.startswith("has_"):
                feature_name = feature.replace("has_", "").capitalize()
                status = "✅ Available" if has_access else "❌ Not Available"
                print(f"{feature_name}: {status}")

def get_filter_info(entity=None):
    """Display available filters for SportMonks API entities"""
    account = SportMonksAccount()
    
    if entity:
        # Show filters for a specific entity
        filters = account.get_entity_filters(entity)
        if not filters:
            print(f"❌ No filters found for entity '{entity}'.")
            return
            
        print(f"\n=== Available Filters for {entity} ===")
        for filter_name in filters:
            print(f"- {filter_name}")
    else:
        # Show all entities with filters
        all_filters = account.get_available_filters()
        if not all_filters:
            print("❌ Could not retrieve filter information.")
            return
            
        print("\n=== Available Entity Filters ===")
        for entity_name, filters in all_filters.items():
            print(f"\n{entity_name} ({len(filters)} filters):")
            # Show first 5 filters as examples
            for filter_name in filters[:5]:
                print(f"- {filter_name}")
                
            if len(filters) > 5:
                print(f"... and {len(filters) - 5} more filters.")

def main():
    parser = argparse.ArgumentParser(description="Display SportMonks account information")
    parser.add_argument('--export', '-e', action='store_true', help='Export full subscription report to JSON')
    parser.add_argument('--output', '-o', help='Output file for subscription report')
    parser.add_argument('--filters', '-f', action='store_true', help='Show available API filters')
    parser.add_argument('--entity', help='Show filters for a specific entity')
    
    args = parser.parse_args()
    
    if args.filters or args.entity:
        get_filter_info(args.entity)
    elif args.export:
        export_subscription_report(args.output)
    else:
        display_account_info()

if __name__ == "__main__":
    main()
