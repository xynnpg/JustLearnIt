from sqlalchemy.orm import Session as SQLAlchemySession
from sqlalchemy.orm import Query
from api_query import APIQuery
import requests
import logging

logger = logging.getLogger(__name__)

class APISession(SQLAlchemySession):
    def __init__(self, *args, **kwargs):
        self.api_url = kwargs.pop('api_url', None)
        super().__init__(*args, **kwargs)

    def query(self, *entities, **kwargs):
        """Create a new query for this session."""
        return APIQuery(entities, self, api_url=self.api_url)

    def remove(self):
        """Remove the current session."""
        self.expire_all()
        # Don't call close() as it's not needed for API sessions

    def execute(self, statement, parameters=None):
        try:
            # Execute the query on the API
            response = requests.post(
                f"{self.api_url}/execute",
                json={
                    "statement": statement,
                    "parameters": parameters or []
                }
            )
            if response.status_code != 200:
                raise Exception(f"Failed to execute query on API: {response.status_code}")

            # Process the results
            results = response.json()
            if results.get("error"):
                raise Exception(results["error"])

            return results
        except Exception as e:
            logger.error(f"Error executing query on API database: {e}")
            raise

    def commit(self):
        try:
            # Commit the transaction on the API
            response = requests.post(f"{self.api_url}/commit")
            if response.status_code != 200:
                raise Exception(f"Failed to commit transaction on API: {response.status_code}")

            # Process the results
            results = response.json()
            if results.get("error"):
                raise Exception(results["error"])

            logger.info("Committed transaction on API database")
        except Exception as e:
            logger.error(f"Error committing transaction on API database: {e}")
            raise

    def rollback(self):
        try:
            # Rollback the transaction on the API
            response = requests.post(f"{self.api_url}/rollback")
            if response.status_code != 200:
                raise Exception(f"Failed to rollback transaction on API: {response.status_code}")

            # Process the results
            results = response.json()
            if results.get("error"):
                raise Exception(results["error"])

            logger.info("Rolled back transaction on API database")
        except Exception as e:
            logger.error(f"Error rolling back transaction on API database: {e}")
            raise 