import logging
import requests
from typing import Dict, List, Tuple, Any, Optional
import time
import json
from datetime import datetime, timedelta
from pathlib import Path
from config.settings import API_REQUEST_TIMEOUT, API_RETRY_COUNT, API_RETRY_DELAY
from config.leagues import SUPPORTED_LEAGUE_IDS
from api.auth import AuthManager

# Set up logging
logger = logging.getLogger(__name__)

class APICache:
    """Simple cache for API responses"""
    
    def __init__(self, cache_dir: str = "cache", cache_duration: int = 3600):
        """
        Initialize the cache
        
        Args:
            cache_dir: Directory to store cache files
            cache_duration: Cache duration in seconds (default: 1 hour)
        """
        self.cache_dir = Path(cache_dir)
        self.cache_duration = cache_duration
        
        # Create cache directory if it doesn't exist
        self.cache_dir.mkdir(parents=True, exist_ok=True)
    
    def get(self, key: str) -> Optional[Dict]:
        """
        Get data from cache
        
        Args:
            key: Cache key
            
        Returns:
            Cached data or None if not found/expired
        """
        cache_file = self.cache_dir / f"{key}.json"
        
        if not cache_file.exists():
            return None
            
        try:
            # Check if cache is still valid
            modified_time = datetime.fromtimestamp(cache_file.stat().st_mtime)
            if datetime.now() - modified_time > timedelta(seconds=self.cache_duration):
                # Cache expired
                return None
                
            # Read and return cached data
            with open(cache_file, "r") as f:
                return json.load(f)
                
        except Exception as e:
            logger.warning(f"Error reading cache: {str(e)}")
            return None
    
    def set(self, key: str, data: Dict) -> bool:
        """
        Save data to cache
        
        Args:
            key: Cache key
            data: Data to cache
            
        Returns:
            Success flag
        """
        cache_file = self.cache_dir / f"{key}.json"
        
        try:
            # Write data to cache file
            with open(cache_file, "w") as f:
                json.dump(data, f)
            return True
            
        except Exception as e:
            logger.warning(f"Error writing to cache: {str(e)}")
            return False

class RateLimiter:
    """Track and manage API rate limits"""
    
    def __init__(self):
        self.limit = None  # Maximum requests per minute
        self.remaining = None  # Remaining requests
        self.reset_timestamp = None  # When the rate limit resets (Unix timestamp)
        self.last_check = 0  # Last time we checked the rate limit
        
    def update_from_headers(self, headers: Dict):
        """Update rate limit info from response headers"""
        if 'X-RateLimit-Limit' in headers:
            self.limit = int(headers['X-RateLimit-Limit'])
            
        if 'X-RateLimit-Remaining' in headers:
            self.remaining = int(headers['X-RateLimit-Remaining'])
            
        if 'X-RateLimit-Reset' in headers:
            self.reset_timestamp = int(headers['X-RateLimit-Reset'])
            
        self.last_check = time.time()
        
    def should_wait(self, buffer_requests: int = 5) -> Tuple[bool, float]:
        """
        Determine if we should wait before making more requests
        
        Args:
            buffer_requests: Number of requests to keep as buffer
            
        Returns:
            Tuple of (should_wait, seconds_to_wait)
        """
        # If we don't have rate limit info yet, don't wait
        if None in (self.remaining, self.reset_timestamp):
            return False, 0
            
        # If we have plenty of requests remaining, don't wait
        if self.remaining > buffer_requests:
            return False, 0
            
        # Calculate time until reset
        now = time.time()
        seconds_until_reset = max(0, self.reset_timestamp - now)
        
        # If rate limit will reset soon, wait until then
        if seconds_until_reset > 0:
            return True, seconds_until_reset
            
        # If we're out of requests but reset time has passed, 
        # we should make a small request to refresh rate limit info
        if seconds_until_reset <= 0 and now - self.last_check >= 60:
            return False, 0
            
        # Otherwise, wait a bit to be safe (10 seconds)
        return True, 10

