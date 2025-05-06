from sqlalchemy.engine.result import Result
import requests
import logging
import json

logger = logging.getLogger(__name__)

class APIResultProxy(Result):
    """Custom result proxy for API database."""
    
    def __init__(self, context, api_url=None):
        self.api_url = api_url
        super().__init__(context)
    
    def _fetch_results(self, fetch_type, size=None):
        """Fetch results from the API database."""
        try:
            # Prepare fetch parameters
            params = {
                'fetch_type': fetch_type,
                'size': size
            }
            
            # Fetch results from API
            response = requests.post(
                f"{self.api_url}/fetch",
                json=params
            )
            
            if response.status_code != 200:
                raise Exception(f"Failed to fetch results from API: {response.status_code}")
            
            # Process results
            result = response.json()
            if result.get('error'):
                raise Exception(result['error'])
            
            logger.info(f"Fetched {fetch_type} results")
            return result.get('data', [])
        except Exception as e:
            logger.error(f"Error fetching {fetch_type} results: {e}")
            raise
    
    def fetchall(self):
        """Fetch all results."""
        return self._fetch_results('all')
    
    def fetchone(self):
        """Fetch one result."""
        results = self._fetch_results('one')
        return results[0] if results else None
    
    def fetchmany(self, size=None):
        """Fetch many results."""
        return self._fetch_results('many', size)
    
    def first(self):
        """Get the first result."""
        results = self._fetch_results('first')
        return results[0] if results else None
    
    def scalar(self):
        """Get a scalar result."""
        results = self._fetch_results('scalar')
        return results[0] if results else None
    
    def keys(self):
        """Get the column keys."""
        try:
            # Get keys from API
            response = requests.get(f"{self.api_url}/keys")
            if response.status_code != 200:
                raise Exception(f"Failed to get keys from API: {response.status_code}")
            
            # Process keys
            result = response.json()
            if result.get('error'):
                raise Exception(result['error'])
            
            logger.info("Got column keys")
            return result.get('keys', [])
        except Exception as e:
            logger.error(f"Error getting column keys: {e}")
            raise
    
    def close(self):
        """Close the result proxy."""
        try:
            # Close result proxy on API
            response = requests.post(f"{self.api_url}/close_result")
            if response.status_code != 200:
                logger.warning(f"Failed to close result proxy on API: {response.status_code}")
            
            super().close()
            logger.info("Closed result proxy")
        except Exception as e:
            logger.error(f"Error closing result proxy: {e}")
            raise 