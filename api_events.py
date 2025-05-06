from sqlalchemy import event
import requests
import logging
import tempfile
import os

logger = logging.getLogger(__name__)

def setup_api_events(engine, api_url):
    """Setup event listeners for API database operations."""
    
    @event.listens_for(engine, 'connect')
    def connect(dbapi_connection, connection_record):
        """Handle database connection."""
        try:
            # Get database content from API
            response = requests.get(f"{api_url}/database")
            if response.status_code != 200:
                raise Exception(f"Failed to get database content from API: {response.status_code}")
            
            # Create temporary file for database
            temp_db = tempfile.NamedTemporaryFile(delete=False)
            temp_db.write(response.content)
            temp_db.close()
            
            # Attach temporary database to connection
            dbapi_connection.execute(f"ATTACH DATABASE '{temp_db.name}' AS api_db")
            connection_record.info['temp_db'] = temp_db.name
            
            logger.info("Connected to API database")
        except Exception as e:
            logger.error(f"Error connecting to API database: {e}")
            raise

    @event.listens_for(engine, 'close')
    def close(dbapi_connection, connection_record):
        """Handle database disconnection."""
        try:
            # Detach temporary database
            if 'temp_db' in connection_record.info:
                dbapi_connection.execute("DETACH DATABASE api_db")
                os.unlink(connection_record.info['temp_db'])
                logger.info("Disconnected from API database")
        except Exception as e:
            logger.error(f"Error disconnecting from API database: {e}")
            raise

    @event.listens_for(engine, 'before_cursor_execute')
    def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        """Handle query execution."""
        try:
            # Execute query on API
            response = requests.post(
                f"{api_url}/execute",
                json={
                    'statement': statement,
                    'parameters': parameters,
                    'executemany': executemany
                }
            )
            
            if response.status_code != 200:
                raise Exception(f"Failed to execute query on API: {response.status_code}")
            
            # Process results
            result = response.json()
            if result.get('error'):
                raise Exception(result['error'])
            
            # Update cursor with results
            cursor.description = result.get('description')
            cursor.rowcount = result.get('rowcount', 0)
            cursor._rows = result.get('rows', [])
            
            logger.info(f"Executed query: {statement}")
        except Exception as e:
            logger.error(f"Error executing query: {e}")
            raise

    @event.listens_for(engine, 'after_cursor_execute')
    def after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        """Handle post-query execution."""
        try:
            # Commit transaction on API
            response = requests.post(f"{api_url}/commit")
            if response.status_code != 200:
                raise Exception(f"Failed to commit transaction on API: {response.status_code}")
            
            logger.info("Committed transaction")
        except Exception as e:
            logger.error(f"Error committing transaction: {e}")
            raise 