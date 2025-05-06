from sqlalchemy.engine.cursor import CursorResult
import requests
import logging
import json

logger = logging.getLogger(__name__)

class APICursor(CursorResult):
    """Custom cursor class for API database."""
    
    def __init__(self, context, api_url=None):
        self.api_url = api_url
        super().__init__(context)
    
    def _fetch_impl(self, size=None):
        """Fetch results from the API database."""
        try:
            # Prepare fetch parameters
            params = {
                'cursor_id': self.cursor_id,
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
            
            logger.info(f"Fetched {size if size else 'all'} results")
            return result.get('data', [])
        except Exception as e:
            logger.error(f"Error fetching results: {e}")
            raise
    
    def fetchall(self):
        """Fetch all results."""
        return self._fetch_impl()
    
    def fetchone(self):
        """Fetch one result."""
        results = self._fetch_impl(size=1)
        return results[0] if results else None
    
    def fetchmany(self, size=None):
        """Fetch many results."""
        return self._fetch_impl(size=size)
    
    def close(self):
        """Close the cursor."""
        try:
            # Close cursor on API
            response = requests.post(
                f"{self.api_url}/close_cursor",
                json={'cursor_id': self.cursor_id}
            )
            
            if response.status_code != 200:
                logger.warning(f"Failed to close cursor on API: {response.status_code}")
            
            super().close()
            logger.info("Closed cursor")
        except Exception as e:
            logger.error(f"Error closing cursor: {e}")
            raise
    
    def keys(self):
        """Get the column keys."""
        try:
            # Get keys from API
            response = requests.get(
                f"{self.api_url}/cursor_keys",
                params={'cursor_id': self.cursor_id}
            )
            
            if response.status_code != 200:
                raise Exception(f"Failed to get cursor keys from API: {response.status_code}")
            
            # Process keys
            result = response.json()
            if result.get('error'):
                raise Exception(result['error'])
            
            logger.info("Got cursor keys")
            return result.get('keys', [])
        except Exception as e:
            logger.error(f"Error getting cursor keys: {e}")
            raise
    
    def rowcount(self):
        """Get the row count."""
        try:
            # Get row count from API
            response = requests.get(
                f"{self.api_url}/cursor_rowcount",
                params={'cursor_id': self.cursor_id}
            )
            
            if response.status_code != 200:
                raise Exception(f"Failed to get cursor row count from API: {response.status_code}")
            
            # Process row count
            result = response.json()
            if result.get('error'):
                raise Exception(result['error'])
            
            logger.info("Got cursor row count")
            return result.get('rowcount', 0)
        except Exception as e:
            logger.error(f"Error getting cursor row count: {e}")
            raise 