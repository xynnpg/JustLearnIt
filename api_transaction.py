from sqlalchemy.engine.base import Transaction
import requests
import logging
import json

logger = logging.getLogger(__name__)

class APITransaction(Transaction):
    """Custom transaction class for API database."""
    
    def __init__(self, connection, parent=None, api_url=None):
        self.api_url = api_url
        super().__init__(connection, parent)
    
    def _begin(self):
        """Begin a new transaction."""
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
        except Exception as e:
            logger.error(f"Error beginning transaction: {e}")
            raise
    
    def _prepare(self):
        """Prepare the transaction for two-phase commit."""
        try:
            # Prepare transaction on API
            response = requests.post(
                f"{self.api_url}/prepare",
                json={'transaction_id': self.transaction_id}
            )
            
            if response.status_code != 200:
                raise Exception(f"Failed to prepare transaction on API: {response.status_code}")
            
            # Process response
            result = response.json()
            if result.get('error'):
                raise Exception(result['error'])
            
            logger.info(f"Prepared transaction {self.transaction_id}")
        except Exception as e:
            logger.error(f"Error preparing transaction: {e}")
            raise
    
    def _commit(self):
        """Commit the transaction."""
        try:
            # Commit transaction on API
            response = requests.post(
                f"{self.api_url}/commit",
                json={'transaction_id': self.transaction_id}
            )
            
            if response.status_code != 200:
                raise Exception(f"Failed to commit transaction on API: {response.status_code}")
            
            # Process response
            result = response.json()
            if result.get('error'):
                raise Exception(result['error'])
            
            logger.info(f"Committed transaction {self.transaction_id}")
        except Exception as e:
            logger.error(f"Error committing transaction: {e}")
            raise
    
    def _rollback(self):
        """Rollback the transaction."""
        try:
            # Rollback transaction on API
            response = requests.post(
                f"{self.api_url}/rollback",
                json={'transaction_id': self.transaction_id}
            )
            
            if response.status_code != 200:
                raise Exception(f"Failed to rollback transaction on API: {response.status_code}")
            
            # Process response
            result = response.json()
            if result.get('error'):
                raise Exception(result['error'])
            
            logger.info(f"Rolled back transaction {self.transaction_id}")
        except Exception as e:
            logger.error(f"Error rolling back transaction: {e}")
            raise
    
    def close(self):
        """Close the transaction."""
        try:
            # Close transaction on API
            response = requests.post(
                f"{self.api_url}/close_transaction",
                json={'transaction_id': self.transaction_id}
            )
            
            if response.status_code != 200:
                logger.warning(f"Failed to close transaction on API: {response.status_code}")
            
            super().close()
            logger.info(f"Closed transaction {self.transaction_id}")
        except Exception as e:
            logger.error(f"Error closing transaction: {e}")
            raise 