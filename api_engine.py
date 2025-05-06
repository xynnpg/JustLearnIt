from sqlalchemy import create_engine
from sqlalchemy.pool import NullPool
from api_url import APIURL
from api_dialect import APIDialect
from api_connection import APIConnection
import requests
import logging
import json

logger = logging.getLogger(__name__)

def create_api_engine(api_url=None, **kwargs):
    """Create an engine for the API database."""
    # Create a URL object for the API
    url = APIURL.create(f"api://{api_url}")
    
    # Create the dialect
    dialect = APIDialect()
    
    # Create the engine with the correct URL format
    engine = create_engine(
        f"api://{api_url}",
        dialect=dialect,
        poolclass=NullPool,
        **kwargs
    )
    
    # Store the API URL on the engine
    engine.api_url = api_url
    
    return engine

class APIEngine:
    def __init__(self, api_url=None, **kwargs):
        """Initialize the API engine."""
        self.engine = create_api_engine(api_url, **kwargs)
        self.api_url = api_url

    @property
    def url(self):
        return self.engine.url
    
    @property
    def dialect(self):
        return self.engine.dialect
    
    @property
    def pool(self):
        """Get the connection pool."""
        return self.engine.pool
    
    @property
    def echo(self):
        return self.engine.echo
    
    @property
    def execution_options(self):
        return self.engine.execution_options
    
    def execute(self, statement, *multiparams, **params):
        """Execute a statement on the API database."""
        try:
            # Prepare statement parameters
            stmt_params = {
                'statement': str(statement),
                'params': params,
                'multiparams': multiparams
            }
            
            # Execute statement on API
            response = requests.post(
                f"{self.api_url}/execute",
                json=stmt_params
            )
            
            if response.status_code != 200:
                raise Exception(f"Failed to execute statement on API: {response.status_code}")
            
            # Process result
            result = response.json()
            if result.get('error'):
                raise Exception(result['error'])
            
            logger.info("Executed statement")
            return result.get('result', [])
        except Exception as e:
            logger.error(f"Error executing statement: {e}")
            raise
    
    def _run_ddl_visitor(self, visitorcallable, element, **kwargs):
        """Run a DDL visitor on the given element."""
        try:
            # Get the DDL statements from the visitor
            ddl_statements = visitorcallable(element).collect()
            
            # Execute each DDL statement on the API
            for statement in ddl_statements:
                response = requests.post(
                    f"{self.api_url}/execute",
                    json={
                        "statement": str(statement),
                        "parameters": []
                    }
                )
                
                if response.status_code != 200:
                    raise Exception(f"Failed to execute DDL statement on API: {response.status_code}")
                
                # Process the results
                results = response.json()
                if results.get("error"):
                    raise Exception(results["error"])
                
                logger.info(f"Executed DDL statement: {statement}")
            
            # Commit the changes
            response = requests.post(f"{self.api_url}/commit")
            if response.status_code != 200:
                raise Exception(f"Failed to commit DDL changes on API: {response.status_code}")
            
            logger.info("Committed DDL changes")
            
        except Exception as e:
            logger.error(f"Error running DDL visitor: {e}")
            raise
    
    def connect(self, **kwargs):
        """Create a new connection to the API."""
        return APIConnection(self)
    
    def dispose(self):
        """Dispose of the engine."""
        self.engine.dispose()
    
    def raw_connection(self):
        """Get a raw connection to the API database."""
        try:
            # Get raw connection from API
            response = requests.get(f"{self.api_url}/raw_connection")
            if response.status_code != 200:
                raise Exception(f"Failed to get raw connection from API: {response.status_code}")
            
            # Process connection
            connection = response.json()
            if connection.get('error'):
                raise Exception(connection['error'])
            
            logger.info("Got raw connection to API database")
            return connection
        except Exception as e:
            logger.error(f"Error getting raw connection to API database: {e}")
            raise
    
    def table_names(self, schema=None, connection=None):
        """Get list of table names from the API database."""
        try:
            # Get table names from API
            response = requests.get(f"{self.api_url}/tables")
            if response.status_code != 200:
                raise Exception(f"Failed to get table names from API: {response.status_code}")
            
            # Process table names
            tables = response.json()
            if tables.get('error'):
                raise Exception(tables['error'])
            
            logger.info("Got table names from API database")
            return tables
        except Exception as e:
            logger.error(f"Error getting table names from API database: {e}")
            raise

    def __getattr__(self, name):
        """Delegate all other attributes to the underlying engine."""
        return getattr(self.engine, name)

class APIConnection:
    def __init__(self, engine):
        self.engine = engine
        self._closed = False

    def execute(self, statement, parameters=None):
        return self.engine.execute(statement, parameters)

    def executemany(self, statement, parameters=None):
        return self.engine.executemany(statement, parameters)

    def close(self):
        self._closed = True

    @property
    def closed(self):
        return self._closed 