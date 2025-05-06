from sqlalchemy.sql.compiler import DDLCompiler
import requests
import logging
import json

logger = logging.getLogger(__name__)

class APIDDLCompiler(DDLCompiler):
    """Custom DDL compiler class for API database."""
    
    def __init__(self, dialect, statement, **kwargs):
        self.api_url = kwargs.pop('api_url', None)
        super().__init__(dialect, statement, **kwargs)
    
    def visit_create_table(self, create):
        """Compile a CREATE TABLE statement."""
        try:
            # Prepare create table parameters
            params = {
                'table_name': create.element.name,
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
                    for column in create.element.columns
                ],
                'constraints': [
                    {
                        'name': constraint.name,
                        'type': type(constraint).__name__,
                        'columns': [col.name for col in constraint.columns]
                    }
                    for constraint in create.element.constraints
                ]
            }
            
            # Compile create table on API
            response = requests.post(
                f"{self.api_url}/compile_create_table",
                json=params
            )
            
            if response.status_code != 200:
                raise Exception(f"Failed to compile CREATE TABLE on API: {response.status_code}")
            
            # Process result
            result = response.json()
            if result.get('error'):
                raise Exception(result['error'])
            
            logger.info(f"Compiled CREATE TABLE for {create.element.name}")
            return result.get('sql', '')
        except Exception as e:
            logger.error(f"Error compiling CREATE TABLE: {e}")
            raise
    
    def visit_drop_table(self, drop):
        """Compile a DROP TABLE statement."""
        try:
            # Prepare drop table parameters
            params = {
                'table_name': drop.element.name,
                'if_exists': drop.if_exists
            }
            
            # Compile drop table on API
            response = requests.post(
                f"{self.api_url}/compile_drop_table",
                json=params
            )
            
            if response.status_code != 200:
                raise Exception(f"Failed to compile DROP TABLE on API: {response.status_code}")
            
            # Process result
            result = response.json()
            if result.get('error'):
                raise Exception(result['error'])
            
            logger.info(f"Compiled DROP TABLE for {drop.element.name}")
            return result.get('sql', '')
        except Exception as e:
            logger.error(f"Error compiling DROP TABLE: {e}")
            raise
    
    def visit_create_index(self, create):
        """Compile a CREATE INDEX statement."""
        try:
            # Prepare create index parameters
            params = {
                'index_name': create.element.name,
                'table_name': create.element.table.name,
                'columns': [col.name for col in create.element.columns],
                'unique': create.element.unique,
                'if_not_exists': create.if_not_exists
            }
            
            # Compile create index on API
            response = requests.post(
                f"{self.api_url}/compile_create_index",
                json=params
            )
            
            if response.status_code != 200:
                raise Exception(f"Failed to compile CREATE INDEX on API: {response.status_code}")
            
            # Process result
            result = response.json()
            if result.get('error'):
                raise Exception(result['error'])
            
            logger.info(f"Compiled CREATE INDEX for {create.element.name}")
            return result.get('sql', '')
        except Exception as e:
            logger.error(f"Error compiling CREATE INDEX: {e}")
            raise
    
    def visit_drop_index(self, drop):
        """Compile a DROP INDEX statement."""
        try:
            # Prepare drop index parameters
            params = {
                'index_name': drop.element.name,
                'table_name': drop.element.table.name,
                'if_exists': drop.if_exists
            }
            
            # Compile drop index on API
            response = requests.post(
                f"{self.api_url}/compile_drop_index",
                json=params
            )
            
            if response.status_code != 200:
                raise Exception(f"Failed to compile DROP INDEX on API: {response.status_code}")
            
            # Process result
            result = response.json()
            if result.get('error'):
                raise Exception(result['error'])
            
            logger.info(f"Compiled DROP INDEX for {drop.element.name}")
            return result.get('sql', '')
        except Exception as e:
            logger.error(f"Error compiling DROP INDEX: {e}")
            raise 