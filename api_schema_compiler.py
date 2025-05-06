from sqlalchemy.schema import CreateTable, DropTable, CreateIndex, DropIndex
import requests
import logging
import json

logger = logging.getLogger(__name__)

class APISchemaGenerator:
    """Custom schema generator class for API database."""
    
    def __init__(self, dialect, connection, checkfirst=False, tables=None, **kwargs):
        self.api_url = kwargs.pop('api_url', None)
        self.dialect = dialect
        self.connection = connection
        self.checkfirst = checkfirst
        self.tables = tables
    
    def visit_metadata(self, metadata):
        """Generate schema for all tables in metadata."""
        try:
            # Prepare metadata parameters
            params = {
                'tables': [
                    {
                        'name': table.name,
                        'schema': table.schema,
                        'columns': [
                            {
                                'name': column.name,
                                'type': str(column.type),
                                'nullable': column.nullable,
                                'primary_key': column.primary_key,
                                'foreign_keys': [
                                    {
                                        'target_table': fk.column.table.name,
                                        'target_column': fk.column.name,
                                        'onupdate': fk.onupdate,
                                        'ondelete': fk.ondelete
                                    }
                                    for fk in column.foreign_keys
                                ]
                            }
                            for column in table.columns
                        ],
                        'constraints': [
                            {
                                'name': constraint.name,
                                'type': type(constraint).__name__,
                                'columns': [col.name for col in constraint.columns]
                            }
                            for constraint in table.constraints
                        ],
                        'indexes': [
                            {
                                'name': index.name,
                                'columns': [col.name for col in index.columns],
                                'unique': index.unique
                            }
                            for index in table.indexes
                        ]
                    }
                    for table in metadata.tables.values()
                ]
            }
            
            # Generate schema on API
            response = requests.post(
                f"{self.api_url}/generate_schema",
                json=params
            )
            
            if response.status_code != 200:
                raise Exception(f"Failed to generate schema on API: {response.status_code}")
            
            # Process result
            result = response.json()
            if result.get('error'):
                raise Exception(result['error'])
            
            logger.info("Generated schema")
            return result.get('sql', '')
        except Exception as e:
            logger.error(f"Error generating schema: {e}")
            raise

class APISchemaDropper:
    """Custom schema dropper class for API database."""
    
    def __init__(self, dialect, connection, checkfirst=False, tables=None, **kwargs):
        self.api_url = kwargs.pop('api_url', None)
        self.dialect = dialect
        self.connection = connection
        self.checkfirst = checkfirst
        self.tables = tables
    
    def visit_metadata(self, metadata):
        """Drop schema for all tables in metadata."""
        try:
            # Prepare metadata parameters
            params = {
                'tables': [
                    {
                        'name': table.name,
                        'schema': table.schema
                    }
                    for table in metadata.tables.values()
                ]
            }
            
            # Drop schema on API
            response = requests.post(
                f"{self.api_url}/drop_schema",
                json=params
            )
            
            if response.status_code != 200:
                raise Exception(f"Failed to drop schema on API: {response.status_code}")
            
            # Process result
            result = response.json()
            if result.get('error'):
                raise Exception(result['error'])
            
            logger.info("Dropped schema")
            return result.get('sql', '')
        except Exception as e:
            logger.error(f"Error dropping schema: {e}")
            raise 