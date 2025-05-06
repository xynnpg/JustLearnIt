from sqlalchemy.sql.compiler import SQLCompiler
import requests
import logging
import json

logger = logging.getLogger(__name__)

class APICompiler(SQLCompiler):
    """Custom compiler class for API database."""
    
    def __init__(self, dialect, statement, bind=None, schema_translate_map=None, api_url=None):
        self.api_url = api_url
        super().__init__(dialect, statement, bind, schema_translate_map)
    
    def visit_select(self, select, **kwargs):
        """Compile a SELECT statement."""
        try:
            # Prepare select parameters
            params = {
                'select': str(select),
                'kwargs': kwargs
            }
            
            # Compile select on API
            response = requests.post(
                f"{self.api_url}/compile_select",
                json=params
            )
            
            if response.status_code != 200:
                raise Exception(f"Failed to compile SELECT on API: {response.status_code}")
            
            # Process result
            result = response.json()
            if result.get('error'):
                raise Exception(result['error'])
            
            logger.info("Compiled SELECT statement")
            return result.get('sql', '')
        except Exception as e:
            logger.error(f"Error compiling SELECT: {e}")
            raise
    
    def visit_insert(self, insert, **kwargs):
        """Compile an INSERT statement."""
        try:
            # Prepare insert parameters
            params = {
                'insert': str(insert),
                'kwargs': kwargs
            }
            
            # Compile insert on API
            response = requests.post(
                f"{self.api_url}/compile_insert",
                json=params
            )
            
            if response.status_code != 200:
                raise Exception(f"Failed to compile INSERT on API: {response.status_code}")
            
            # Process result
            result = response.json()
            if result.get('error'):
                raise Exception(result['error'])
            
            logger.info("Compiled INSERT statement")
            return result.get('sql', '')
        except Exception as e:
            logger.error(f"Error compiling INSERT: {e}")
            raise
    
    def visit_update(self, update, **kwargs):
        """Compile an UPDATE statement."""
        try:
            # Prepare update parameters
            params = {
                'update': str(update),
                'kwargs': kwargs
            }
            
            # Compile update on API
            response = requests.post(
                f"{self.api_url}/compile_update",
                json=params
            )
            
            if response.status_code != 200:
                raise Exception(f"Failed to compile UPDATE on API: {response.status_code}")
            
            # Process result
            result = response.json()
            if result.get('error'):
                raise Exception(result['error'])
            
            logger.info("Compiled UPDATE statement")
            return result.get('sql', '')
        except Exception as e:
            logger.error(f"Error compiling UPDATE: {e}")
            raise
    
    def visit_delete(self, delete, **kwargs):
        """Compile a DELETE statement."""
        try:
            # Prepare delete parameters
            params = {
                'delete': str(delete),
                'kwargs': kwargs
            }
            
            # Compile delete on API
            response = requests.post(
                f"{self.api_url}/compile_delete",
                json=params
            )
            
            if response.status_code != 200:
                raise Exception(f"Failed to compile DELETE on API: {response.status_code}")
            
            # Process result
            result = response.json()
            if result.get('error'):
                raise Exception(result['error'])
            
            logger.info("Compiled DELETE statement")
            return result.get('sql', '')
        except Exception as e:
            logger.error(f"Error compiling DELETE: {e}")
            raise
    
    def visit_join(self, join, **kwargs):
        """Compile a JOIN clause."""
        try:
            # Prepare join parameters
            params = {
                'join': str(join),
                'kwargs': kwargs
            }
            
            # Compile join on API
            response = requests.post(
                f"{self.api_url}/compile_join",
                json=params
            )
            
            if response.status_code != 200:
                raise Exception(f"Failed to compile JOIN on API: {response.status_code}")
            
            # Process result
            result = response.json()
            if result.get('error'):
                raise Exception(result['error'])
            
            logger.info("Compiled JOIN clause")
            return result.get('sql', '')
        except Exception as e:
            logger.error(f"Error compiling JOIN: {e}")
            raise 