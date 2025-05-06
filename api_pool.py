from sqlalchemy.pool import Pool
import requests
import logging
import time

logger = logging.getLogger(__name__)

class APIPool(Pool):
    """Custom connection pool for API database."""
    
    def __init__(self, creator, api_url, **kwargs):
        self.api_url = api_url
        super().__init__(creator, **kwargs)
    
    def _create_connection(self):
        """Create a new connection to the API database."""
        try:
            # Check API availability
            response = requests.get(f"{self.api_url}/health")
            if response.status_code != 200:
                raise Exception(f"API is not available: {response.status_code}")
            
            # Create connection
            connection = self._creator()
            connection.info['api_url'] = self.api_url
            connection.info['created_at'] = time.time()
            
            logger.info("Created new API database connection")
            return connection
        except Exception as e:
            logger.error(f"Error creating API database connection: {e}")
            raise
    
    def _checkout(self):
        """Check out a connection from the pool."""
        try:
            connection = super()._checkout()
            connection.info['checked_out_at'] = time.time()
            logger.info("Checked out API database connection")
            return connection
        except Exception as e:
            logger.error(f"Error checking out API database connection: {e}")
            raise
    
    def _checkin(self, connection):
        """Check in a connection to the pool."""
        try:
            connection.info['checked_in_at'] = time.time()
            super()._checkin(connection)
            logger.info("Checked in API database connection")
        except Exception as e:
            logger.error(f"Error checking in API database connection: {e}")
            raise
    
    def _invalidate(self, connection, exception=None):
        """Invalidate a connection."""
        try:
            # Close connection on API
            response = requests.post(f"{self.api_url}/close")
            if response.status_code != 200:
                logger.warning(f"Failed to close connection on API: {response.status_code}")
            
            super()._invalidate(connection, exception)
            logger.info("Invalidated API database connection")
        except Exception as e:
            logger.error(f"Error invalidating API database connection: {e}")
            raise
    
    def dispose(self):
        """Dispose of the connection pool."""
        try:
            # Close all connections on API
            response = requests.post(f"{self.api_url}/close_all")
            if response.status_code != 200:
                logger.warning(f"Failed to close all connections on API: {response.status_code}")
            
            super().dispose()
            logger.info("Disposed API database connection pool")
        except Exception as e:
            logger.error(f"Error disposing API database connection pool: {e}")
            raise 