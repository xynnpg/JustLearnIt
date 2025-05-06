from sqlalchemy.sql.compiler import GenericTypeCompiler
import requests
import logging
import json

logger = logging.getLogger(__name__)

class APITypeCompiler(GenericTypeCompiler):
    """Custom type compiler class for API database."""
    
    def __init__(self, dialect, api_url=None):
        self.api_url = api_url
        super().__init__(dialect)
    
    def visit_BOOLEAN(self, type_, **kwargs):
        """Compile a BOOLEAN type."""
        try:
            # Prepare type parameters
            params = {
                'type': 'BOOLEAN',
                'kwargs': kwargs
            }
            
            # Compile type on API
            response = requests.post(
                f"{self.api_url}/compile_type",
                json=params
            )
            
            if response.status_code != 200:
                raise Exception(f"Failed to compile BOOLEAN type on API: {response.status_code}")
            
            # Process result
            result = response.json()
            if result.get('error'):
                raise Exception(result['error'])
            
            logger.info("Compiled BOOLEAN type")
            return result.get('sql', 'BOOLEAN')
        except Exception as e:
            logger.error(f"Error compiling BOOLEAN type: {e}")
            raise
    
    def visit_INTEGER(self, type_, **kwargs):
        """Compile an INTEGER type."""
        try:
            # Prepare type parameters
            params = {
                'type': 'INTEGER',
                'kwargs': kwargs
            }
            
            # Compile type on API
            response = requests.post(
                f"{self.api_url}/compile_type",
                json=params
            )
            
            if response.status_code != 200:
                raise Exception(f"Failed to compile INTEGER type on API: {response.status_code}")
            
            # Process result
            result = response.json()
            if result.get('error'):
                raise Exception(result['error'])
            
            logger.info("Compiled INTEGER type")
            return result.get('sql', 'INTEGER')
        except Exception as e:
            logger.error(f"Error compiling INTEGER type: {e}")
            raise
    
    def visit_FLOAT(self, type_, **kwargs):
        """Compile a FLOAT type."""
        try:
            # Prepare type parameters
            params = {
                'type': 'FLOAT',
                'kwargs': kwargs
            }
            
            # Compile type on API
            response = requests.post(
                f"{self.api_url}/compile_type",
                json=params
            )
            
            if response.status_code != 200:
                raise Exception(f"Failed to compile FLOAT type on API: {response.status_code}")
            
            # Process result
            result = response.json()
            if result.get('error'):
                raise Exception(result['error'])
            
            logger.info("Compiled FLOAT type")
            return result.get('sql', 'FLOAT')
        except Exception as e:
            logger.error(f"Error compiling FLOAT type: {e}")
            raise
    
    def visit_STRING(self, type_, **kwargs):
        """Compile a STRING type."""
        try:
            # Prepare type parameters
            params = {
                'type': 'STRING',
                'length': getattr(type_, 'length', None),
                'kwargs': kwargs
            }
            
            # Compile type on API
            response = requests.post(
                f"{self.api_url}/compile_type",
                json=params
            )
            
            if response.status_code != 200:
                raise Exception(f"Failed to compile STRING type on API: {response.status_code}")
            
            # Process result
            result = response.json()
            if result.get('error'):
                raise Exception(result['error'])
            
            logger.info("Compiled STRING type")
            return result.get('sql', 'VARCHAR')
        except Exception as e:
            logger.error(f"Error compiling STRING type: {e}")
            raise
    
    def visit_DATETIME(self, type_, **kwargs):
        """Compile a DATETIME type."""
        try:
            # Prepare type parameters
            params = {
                'type': 'DATETIME',
                'kwargs': kwargs
            }
            
            # Compile type on API
            response = requests.post(
                f"{self.api_url}/compile_type",
                json=params
            )
            
            if response.status_code != 200:
                raise Exception(f"Failed to compile DATETIME type on API: {response.status_code}")
            
            # Process result
            result = response.json()
            if result.get('error'):
                raise Exception(result['error'])
            
            logger.info("Compiled DATETIME type")
            return result.get('sql', 'DATETIME')
        except Exception as e:
            logger.error(f"Error compiling DATETIME type: {e}")
            raise 