from sqlalchemy.dialects.sqlite.base import SQLiteDialect
from sqlalchemy.engine import URL
import requests
import logging

logger = logging.getLogger(__name__)

class APISQLiteDialect(SQLiteDialect):
    def __init__(self, api_url, **kwargs):
        super().__init__(**kwargs)
        self.api_url = api_url
        self._connection = None

    def create_connect_args(self, url):
        try:
            # Get the database content from the API
            response = requests.get(self.api_url)
            if response.status_code != 200:
                raise Exception(f"Failed to get database from API: {response.status_code}")

            # Create a temporary file to store the database
            import tempfile
            import os
            fd, path = tempfile.mkstemp(suffix='.db')
            os.close(fd)

            # Write the database content to the temporary file
            with open(path, 'wb') as f:
                f.write(response.content)

            # Return the connection arguments
            return [f"file:{path}?mode=ro", {}]
        except Exception as e:
            logger.error(f"Error creating connection to API database: {e}")
            raise

    def do_execute(self, cursor, statement, parameters, context=None):
        try:
            # Execute the query on the API
            response = requests.post(
                f"{self.api_url}/execute",
                json={
                    "statement": statement,
                    "parameters": parameters
                }
            )
            if response.status_code != 200:
                raise Exception(f"Failed to execute query on API: {response.status_code}")

            # Process the results
            results = response.json()
            if results.get("error"):
                raise Exception(results["error"])

            # Set the results on the cursor
            cursor.description = results.get("description", [])
            cursor.rowcount = results.get("rowcount", 0)
            cursor._rows = results.get("rows", [])
        except Exception as e:
            logger.error(f"Error executing query on API database: {e}")
            raise

    def do_executemany(self, cursor, statement, parameters, context=None):
        try:
            # Execute the batch query on the API
            response = requests.post(
                f"{self.api_url}/executemany",
                json={
                    "statement": statement,
                    "parameters": parameters
                }
            )
            if response.status_code != 200:
                raise Exception(f"Failed to execute batch query on API: {response.status_code}")

            # Process the results
            results = response.json()
            if results.get("error"):
                raise Exception(results["error"])

            # Set the results on the cursor
            cursor.description = results.get("description", [])
            cursor.rowcount = results.get("rowcount", 0)
            cursor._rows = results.get("rows", [])
        except Exception as e:
            logger.error(f"Error executing batch query on API database: {e}")
            raise 