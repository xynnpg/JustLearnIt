from sqlalchemy.dialects.sqlite.base import SQLiteDialect
from sqlalchemy import types
from sqlalchemy.engine import default
import requests
import logging

logger = logging.getLogger(__name__)

class APIDialect(SQLiteDialect):
    """Custom dialect for API database."""
    
    name = 'api'
    driver = 'api'
    
    @classmethod
    def get_dialect_cls(cls, url):
        """Get the dialect class for the given URL."""
        return cls
    
    @classmethod
    def import_dbapi(cls):
        """Import the DBAPI module."""
        # For our API dialect, we don't need a traditional DBAPI
        # Instead, we'll return a dummy module that provides the necessary interface
        class DummyDBAPI:
            def __init__(self):
                self.paramstyle = 'qmark'
                self.threadsafety = 1
                self.apilevel = '2.0'
                self.sqlite_version_info = (3, 7, 16)  # Minimum required version
                self.sqlite_version = "3.7.16"
                self.OperationalError = Exception
                self.IntegrityError = Exception
                self.DatabaseError = Exception
                self.ProgrammingError = Exception
            
            def connect(self, *args, **kwargs):
                return DummyConnection()
        
        class DummyConnection:
            def __init__(self):
                self.closed = False
            
            def close(self):
                self.closed = True
            
            def commit(self):
                pass
            
            def rollback(self):
                pass
            
            def cursor(self):
                return DummyCursor()
        
        class DummyCursor:
            def __init__(self):
                self.description = None
                self.rowcount = 0
            
            def execute(self, *args, **kwargs):
                pass
            
            def fetchone(self):
                return None
            
            def fetchall(self):
                return []
            
            def close(self):
                pass
        
        return DummyDBAPI()
    
    def __init__(self, api_url=None, **kwargs):
        self.api_url = api_url
        super().__init__(**kwargs)
    
    def initialize(self, connection):
        """Initialize the dialect with a connection."""
        try:
            # Get database schema from API
            response = requests.get(f"{self.api_url}/schema")
            if response.status_code != 200:
                raise Exception(f"Failed to get database schema from API: {response.status_code}")
            
            # Process schema
            schema = response.json()
            if schema.get('error'):
                raise Exception(schema['error'])
            
            # Configure dialect
            self.supports_native_decimal = schema.get('supports_native_decimal', False)
            self.supports_native_boolean = schema.get('supports_native_boolean', False)
            self.supports_unicode_statements = schema.get('supports_unicode_statements', True)
            self.supports_unicode_binds = schema.get('supports_unicode_binds', True)
            self.supports_multivalues_insert = schema.get('supports_multivalues_insert', True)
            
            logger.info("Initialized API database dialect")
        except Exception as e:
            logger.error(f"Error initializing API database dialect: {e}")
            raise
    
    def get_columns(self, connection, table_name, schema=None, **kwargs):
        """Get column information for a table."""
        try:
            # Get table schema from API
            response = requests.get(f"{self.api_url}/schema/{table_name}")
            if response.status_code != 200:
                raise Exception(f"Failed to get table schema from API: {response.status_code}")
            
            # Process schema
            schema = response.json()
            if schema.get('error'):
                raise Exception(schema['error'])
            
            # Convert columns
            columns = []
            for column in schema['columns']:
                col_type = self._get_column_type(column['type'])
                columns.append({
                    'name': column['name'],
                    'type': col_type,
                    'nullable': column.get('nullable', True),
                    'default': column.get('default'),
                    'primary_key': column.get('primary_key', False),
                    'autoincrement': column.get('autoincrement', False)
                })
            
            logger.info(f"Got columns for table {table_name}")
            return columns
        except Exception as e:
            logger.error(f"Error getting columns for table {table_name}: {e}")
            raise
    
    def get_foreign_keys(self, connection, table_name, schema=None, **kwargs):
        """Get foreign key information for a table."""
        try:
            # Get foreign keys from API
            response = requests.get(f"{self.api_url}/foreign_keys/{table_name}")
            if response.status_code != 200:
                raise Exception(f"Failed to get foreign keys from API: {response.status_code}")
            
            # Process foreign keys
            foreign_keys = response.json()
            if foreign_keys.get('error'):
                raise Exception(foreign_keys['error'])
            
            logger.info(f"Got foreign keys for table {table_name}")
            return foreign_keys
        except Exception as e:
            logger.error(f"Error getting foreign keys for table {table_name}: {e}")
            raise
    
    def get_indexes(self, connection, table_name, schema=None, **kwargs):
        """Get index information for a table."""
        try:
            # Get indexes from API
            response = requests.get(f"{self.api_url}/indexes/{table_name}")
            if response.status_code != 200:
                raise Exception(f"Failed to get indexes from API: {response.status_code}")
            
            # Process indexes
            indexes = response.json()
            if indexes.get('error'):
                raise Exception(indexes['error'])
            
            logger.info(f"Got indexes for table {table_name}")
            return indexes
        except Exception as e:
            logger.error(f"Error getting indexes for table {table_name}: {e}")
            raise
    
    def _get_column_type(self, type_name):
        """Convert API type name to SQLAlchemy type."""
        type_map = {
            'integer': types.Integer,
            'string': types.String,
            'text': types.Text,
            'float': types.Float,
            'boolean': types.Boolean,
            'datetime': types.DateTime,
            'date': types.Date,
            'time': types.Time,
            'binary': types.LargeBinary,
            'json': types.JSON
        }
        return type_map.get(type_name.lower(), types.String)

    def create_connect_args(self, url):
        """Create connection arguments."""
        return [], {}
    
    def do_execute(self, cursor, statement, parameters, context=None):
        """Execute a statement."""
        try:
            # Prepare statement parameters
            stmt_params = {
                'statement': str(statement),
                'parameters': parameters
            }
            
            # Execute statement on API
            response = requests.post(
                f"{url.host}/execute",
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
    
    def do_executemany(self, cursor, statement, parameters, context=None):
        """Execute a statement with multiple parameter sets."""
        try:
            # Prepare statement parameters
            stmt_params = {
                'statement': str(statement),
                'parameters': parameters
            }
            
            # Execute statement on API
            response = requests.post(
                f"{url.host}/executemany",
                json=stmt_params
            )
            
            if response.status_code != 200:
                raise Exception(f"Failed to execute statement on API: {response.status_code}")
            
            # Process result
            result = response.json()
            if result.get('error'):
                raise Exception(result['error'])
            
            logger.info("Executed statement with multiple parameter sets")
            return result.get('result', [])
        except Exception as e:
            logger.error(f"Error executing statement with multiple parameter sets: {e}")
            raise
    
    def do_begin(self, connection):
        """Begin a transaction."""
        try:
            # Begin transaction on API
            response = requests.post(
                f"{url.host}/begin"
            )
            
            if response.status_code != 200:
                raise Exception(f"Failed to begin transaction on API: {response.status_code}")
            
            # Process result
            result = response.json()
            if result.get('error'):
                raise Exception(result['error'])
            
            logger.info("Began transaction")
            return result.get('result', {})
        except Exception as e:
            logger.error(f"Error beginning transaction: {e}")
            raise
    
    def do_commit(self, connection):
        """Commit a transaction."""
        try:
            # Commit transaction on API
            response = requests.post(
                f"{url.host}/commit"
            )
            
            if response.status_code != 200:
                raise Exception(f"Failed to commit transaction on API: {response.status_code}")
            
            # Process result
            result = response.json()
            if result.get('error'):
                raise Exception(result['error'])
            
            logger.info("Committed transaction")
            return result.get('result', {})
        except Exception as e:
            logger.error(f"Error committing transaction: {e}")
            raise
    
    def do_rollback(self, connection):
        """Rollback a transaction."""
        try:
            # Rollback transaction on API
            response = requests.post(
                f"{url.host}/rollback"
            )
            
            if response.status_code != 200:
                raise Exception(f"Failed to rollback transaction on API: {response.status_code}")
            
            # Process result
            result = response.json()
            if result.get('error'):
                raise Exception(result['error'])
            
            logger.info("Rolled back transaction")
            return result.get('result', {})
        except Exception as e:
            logger.error(f"Error rolling back transaction: {e}")
            raise 