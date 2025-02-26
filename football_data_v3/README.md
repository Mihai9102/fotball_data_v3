# Football Data v3

A project for collecting and analyzing football (soccer) data from the SportMonks API v3.

## Features

- Extracts match data, predictions, and odds from SportMonks API v3
- Supports all leagues included in the "Europa Advance" plan
- Stores data in a relational database (PostgreSQL, MySQL, or SQLite)
- Updates data at regular intervals
- Visualizes data using Grafana dashboards

## Requirements

- Python 3.8+
- PostgreSQL, MySQL, or SQLite database
- SportMonks API token (Europa Advance plan)
- Grafana (for visualization)

## Setup

1. Clone the repository:

```bash
git clone <repository-url>
cd football_data_v3
```

2. Install the requirements:

```bash
pip install -r requirements.txt
```

3. Copy `.env.example` to `.env` and update with your settings:

```bash
# API Settings
SPORTMONKS_API_TOKEN=your_api_token_here

# Database Settings
DB_TYPE=postgresql  # postgresql, mysql, or sqlite
DB_HOST=localhost
DB_PORT=5432
DB_NAME=football_data
DB_USER=your_username
DB_PASSWORD=your_password

# Logging Settings
LOG_LEVEL=INFO
LOG_FILE=football_data.log
```

4. Set up your SportMonks API token (see below)

5. Test your API connection:

```bash
python scripts/test_api.py
```

6. Initialize the database:

```bash
python -m scripts.init_db
```

## Setting up your SportMonks API Token

You need a valid SportMonks API token to use this project. You can obtain one by:

1. Register on [SportMonks](https://sportmonks.com/)
2. Subscribe to a plan with API access
3. Get your API token from your account dashboard

There are two ways to set up your API token:

### Option 1: Using the API Key Manager

Use the built-in API key manager script:

```bash
python scripts/api_key_manager.py --setup
```

This will securely store your token in a file with appropriate permissions.

### Option 2: Set in .env File

Edit the `.env` file and add your token:

```
SPORTMONKS_API_TOKEN=your_token_here
```

## Testing Your API Connection

To verify your API token and subscription features:

```bash
python scripts/test_api.py
```

This will check if your token is valid and which API endpoints you can access based on your subscription.

To make a sample request to a specific endpoint:

```bash
python scripts/test_api.py --sample leagues
```

## Making Your First API Request

You can directly use the SportMonksAPI class to make requests:

```python
from api.sportmonks import SportMonksAPI

# Initialize the API client
api = SportMonksAPI()

# Get list of leagues
leagues, success = api.get_leagues()
if success:
    for league in leagues[:5]:  # Show first 5 leagues
        print(f"League: {league.get('name')}")

# Get fixtures for a specific date range
start_date = "2023-08-01"
end_date = "2023-08-07"
fixtures, success = api.get_fixtures_between_dates(
    start_date=start_date,
    end_date=end_date,
    include_odds=True
)

if success:
    print(f"Found {len(fixtures)} fixtures")
```

## Usage

### Running a Single Data Collection Job

```bash
python main.py --run-once
```

### Running with a Specific Date Range

```bash
python main.py --run-once --start-date 2023-09-01 --end-date 2023-09-30
```

### Running as a Scheduled Service

```bash
python main.py
```

This will run the data collection job according to the schedule defined in `config/settings.py` (default is every 4 hours).

## Database Schema

### Matches Table
- `id`: Primary key, match ID from SportMonks
- `league_id`: League ID
- `league_name`: Name of the league
- `localteam_id`: Home team ID
- `localteam_name`: Home team name
- `visitorteam_id`: Away team ID
- `visitorteam_name`: Away team name
- `starting_at_timestamp`: Match start time
- `status`: Match status
- `score_localteam`: Home team score
- `score_visitorteam`: Away team score

### Predictions Table
- `id`: Auto-incrementing primary key
- `match_id`: Foreign key to matches.id
- `bet_type`: Type of prediction (e.g., "1X2", "btts")
- `prediction_key`: Specific prediction (e.g., "home_win", "away_win", "btts_yes")
- `probability`: Probability value (0.0-1.0)

### Odds Table
- `id`: Auto-incrementing primary key
- `match_id`: Foreign key to matches.id
- `bookmaker_id`: Bookmaker ID
- `bookmaker_name`: Bookmaker name
- `market_name`: Market name (e.g., "1X2", "Over/Under 2.5")
- `selection_name`: Selection name (e.g., "Home", "Away", "Over 2.5")
- `value`: Odd value

## Grafana Integration

1. Set up a PostgreSQL data source in Grafana.

2. Import the dashboards using the setup script:

```bash
python -m scripts.setup_grafana --api-key your_grafana_api_key
```

3. Access the dashboards in Grafana:
   - Football Matches: Overview of all matches
   - Football Predictions: Analysis of prediction probabilities
   - Football Odds Comparison: Comparison of odds across bookmakers

## Available Scripts

- `scripts/api_key_manager.py`: Manage your API token securely
- `scripts/test_api.py`: Test API connection and features
- `scripts/fixtures_collector.py`: Collect fixture data
- `scripts/odds_collector.py`: Collect odds data
- `scripts/value_bets.py`: Find value betting opportunities

## Documentation

For more information on the SportMonks API, refer to:
- [SportMonks API Documentation](https://docs.sportmonks.com/football/)
- [Authentication](https://docs.sportmonks.com/football/welcome/authentication)
- [Making Your First Request](https://docs.sportmonks.com/football/welcome/making-your-first-request)

## License

[Specify your license here]
