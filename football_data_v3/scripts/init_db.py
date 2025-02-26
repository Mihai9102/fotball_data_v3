import logging
import argparse
import sys
sys.path.append('/Users/mihaivictor/CascadeProjects/football_data/football_data_v3')

from database.models import create_tables

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    """Initialize the database schema"""
    logger.info("Starting database initialization...")
    
    try:
        create_tables()
        logger.info("Database schema created successfully")
    except Exception as e:
        logger.error(f"Error initializing database: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Initialize the football data database")
    parser.add_argument("--force", action="store_true", help="Force re-creation of tables (WARNING: This will delete all existing data)")
    
    args = parser.parse_args()
    
    # TODO: Implement force flag to drop and recreate tables if needed
    main()
