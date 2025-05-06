from sqlalchemy.engine.base import Connection
import requests
import logging
import json

logger = logging.getLogger(__name__)

class APIConnection(Connection):
    """Custom connection class for API database."""
    
    def __init__(self, engine, connection=None, close_with_result=False, api_url=None):
        self.api_url = api_url
        super().__init__(engine, connection, close_with_result)
    
    def _execute_context(self, dialect, constructor, statement, parameters, *args):
        """Execute a statement within a context."""
        try:
            # Prepare execution parameters
            params = {
                'statement': str(statement),
                'parameters': parameters,
                'args': args
            }
            
            # Execute statement on API
            response = requests.post(
                f"{self.api_url}/execute",
                json=params
            )
            
            if response.status_code != 200:
                raise Exception(f"Failed to execute statement on API: {response.status_code}")
            
            # Process results
            result = response.json()
            if result.get('error'):
                raise Exception(result['error'])
            
            logger.info(f"Executed statement: {statement}")
            return result
        except Exception as e:
            logger.error(f"Error executing statement: {e}")
            raise
    
    def begin(self):
        """Begin a transaction."""
        try:
            # Begin transaction on API
            response = requests.post(f"{self.api_url}/begin")
            if response.status_code != 200:
                raise Exception(f"Failed to begin transaction on API: {response.status_code}")
            
            # Process response
            result = response.json()
            if result.get('error'):
                raise Exception(result['error'])
            
            # Store transaction ID
            self.transaction_id = result.get('transaction_id')
            
            logger.info(f"Began transaction {self.transaction_id}")
            return super().begin()
        except Exception as e:
            logger.error(f"Error beginning transaction: {e}")
            raise
    
    def commit(self):
        """Commit the transaction."""
        try:
            # Commit transaction on API
            response = requests.post(
                f"{self.api_url}/commit",
                json={'transaction_id': getattr(self, 'transaction_id', None)}
            )
            
            if response.status_code != 200:
                raise Exception(f"Failed to commit transaction on API: {response.status_code}")
            
            # Process response
            result = response.json()
            if result.get('error'):
                raise Exception(result['error'])
            
            logger.info(f"Committed transaction {getattr(self, 'transaction_id', None)}")
            return super().commit()
        except Exception as e:
            logger.error(f"Error committing transaction: {e}")
            raise
    
    def rollback(self):
        """Rollback the transaction."""
        try:
            # Rollback transaction on API
            response = requests.post(
                f"{self.api_url}/rollback",
                json={'transaction_id': getattr(self, 'transaction_id', None)}
            )
            
            if response.status_code != 200:
                raise Exception(f"Failed to rollback transaction on API: {response.status_code}")
            
            # Process response
            result = response.json()
            if result.get('error'):
                raise Exception(result['error'])
            
            logger.info(f"Rolled back transaction {getattr(self, 'transaction_id', None)}")
            return super().rollback()
        except Exception as e:
            logger.error(f"Error rolling back transaction: {e}")
            raise
    
    def close(self):
        """Close the connection."""
        try:
            # Close connection on API
            response = requests.post(f"{self.api_url}/close_connection")
            if response.status_code != 200:
                logger.warning(f"Failed to close connection on API: {response.status_code}")
            
            super().close()
            logger.info("Closed connection")
        except Exception as e:
            logger.error(f"Error closing connection: {e}")
            raise 