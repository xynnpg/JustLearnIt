from sqlalchemy.orm.query import Query
import requests
import logging
import json

logger = logging.getLogger(__name__)

class APIQuery(Query):
    """Custom query class for API database."""
    
    def __init__(self, entities, session=None, api_url=None):
        self.api_url = api_url
        super().__init__(entities, session)
    
    def _execute_query(self, query_type, *args, **kwargs):
        """Execute a query on the API database."""
        try:
            # Prepare query parameters
            params = {
                'query_type': query_type,
                'args': args,
                'kwargs': kwargs
            }
            
            # Execute query on API
            response = requests.post(
                f"{self.api_url}/query",
                json=params
            )
            
            if response.status_code != 200:
                raise Exception(f"Failed to execute query on API: {response.status_code}")
            
            # Process results
            result = response.json()
            if result.get('error'):
                raise Exception(result['error'])
            
            logger.info(f"Executed {query_type} query")
            return result.get('data', [])
        except Exception as e:
            logger.error(f"Error executing {query_type} query: {e}")
            raise
    
    def all(self):
        """Get all results from the query."""
        return self._execute_query('all')
    
    def first(self):
        """Get the first result from the query."""
        results = self._execute_query('first')
        return results[0] if results else None
    
    def one(self):
        """Get exactly one result from the query."""
        results = self._execute_query('one')
        if not results:
            raise Exception("No results found")
        if len(results) > 1:
            raise Exception("Multiple results found")
        return results[0]
    
    def count(self):
        """Get the count of results from the query."""
        return self._execute_query('count')
    
    def filter(self, *criterion):
        """Filter the query."""
        self._execute_query('filter', criterion)
        return self
    
    def filter_by(self, **kwargs):
        """Filter the query by keyword arguments."""
        self._execute_query('filter_by', kwargs)
        return self
    
    def order_by(self, *criterion):
        """Order the query results."""
        self._execute_query('order_by', criterion)
        return self
    
    def group_by(self, *criterion):
        """Group the query results."""
        self._execute_query('group_by', criterion)
        return self
    
    def having(self, *criterion):
        """Add having clause to the query."""
        self._execute_query('having', criterion)
        return self
    
    def join(self, *props, **kwargs):
        """Add join clause to the query."""
        self._execute_query('join', props, kwargs)
        return self
    
    def outerjoin(self, *props, **kwargs):
        """Add outer join clause to the query."""
        self._execute_query('outerjoin', props, kwargs)
        return self
    
    def limit(self, limit):
        """Limit the number of results."""
        self._execute_query('limit', limit)
        return self
    
    def offset(self, offset):
        """Add offset to the query."""
        self._execute_query('offset', offset)
        return self
    
    def distinct(self, *criterion):
        """Make the query return distinct results."""
        self._execute_query('distinct', criterion)
        return self
    
    def scalar(self):
        """Return a scalar result."""
        results = self._execute_query('scalar')
        return results[0] if results else None 