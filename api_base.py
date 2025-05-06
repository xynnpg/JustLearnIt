from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Table, Column, ForeignKey, Index, MetaData
import requests
import logging

logger = logging.getLogger(__name__)

# Create metadata and base class
metadata = MetaData()
Base = declarative_base(metadata=metadata)

class APIDeclarativeBase(Base):
    """Custom declarative base class for API database."""
    
    __abstract__ = True  # This makes it a non-mapped class
    
    def __init__(self, api_url, **kwargs):
        self.api_url = api_url
        super().__init__(**kwargs)

    @classmethod
    def __init_subclass__(cls, **kwargs):
        """Initialize a subclass of the declarative base."""
        try:
            # Get the table schema from the API
            response = requests.get(f"{cls.api_url}/schema/{cls.__name__}")
            if response.status_code != 200:
                raise Exception(f"Failed to get table schema from API: {response.status_code}")

            # Process the schema
            schema = response.json()
            if schema.get("error"):
                raise Exception(schema["error"])

            # Set the table name
            cls.__tablename__ = schema["name"]

            # Configure the table
            cls.__table__ = Table(
                schema["name"],
                cls.metadata,
                *[Column(**column) for column in schema["columns"]],
                *[ForeignKey(**fk) for fk in schema.get("foreign_keys", [])],
                *[Index(**idx) for idx in schema.get("indexes", [])]
            )

            # Configure the relationships
            for relationship in schema.get("relationships", []):
                setattr(
                    cls,
                    relationship["name"],
                    relationship(
                        relationship["target"],
                        relationship["type"],
                        backref=relationship.get("backref", None),
                        cascade=relationship.get("cascade", None),
                        lazy=relationship.get("lazy", "select")
                    )
                )

            # Configure the inheritance
            if schema.get("inheritance"):
                inheritance = schema["inheritance"]
                if inheritance["type"] in ["single", "joined", "concrete"]:
                    cls.__mapper_args__ = {
                        "polymorphic_on": inheritance.get("polymorphic_on"),
                        "polymorphic_identity": inheritance.get("polymorphic_identity")
                    }

            logger.info(f"Configured model {cls.__name__}")
        except Exception as e:
            logger.error(f"Error configuring model {cls.__name__}: {e}")
            raise

    def __repr__(self):
        """Return a string representation of the model."""
        return f"<{self.__class__.__name__}({', '.join(f'{k}={v}' for k, v in self.__dict__.items() if not k.startswith('_'))})>" 