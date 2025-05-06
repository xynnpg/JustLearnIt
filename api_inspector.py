from sqlalchemy.engine.reflection import Inspector
import requests
import logging
import json

logger = logging.getLogger(__name__)

class APIInspector(Inspector):
    """Custom inspector class for API database."""
    
    def __init__(self, bind, api_url=None):
        self.api_url = api_url
        super().__init__(bind)
    
    def get_table_names(self, schema=None):
        """Get all table names."""
        try:
            # Get table names from API
            response = requests.get(
                f"{self.api_url}/tables",
                params={'schema': schema}
            )
            
            if response.status_code != 200:
                raise Exception(f"Failed to get table names from API: {response.status_code}")
            
            # Process result
            result = response.json()
            if result.get('error'):
                raise Exception(result['error'])
            
            logger.info("Got table names")
            return result.get('tables', [])
        except Exception as e:
            logger.error(f"Error getting table names: {e}")
            raise
    
    def get_table_options(self, table_name, schema=None):
        """Get table options."""
        try:
            # Get table options from API
            response = requests.get(
                f"{self.api_url}/table_options",
                params={
                    'table_name': table_name,
                    'schema': schema
                }
            )
            
            if response.status_code != 200:
                raise Exception(f"Failed to get table options from API: {response.status_code}")
            
            # Process result
            result = response.json()
            if result.get('error'):
                raise Exception(result['error'])
            
            logger.info(f"Got options for table {table_name}")
            return result.get('options', {})
        except Exception as e:
            logger.error(f"Error getting table options: {e}")
            raise
    
    def get_columns(self, table_name, schema=None):
        """Get all columns for a table."""
        try:
            # Get columns from API
            response = requests.get(
                f"{self.api_url}/columns",
                params={
                    'table_name': table_name,
                    'schema': schema
                }
            )
            
            if response.status_code != 200:
                raise Exception(f"Failed to get columns from API: {response.status_code}")
            
            # Process result
            result = response.json()
            if result.get('error'):
                raise Exception(result['error'])
            
            logger.info(f"Got columns for table {table_name}")
            return result.get('columns', [])
        except Exception as e:
            logger.error(f"Error getting columns: {e}")
            raise
    
    def get_primary_keys(self, table_name, schema=None):
        """Get primary keys for a table."""
        try:
            # Get primary keys from API
            response = requests.get(
                f"{self.api_url}/primary_keys",
                params={
                    'table_name': table_name,
                    'schema': schema
                }
            )
            
            if response.status_code != 200:
                raise Exception(f"Failed to get primary keys from API: {response.status_code}")
            
            # Process result
            result = response.json()
            if result.get('error'):
                raise Exception(result['error'])
            
            logger.info(f"Got primary keys for table {table_name}")
            return result.get('primary_keys', [])
        except Exception as e:
            logger.error(f"Error getting primary keys: {e}")
            raise
    
    def get_foreign_keys(self, table_name, schema=None):
        """Get foreign keys for a table."""
        try:
            # Get foreign keys from API
            response = requests.get(
                f"{self.api_url}/foreign_keys",
                params={
                    'table_name': table_name,
                    'schema': schema
                }
            )
            
            if response.status_code != 200:
                raise Exception(f"Failed to get foreign keys from API: {response.status_code}")
            
            # Process result
            result = response.json()
            if result.get('error'):
                raise Exception(result['error'])
            
            logger.info(f"Got foreign keys for table {table_name}")
            return result.get('foreign_keys', [])
        except Exception as e:
            logger.error(f"Error getting foreign keys: {e}")
            raise
    
    def get_indexes(self, table_name, schema=None):
        """Get indexes for a table."""
        try:
            # Get indexes from API
            response = requests.get(
                f"{self.api_url}/indexes",
                params={
                    'table_name': table_name,
                    'schema': schema
                }
            )
            
            if response.status_code != 200:
                raise Exception(f"Failed to get indexes from API: {response.status_code}")
            
            # Process result
            result = response.json()
            if result.get('error'):
                raise Exception(result['error'])
            
            logger.info(f"Got indexes for table {table_name}")
            return result.get('indexes', [])
        except Exception as e:
            logger.error(f"Error getting indexes: {e}")
            raise 