class SportMonksAPI:
    """Client for SportMonks API v3"""
    
    def __init__(self, use_cache: bool = True, api_token: str = None):
        self.base_url = "https://api.sportmonks.com/v3/football"
        self.auth = AuthManager(api_token)
        self.headers = self.auth.get_auth_headers()
        self.use_cache = use_cache
        self.cache = APICache() if use_cache else None
        self.rate_limiter = RateLimiter()
        
    def _make_request(self, endpoint: str, params: Dict = None) -> Tuple[Optional[Dict], bool]:
        """
        Make a request to the SportMonks API with retry logic
        
        Args:
            endpoint: API endpoint (without base URL)
            params: Query parameters
            
        Returns:
            Tuple of (response data, success flag)
        """
        if params is None:
            params = {}
            
        url = f"{self.base_url}/{endpoint}"
        
        # Try to get from cache first
        if self.use_cache:
            cache_key = f"{endpoint}_{hash(frozenset(params.items()))}"
            cached_data = self.cache.get(cache_key)
            
            if cached_data:
                logger.debug(f"Using cached data for {endpoint}")
                return cached_data, True
        
        # Check if we should wait due to rate limiting
        should_wait, wait_seconds = self.rate_limiter.should_wait()
        if should_wait:
            logger.warning(
                f"Rate limit approaching: {self.rate_limiter.remaining}/{self.rate_limiter.limit} "
                f"requests remaining. Waiting {wait_seconds:.1f}s until reset."
            )
            time.sleep(wait_seconds)
        
        for attempt in range(API_RETRY_COUNT):
            try:
                logger.debug(f"Making API request to {endpoint}")
                response = requests.get(
                    url, 
                    headers=self.headers, 
                    params=params,
                    timeout=API_REQUEST_TIMEOUT
                )
                
                # Update rate limit information from headers
                self.rate_limiter.update_from_headers(response.headers)
                
                if response.status_code == 200:
                    # Log rate limit info
                    if self.rate_limiter.limit and self.rate_limiter.remaining:
                        logger.debug(
                            f"Rate limit status: {self.rate_limiter.remaining}/{self.rate_limiter.limit} "
                            f"requests remaining"
                        )
                
                # Handle authentication errors specifically
                if response.status_code == 401:
                    logger.error("Authentication failed: Invalid API token")
                    return None, False
                    
                # Handle authorization errors
                if response.status_code == 403:
                    logger.error("Authorization failed: Insufficient permissions for this endpoint")
                    return None, False
                
                # Handle rate limiting (HTTP 429)
                if response.status_code == 429:
                    retry_after = int(response.headers.get('Retry-After', API_RETRY_DELAY))
                    reset_time = datetime.fromtimestamp(self.rate_limiter.reset_timestamp) if self.rate_limiter.reset_timestamp else "unknown time"
                    
                    logger.warning(
                        f"Rate limit exceeded! Waiting for {retry_after}s. "
                        f"Rate limit resets at {reset_time}."
                    )
                    time.sleep(retry_after)
                    continue
                
                # Check for any other HTTP errors
                response.raise_for_status()
                
                data = response.json()
                
                # Check for API-specific error messages
                if "error" in data:
                    error_msg, is_terminal = self.auth.handle_auth_error(data["error"])
                    logger.error(f"API error: {error_msg}")
                    
                    if not is_terminal and attempt < API_RETRY_COUNT - 1:
                        backoff_time = API_RETRY_DELAY * (2 ** attempt)
                        logger.info(f"Retrying in {backoff_time}s...")
                        time.sleep(backoff_time)
                        continue
                    
                    return None, False
                
                # Store in cache if successful and caching is enabled
                if self.use_cache:
                    self.cache.set(cache_key, data)
                    
                return data, True
                
            except requests.exceptions.RequestException as e:
                logger.error(f"Request error (attempt {attempt+1}/{API_RETRY_COUNT}): {str(e)}")
                
                if attempt < API_RETRY_COUNT - 1:
                    # Calculate backoff time (exponential backoff)
                    backoff_time = API_RETRY_DELAY * (2 ** attempt)
                    logger.info(f"Retrying in {backoff_time}s...")
                    time.sleep(backoff_time)
                    continue
                    
                return None, False
                
        # Should never reach here, but just in case
        return None, False
    
    def _paginate_results(self, endpoint: str, params: Dict) -> Tuple[List[Dict], bool]:
        """
        Handle paginated results from the API
        
        Args:
            endpoint: API endpoint
            params: Query parameters
            
        Returns:
            Tuple of (combined results, success flag)
        """
        results = []
        page = 1
        has_more = True
        
        # Best practice: Set explicit per_page with a reasonable value
        if "per_page" not in params:
            params["per_page"] = 50
        
        while has_more:
            # Add page to params
            params["page"] = page
            
            # Before making a request for next page, check if we're approaching rate limits
            should_wait, wait_seconds = self.rate_limiter.should_wait(buffer_requests=10)
            if should_wait:
                logger.info(f"Pausing pagination to avoid rate limits. Waiting {wait_seconds:.1f}s...")
                time.sleep(wait_seconds)
            
            # Make request
            data, success = self._make_request(endpoint, params)
            
            if not success:
                return [], False
                
            # Process data
            if "data" in data:
                results.extend(data["data"])
                
            # Check for pagination
            if "pagination" in data:
                pagination = data["pagination"]
                current_page = pagination.get("current_page", 1)
                last_page = pagination.get("total_pages", 1)
                has_more = current_page < last_page
                
                if has_more:
                    logger.debug(f"Pagination: Processing page {current_page}/{last_page}")
                    page += 1
            else:
                # No pagination info, assume no more pages
                has_more = False
            
            # Always sleep between paginated requests to be kind to the API
            if has_more:
                time.sleep(0.5)  # 500ms pause between requests
                
        return results, True
    
    def get_fixtures_between_dates(self, start_date: str, end_date: str, 
                                  include_predictions: bool = False,
                                  include_odds: bool = False,
                                  league_ids: List[int] = None,
                                  markets: List[str] = None) -> Tuple[List[Dict], bool]:
        """
        Get fixtures between two dates
        
        Args:
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            include_predictions: Whether to include prediction data
            include_odds: Whether to include odds data
            league_ids: Optional list of league IDs to filter by
            markets: Optional list of specific markets to include
            
        Returns:
            Tuple of (fixtures list, success flag)
        """
        # Build includes parameter according to SportMonks API v3
        includes = []
        if include_predictions:
            includes.append("predictions")
        if include_odds:
            includes.append("odds")
            includes.append("odds.bookmaker")
            
            # If specific markets requested, add them to the includes
            if markets:
                for market in markets:
                    includes.append(f"odds.market:{market}")
            
        # Add team and league names
        includes.append("localTeam")
        includes.append("visitorTeam")
        includes.append("league")
        
        # Build filters
        filters = [f"fixtures.from:{start_date}", f"fixtures.to:{end_date}"]
        
        # Add league filter if provided
        if league_ids is None:
            # Use supported leagues by default
            league_ids = SUPPORTED_LEAGUE_IDS
            
        if league_ids:
            # Convert list of IDs to comma-separated string
            leagues_str = ",".join(map(str, league_ids))
            filters.append(f"leagues:{leagues_str}")
        
        # Build params
        params = {
            "filters": ";".join(filters),
            "per_page": 50  # Best practice: Set explicit per_page
        }
        
        # Add includes if any
        if includes:
            params["include"] = ";".join(includes)
        
        # Get fixtures
        fixtures, success = self._paginate_results("fixtures", params)
        
        return fixtures, success
    
    def get_fixture_by_id(self, fixture_id: int, 
                        include_predictions: bool = False,
                        include_odds: bool = False) -> Tuple[Optional[Dict], bool]:
        """
        Get a specific fixture by ID
        
        Args:
            fixture_id: Fixture ID
            include_predictions: Whether to include prediction data
            include_odds: Whether to include odds data
            
        Returns:
            Tuple of (fixture data, success flag)
        """
        # Build includes parameter according to SportMonks API v3
        includes = []
        if include_predictions:
            includes.append("predictions")
        if include_odds:
            includes.append("odds")
            includes.append("odds.bookmaker")
            
        # Add team and league names
        includes.append("localTeam")
        includes.append("visitorTeam")
        includes.append("league")
        
        # Build params
        params = {}
        
        # Add includes if any
        if includes:
            params["include"] = ";".join(includes)
        
        # Get fixture
        data, success = self._make_request(f"fixtures/{fixture_id}", params)
        
        if not success:
            return None, False
            
        # SportMonks API v3 typically wraps the result in a 'data' field
        if "data" in data:
            return data["data"], True
        else:
            return data, True
    
    def get_livescores(self, include_predictions: bool = False,
                     include_odds: bool = False) -> Tuple[List[Dict], bool]:
        """
        Get current livescores
        
        Args:
            include_predictions: Whether to include prediction data
            include_odds: Whether to include odds data
            
        Returns:
            Tuple of (livescores list, success flag)
        """
        # Build includes parameter according to SportMonks API v3
        includes = []
        if include_predictions:
            includes.append("predictions")
        if include_odds:
            includes.append("odds")
            includes.append("odds.bookmaker")
            
        # Add team and league names
        includes.append("localTeam")
        includes.append("visitorTeam")
        includes.append("league")
        
        # Build params - for livescores, we don't want to cache
        params = {
            "per_page": 50
        }
        
        # For livescores, we can filter by our supported leagues
        leagues_str = ",".join(map(str, SUPPORTED_LEAGUE_IDS))
        params["filters"] = f"leagues:{leagues_str}"
        
        # Add includes if any
        if includes:
            params["include"] = ";".join(includes)
        
        # Temporarily disable cache for livescores
        original_cache_setting = self.use_cache
        self.use_cache = False
        
        try:
            # Get livescores
            livescores, success = self._paginate_results("livescores", params)
            return livescores, success
        finally:
            # Restore original cache setting
            self.use_cache = original_cache_setting
    
    def get_leagues(self) -> Tuple[List[Dict], bool]:
        """
        Get all available leagues
        
        Returns:
            Tuple of (leagues list, success flag)
        """
        # Get leagues - use a longer cache time for leagues since they rarely change
        original_cache_duration = None
        if self.cache:
            original_cache_duration = self.cache.cache_duration
            self.cache.cache_duration = 86400  # 24 hours
        
        try:
            # Get leagues with a larger per_page value since we need all leagues
            leagues, success = self._paginate_results("leagues", {"per_page": 100})
            return leagues, success
        finally:
            if self.cache:
                self.cache.cache_duration = original_cache_duration

    def get_pre_match_odds(self, fixture_ids: List[int] = None, 
                         bookmaker_ids: List[int] = None,
                         market_ids: List[int] = None) -> Tuple[List[Dict], bool]:
        """
        Get all pre-match odds with optional filters
        
        Args:
            fixture_ids: Optional list of fixture/match IDs to filter
            bookmaker_ids: Optional list of bookmaker IDs to filter
            market_ids: Optional list of market IDs to filter
            
        Returns:
            Tuple of (odds data list, success flag)
        """
        # Build filters
        filters = []
        
        # Add fixture filter if provided
        if fixture_ids:
            fixtures_str = ",".join(map(str, fixture_ids))
            filters.append(f"fixtures:{fixtures_str}")
            
        # Add bookmaker filter if provided
        if bookmaker_ids:
            bookmakers_str = ",".join(map(str, bookmaker_ids))
            filters.append(f"bookmakers:{bookmakers_str}")
            
        # Add market filter if provided
        if market_ids:
            markets_str = ",".join(map(str, market_ids))
            filters.append(f"markets:{markets_str}")
        
        # Build params
        params = {
            "per_page": 50  # Best practice: Set explicit per_page
        }
        
        # Add filters if any
        if filters:
            params["filters"] = ";".join(filters)
        
        # Get pre-match odds
        odds_data, success = self._paginate_results("odds/pre-match", params)
        
        if not success:
            logger.error("Failed to fetch pre-match odds")
            return [], False
            
        return odds_data, True
    
    def get_pre_match_odds_by_fixture_id(self, fixture_id: int,
                                       bookmaker_ids: List[int] = None,
                                       market_ids: List[int] = None) -> Tuple[List[Dict], bool]:
        """
        Get pre-match odds for a specific fixture/match
        
        Args:
            fixture_id: Fixture/match ID
            bookmaker_ids: Optional list of bookmaker IDs to filter
            market_ids: Optional list of market IDs to filter
            
        Returns:
            Tuple of (odds data list, success flag)
        """
        return self.get_pre_match_odds(
            fixture_ids=[fixture_id],
            bookmaker_ids=bookmaker_ids,
            market_ids=market_ids
        )
    
    def get_odds_by_fixture_and_market(self, fixture_id: int, market_id: int) -> Tuple[List[Dict], bool]:
        """
        Get odds for a specific fixture and market
        
        Args:
            fixture_id: Fixture/match ID
            market_id: Market ID
            
        Returns:
            Tuple of (odds data list, success flag)
        """
        return self.get_pre_match_odds(
            fixture_ids=[fixture_id],
            market_ids=[market_id]
        )

    def get_inplay_odds(self, fixture_ids: List[int] = None, 
                       bookmaker_ids: List[int] = None,
                       market_ids: List[int] = None) -> Tuple[List[Dict], bool]:
        """
        Get all live in-play odds with optional filters
        
        Args:
            fixture_ids: Optional list of fixture/match IDs to filter
            bookmaker_ids: Optional list of bookmaker IDs to filter
            market_ids: Optional list of market IDs to filter
            
        Returns:
            Tuple of (odds data list, success flag)
        """
        # Build filters
        filters = []
        
        # Add fixture filter if provided
        if fixture_ids:
            fixtures_str = ",".join(map(str, fixture_ids))
            filters.append(f"fixtures:{fixtures_str}")
            
        # Add bookmaker filter if provided
        if bookmaker_ids:
            bookmakers_str = ",".join(map(str, bookmaker_ids))
            filters.append(f"bookmakers:{bookmakers_str}")
            
        # Add market filter if provided
        if market_ids:
            markets_str = ",".join(map(str, market_ids))
            filters.append(f"markets:{markets_str}")
        
        # Build params - For live data, always use a smaller page size to get faster responses
        params = {
            "per_page": 30
        }
        
        # Add filters if any
        if filters:
            params["filters"] = ";".join(filters)
        
        # Always disable cache for live data
        original_cache_setting = self.use_cache
        self.use_cache = False
        
        try:
            # Get in-play odds
            odds_data, success = self._paginate_results("odds/inplay", params)
            
            if not success:
                logger.error("Failed to fetch in-play odds")
                return [], False
                
            return odds_data, True
        finally:
            # Restore original cache setting
            self.use_cache = original_cache_setting
    
    def get_inplay_odds_by_fixture_id(self, fixture_id: int,
                                    bookmaker_ids: List[int] = None,
                                    market_ids: List[int] = None) -> Tuple[List[Dict], bool]:
        """
        Get live in-play odds for a specific fixture/match
        
        Args:
            fixture_id: Fixture/match ID
            bookmaker_ids: Optional list of bookmaker IDs to filter
            market_ids: Optional list of market IDs to filter
            
        Returns:
            Tuple of (odds data list, success flag)
        """
        return self.get_inplay_odds(
            fixture_ids=[fixture_id],
            bookmaker_ids=bookmaker_ids,
            market_ids=market_ids
        )
        
    def get_live_matches_with_odds(self, league_ids: List[int] = None) -> Tuple[List[Dict], bool]:
        """
        Get all currently live matches with basic odds information
        
        Args:
            league_ids: Optional list of league IDs to filter by
            
        Returns:
            Tuple of (matches list, success flag)
        """
        # If no specific leagues provided, use all supported leagues
        if league_ids is None:
            league_ids = SUPPORTED_LEAGUE_IDS
        
        # First get all live matches
        live_matches, success = self.get_livescores(include_odds=True)
        
        if not success or not live_matches:
            return [], False
        
        # Filter by league if needed
        if league_ids:
            live_matches = [m for m in live_matches if m.get('league_id') in league_ids]
            
        return live_matches, True

    def get_fixtures_with_odds(self, start_date: str = None, end_date: str = None, 
                             league_ids: List[int] = None,
                             bookmaker_ids: List[int] = None,
                             market_ids: List[int] = None) -> Tuple[List[Dict], bool]:
        """
        Get fixtures that have odds available
        
        Args:
            start_date: Optional start date (YYYY-MM-DD)
            end_date: Optional end date (YYYY-MM-DD)
            league_ids: Optional list of league IDs to filter
            bookmaker_ids: Optional list of bookmaker IDs to filter
            market_ids: Optional list of market IDs to filter
            
        Returns:
            Tuple of (fixtures list, success flag)
        """
        # Build filters
        filters = []
        
        # Add date filters if provided
        if start_date:
            filters.append(f"fixtures.from:{start_date}")
        if end_date:
            filters.append(f"fixtures.to:{end_date}")
            
        # Add league filter if provided
        if league_ids is None:
            # Use supported leagues by default
            league_ids = SUPPORTED_LEAGUE_IDS
            
        if league_ids:
            leagues_str = ",".join(map(str, league_ids))
            filters.append(f"leagues:{leagues_str}")
            
        # Add bookmaker filter if provided
        if bookmaker_ids:
            bookmakers_str = ",".join(map(str, bookmaker_ids))
            filters.append(f"bookmakers:{bookmakers_str}")
            
        # Add market filter if provided
        if market_ids:
            markets_str = ",".join(map(str, market_ids))
            filters.append(f"markets:{markets_str}")
        
        # Build params
        params = {
            "per_page": 50  # Best practice: Set explicit per_page
        }
        
        # Add filters if any
        if filters:
            params["filters"] = ";".join(filters)
            
        # Add includes for team and league details
        params["include"] = "localTeam;visitorTeam;league"
        
        # Get fixtures with odds
        fixtures, success = self._paginate_results("fixtures/hasodds", params)
        
        if not success:
            logger.error("Failed to fetch fixtures with odds")
            return [], False
            
        return fixtures, success

    def get_prediction_probabilities(self, fixture_ids: List[int] = None) -> Tuple[List[Dict], bool]:
        """
        Get prediction probabilities for fixtures
        
        Args:
            fixture_ids: Optional list of fixture IDs to filter
            
        Returns:
            Tuple of (probabilities data list, success flag)
        """
        # Build filters
        filters = []
        
        # Add fixture filter if provided
        if fixture_ids:
            fixtures_str = ",".join(map(str, fixture_ids))
            filters.append(f"fixtures:{fixtures_str}")
        
        # Build params
        params = {
            "per_page": 50
        }
        
        # Add filters if any
        if filters:
            params["filters"] = ";".join(filters)
            
        # Get prediction probabilities
        probabilities, success = self._paginate_results("predictions/probabilities", params)
        
        if not success:
            logger.error("Failed to fetch prediction probabilities")
            return [], False
            
        return probabilities, success
        
    def get_prediction_probabilities_by_fixture(self, fixture_id: int) -> Tuple[Dict, bool]:
        """
        Get prediction probabilities for a specific fixture
        
        Args:
            fixture_id: Fixture ID
            
        Returns:
            Tuple of (probabilities data, success flag)
        """
        # Get probabilities using the filter
        probabilities, success = self.get_prediction_probabilities(fixture_ids=[fixture_id])
        
        if not success or not probabilities:
            return {}, False
            
        # Return the first (and only) result
        return probabilities[0] if probabilities else {}, success
    
    def get_prediction_performance_by_league(self, league_id: int) -> Tuple[Dict, bool]:
        """
        Get prediction performance statistics for a specific league
        
        Args:
            league_id: League ID
            
        Returns:
            Tuple of (performance data, success flag)
        """
        # Make direct request to the performance endpoint
        data, success = self._make_request(f"predictions/performances/leagues/{league_id}")
        
        if not success:
            logger.error(f"Failed to fetch prediction performance for league {league_id}")
            return {}, False
            
        # Return the data field if it exists
        if "data" in data:
            return data["data"], True
        else:
            return data, True

    def get_prediction_performances(self) -> Tuple[List[Dict], bool]:
        """
        Get prediction performances for all leagues
        
        Returns:
            Tuple of (performances list, success flag)
        """
        # Make request to the performances endpoint
        data, success = self._paginate_results("predictions/performances", {})
        
        if not success:
            logger.error("Failed to fetch prediction performances")
            return [], False
            
        return data, True

    def get_value_bets(self, league_ids: List[int] = None, 
                     fixture_ids: List[int] = None,
                     min_probability: float = None,
                     min_odds: float = None,
                     market_id: int = None) -> Tuple[List[Dict], bool]:
        """
        Get value bet recommendations from SportMonks
        
        Args:
            league_ids: Optional list of league IDs to filter
            fixture_ids: Optional list of fixture IDs to filter
            min_probability: Optional minimum probability threshold
            min_odds: Optional minimum odds threshold
            market_id: Optional market ID filter
            
        Returns:
            Tuple of (value bets list, success flag)
        """
        # Build filters
        filters = []
        
        # Add league filter if provided
        if league_ids:
            leagues_str = ",".join(map(str, league_ids))
            filters.append(f"leagues:{leagues_str}")
        
        # Add fixture filter if provided
        if fixture_ids:
            fixtures_str = ",".join(map(str, fixture_ids))
            filters.append(f"fixtures:{fixtures_str}")
            
        # Add market filter if provided
        if market_id:
            filters.append(f"markets:{market_id}")
            
        # Build params
        params = {
            "per_page": 50  # Best practice: Set explicit per_page
        }
        
        # Add filters if any
        if filters:
            params["filters"] = ";".join(filters)
            
        # Add includes to get related data
        params["include"] = "fixture;fixture.league;fixture.participants"
            
        # Get value bets
        value_bets, success = self._paginate_results("predictions/valuebet", params)
        
        if not success:
            logger.error("Failed to fetch value bets")
            return [], False
            
        # Apply additional filtering on the client side if needed
        if min_probability or min_odds:
            filtered_bets = []
            for bet in value_bets:
                if min_probability and bet.get('probability', 0) < min_probability:
                    continue
                if min_odds and bet.get('odds', 0) < min_odds:
                    continue
                filtered_bets.append(bet)
            return filtered_bets, True
            
        return value_bets, True

    def test_connection(self) -> Tuple[bool, str]:
        """
        Make a simple API request to test the connection and authentication
        
        Returns:
            Tuple of (success, message)
        """
        try:
            # Try to fetch a single league - a simple request that should work with any subscription
            data, success = self._make_request("leagues", {"per_page": 1})
            
            if not success:
                return False, "API request failed. Check your API token and connection."
                
            if "data" not in data:
                return False, f"Unexpected API response format. Response: {data}"
                
            # Extract API version and verify it's what we expect
            api_version = data.get("version", "unknown")
            if api_version != "3.0.0" and not api_version.startswith("3."):
                logger.warning(f"API version mismatch. Expected 3.x.x but got {api_version}")
                
            leagues = data.get("data", [])
            if not leagues:
                return True, "API connection successful, but no leagues were returned."
                
            league_name = leagues[0].get("name", "unknown")
            return True, f"API connection successful! Sample league: {league_name}"
            
        except Exception as e:
            logger.error(f"Error testing API connection: {str(e)}")
            return False, f"Error: {str(e)}"
    
    def verify_endpoint_access(self, endpoint: str) -> Tuple[bool, str]:
        """
        Verify if an endpoint is accessible with current API token
        
        Args:
            endpoint: API endpoint to test (e.g., "fixtures", "predictions/probabilities")
            
        Returns:
            Tuple of (success, message)
        """
        try:
            # Make a minimal request to the endpoint
            data, success = self._make_request(endpoint, {"per_page": 1})
            
            if not success:
                return False, f"Cannot access endpoint '{endpoint}'. Check your subscription plan."
                
            return True, f"Successfully accessed endpoint: {endpoint}"
            
        except Exception as e:
            logger.error(f"Error verifying endpoint access: {str(e)}")
            return False, f"Error accessing endpoint '{endpoint}': {str(e)}"

    def get_api_status(self) -> Dict:
        """
        Get comprehensive information about API status and capabilities
        
        Returns:
            Dictionary with API status information
        """
        status = {
            "connection": False,
            "endpoints": {},
            "subscription": {
                "plan": "unknown",
                "includes": [],
                "rate_limit": self.rate_limiter.limit
            },
            "timestamp": datetime.now().isoformat()
        }
        
        # Test basic connection
        success, message = self.test_connection()
        status["connection"] = success
        status["message"] = message
        
        if success:
            # Test common endpoints
            common_endpoints = [
                "leagues", 
                "fixtures", 
                "livescores", 
                "odds/pre-match", 
                "predictions/probabilities",
                "predictions/valuebet"
            ]
            
            for endpoint in common_endpoints:
                success, message = self.verify_endpoint_access(endpoint)
                status["endpoints"][endpoint] = {
                    "accessible": success,
                    "message": message
                }
                
                # Infer subscription details based on accessible endpoints
                if success:
                    if endpoint == "predictions/probabilities":
                        status["subscription"]["includes"].append("predictions")
                    elif endpoint == "odds/pre-match":
                        status["subscription"]["includes"].append("odds")
                    elif endpoint == "predictions/valuebet":
                        status["subscription"]["includes"].append("value_bets")
        
        return status