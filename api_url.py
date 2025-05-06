from sqlalchemy.engine.url import URL
import requests
import logging
import json

logger = logging.getLogger(__name__)

class APIURL:
    """Custom URL class for API database."""
    
    def __init__(self, url_string):
        if not url_string.startswith('api://'):
            raise Exception("Invalid API URL format")
        
        # Extract API URL
        self._api_url = url_string[6:]
        self._url = URL(
            drivername='api',
            username=None,
            password=None,
            host=self._api_url,
            port=None,
            database=None,
            query=None
        )
    
    @property
    def api_url(self):
        return self._api_url
    
    @property
    def url(self):
        return self._url
    
    @classmethod
    def create(cls, url_string):
        """Create a new URL instance from a string."""
        try:
            url = cls(url_string)
            logger.info(f"Created API URL: {url}")
            return url
        except Exception as e:
            logger.error(f"Error creating API URL: {e}")
            raise
    
    def get_backend_url(self):
        """Get the backend URL for the API database."""
        try:
            # Get backend URL from API
            response = requests.get(
                f"{self.api_url}/backend_url"
            )
            
            if response.status_code != 200:
                raise Exception(f"Failed to get backend URL from API: {response.status_code}")
            
            # Process result
            result = response.json()
            if result.get('error'):
                raise Exception(result['error'])
            
            logger.info("Got backend URL")
            return result.get('url', '')
        except Exception as e:
            logger.error(f"Error getting backend URL: {e}")
            raise
    
    def get_dialect_name(self):
        """Get the dialect name for the API database."""
        try:
            # Get dialect name from API
            response = requests.get(
                f"{self.api_url}/dialect"
            )
            
            if response.status_code != 200:
                raise Exception(f"Failed to get dialect name from API: {response.status_code}")
            
            # Process result
            result = response.json()
            if result.get('error'):
                raise Exception(result['error'])
            
            logger.info("Got dialect name")
            return result.get('dialect', 'api')
        except Exception as e:
            logger.error(f"Error getting dialect name: {e}")
            raise
    
    def get_driver_name(self):
        """Get the driver name for the API database."""
        try:
            # Get driver name from API
            response = requests.get(
                f"{self.api_url}/driver"
            )
            
            if response.status_code != 200:
                raise Exception(f"Failed to get driver name from API: {response.status_code}")
            
            # Process result
            result = response.json()
            if result.get('error'):
                raise Exception(result['error'])
            
            logger.info("Got driver name")
            return result.get('driver', 'api')
        except Exception as e:
            logger.error(f"Error getting driver name: {e}")
            raise
    
    def translate_connect_args(self, connect_args):
        """Translate connection arguments for the API database."""
        try:
            # Translate connect args on API
            response = requests.post(
                f"{self.api_url}/translate_connect_args",
                json=connect_args
            )
            
            if response.status_code != 200:
                raise Exception(f"Failed to translate connect args on API: {response.status_code}")
            
            # Process result
            result = response.json()
            if result.get('error'):
                raise Exception(result['error'])
            
            logger.info("Translated connect args")
            return result.get('args', {})
        except Exception as e:
            logger.error(f"Error translating connect args: {e}")
            raise 