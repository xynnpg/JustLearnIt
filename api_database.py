import requests
from sqlalchemy.engine import URL
from sqlalchemy.pool import QueuePool
from sqlalchemy import create_engine
import logging

logger = logging.getLogger(__name__)

class APIDatabaseDriver:
    def __init__(self, api_url):
        self.api_url = api_url
        self._engine = None
        self._session = None

    def get_engine(self):
        if self._engine is None:
            try:
                # Create a custom URL for the API database
                url = URL.create(
                    drivername="sqlite",
                    database=self.api_url,
                    query={
                        "timeout": "30",
                        "check_same_thread": "false"
                    }
                )

                # Create the engine with connection pooling
                self._engine = create_engine(
                    url,
                    poolclass=QueuePool,
                    pool_size=5,
                    max_overflow=10,
                    pool_timeout=30,
                    pool_recycle=1800,
                    connect_args={
                        "timeout": 30,
                        "check_same_thread": False
                    }
                )
                logger.info(f"Created database engine for API: {self.api_url}")
            except Exception as e:
                logger.error(f"Error creating database engine: {e}")
                raise
        return self._engine

    def verify_connection(self):
        try:
            response = requests.get(self.api_url)
            if response.status_code == 200:
                logger.info("API database connection verified")
                return True
            else:
                logger.error(f"Failed to verify API database connection. Status code: {response.status_code}")
                return False
        except Exception as e:
            logger.error(f"Error verifying API database connection: {e}")
            return False

    def get_session(self):
        if self._session is None:
            from sqlalchemy.orm import sessionmaker
            Session = sessionmaker(bind=self.get_engine())
            self._session = Session()
        return self._session

    def close(self):
        if self._session:
            self._session.close()
            self._session = None
        if self._engine:
            self._engine.dispose()
            self._engine = None 