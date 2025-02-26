import os
import sys
import json
import logging
import argparse
import requests

sys.path.append('/Users/mihaivictor/CascadeProjects/football_data/football_data_v3')

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def import_dashboard(grafana_url, api_key, dashboard_path):
    """Import a dashboard to Grafana
    
    Args:
        grafana_url: Grafana base URL
        api_key: Grafana API key
        dashboard_path: Path to the dashboard JSON file
    
    Returns:
        Success flag
    """
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    try:
        # Read dashboard file
        logger.info(f"Reading dashboard from {dashboard_path}")
        with open(dashboard_path, 'r') as f:
            dashboard = json.load(f)
        
        # Prepare payload - strip the id, version and uid to create a new dashboard
        if 'id' in dashboard:
            del dashboard['id']
        
        # Keep the uid if it exists for update or set a default one from filename
        if 'uid' not in dashboard:
            basename = os.path.basename(dashboard_path)
            dashboard['uid'] = os.path.splitext(basename)[0].replace("dashboard_", "")
        
        payload = {
            "dashboard": dashboard,
            "overwrite": True
        }
        
        # Send request
        logger.info(f"Importing dashboard: {dashboard.get('title', 'Unnamed')}")
        response = requests.post(
            f"{grafana_url.rstrip('/')}/api/dashboards/db",
            headers=headers,
            json=payload
        )
        
        response.raise_for_status()
        result = response.json()
        
        logger.info(f"Dashboard imported successfully: {result.get('url', 'Unknown URL')}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to import dashboard: {str(e)}")
        return False

def setup_grafana(grafana_url, api_key, dashboards_dir):
    """Set up Grafana dashboards
    
    Args:
        grafana_url: Grafana base URL
        api_key: Grafana API key
        dashboards_dir: Directory containing dashboard JSON files
    """
    success_count = 0
    failure_count = 0
    
    # Find all JSON files in the dashboards directory
    for file in os.listdir(dashboards_dir):
        if file.endswith(".json"):
            dashboard_path = os.path.join(dashboards_dir, file)
            
            if import_dashboard(grafana_url, api_key, dashboard_path):
                success_count += 1
            else:
                failure_count += 1
    
    logger.info(f"Grafana setup complete. Imported {success_count} dashboards, {failure_count} failures.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Set up Grafana dashboards")
    parser.add_argument("--grafana-url", default="http://localhost:3000", help="Grafana base URL")
    parser.add_argument("--api-key", required=True, help="Grafana API key")
    parser.add_argument("--dashboards-dir", default="../grafana", help="Directory containing dashboard JSON files")
    
    args = parser.parse_args()
    
    # Resolve relative path if needed
    if not os.path.isabs(args.dashboards_dir):
        script_dir = os.path.dirname(os.path.abspath(__file__))
        dashboards_dir = os.path.normpath(os.path.join(script_dir, args.dashboards_dir))
    else:
        dashboards_dir = args.dashboards_dir
    
    setup_grafana(args.grafana_url, args.api_key, dashboards_dir)
