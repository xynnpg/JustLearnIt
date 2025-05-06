from sqlalchemy.orm import Mapper
import requests
import logging

logger = logging.getLogger(__name__)

class APIMapper(Mapper):
    """Custom mapper class for API database."""
    
    def __init__(self, class_, local_table=None, properties=None, primary_key=None, non_primary=False, inherits=None, inherit_condition=None, inherit_foreign_keys=None, extension=None, order_by=False, always_refresh=False, version_id_col=None, version_id_generator=None, polymorphic_on=None, _polymorphic_map=None, polymorphic_identity=None, concrete=False, with_polymorphic=None, polymorphic_load=None, allow_partial_pks=True, batch=True, column_prefix=None, include_properties=None, exclude_properties=None, passive_updates=True, passive_deletes=False, confirm_deleted_rows=True, eager_defaults=False, legacy_is_orphan=False, _compiled_cache_size=100, api_url=None):
        self.api_url = api_url
        super().__init__(
            class_=class_,
            local_table=local_table,
            properties=properties,
            primary_key=primary_key,
            non_primary=non_primary,
            inherits=inherits,
            inherit_condition=inherit_condition,
            inherit_foreign_keys=inherit_foreign_keys,
            extension=extension,
            order_by=order_by,
            always_refresh=always_refresh,
            version_id_col=version_id_col,
            version_id_generator=version_id_generator,
            polymorphic_on=polymorphic_on,
            _polymorphic_map=_polymorphic_map,
            polymorphic_identity=polymorphic_identity,
            concrete=concrete,
            with_polymorphic=with_polymorphic,
            polymorphic_load=polymorphic_load,
            allow_partial_pks=allow_partial_pks,
            batch=batch,
            column_prefix=column_prefix,
            include_properties=include_properties,
            exclude_properties=exclude_properties,
            passive_updates=passive_updates,
            passive_deletes=passive_deletes,
            confirm_deleted_rows=confirm_deleted_rows,
            eager_defaults=eager_defaults,
            legacy_is_orphan=legacy_is_orphan,
            _compiled_cache_size=_compiled_cache_size
        )

    def _configure_properties(self):
        """Configure properties for the mapper."""
        try:
            # Get the table schema from the API
            response = requests.get(f"{self.api_url}/schema/{self.class_.__name__}")
            if response.status_code != 200:
                raise Exception(f"Failed to get table schema from API: {response.status_code}")

            # Process the schema
            schema = response.json()
            if schema.get("error"):
                raise Exception(schema["error"])

            # Configure the properties
            for column in schema.get("columns", []):
                self.add_property(
                    column["name"],
                    column["type"],
                    primary_key=column.get("primary_key", False),
                    nullable=column.get("nullable", True),
                    unique=column.get("unique", False),
                    index=column.get("index", False),
                    default=column.get("default", None)
                )

            logger.info(f"Configured properties for {self.class_.__name__}")
        except Exception as e:
            logger.error(f"Error configuring properties for {self.class_.__name__}: {e}")
            raise

    def _configure_relationships(self):
        """Configure relationships for the mapper."""
        try:
            # Get the relationships from the API
            response = requests.get(f"{self.api_url}/relationships/{self.class_.__name__}")
            if response.status_code != 200:
                raise Exception(f"Failed to get relationships from API: {response.status_code}")

            # Process the relationships
            relationships = response.json()
            if relationships.get("error"):
                raise Exception(relationships["error"])

            # Configure the relationships
            for relationship in relationships.get("relationships", []):
                self.add_relationship(
                    relationship["name"],
                    relationship["target"],
                    relationship["type"],
                    backref=relationship.get("backref", None),
                    cascade=relationship.get("cascade", None),
                    lazy=relationship.get("lazy", "select")
                )

            logger.info(f"Configured relationships for {self.class_.__name__}")
        except Exception as e:
            logger.error(f"Error configuring relationships for {self.class_.__name__}: {e}")
            raise

    def _configure_inheritance(self):
        """Configure inheritance for the mapper."""
        try:
            # Get the inheritance from the API
            response = requests.get(f"{self.api_url}/inheritance/{self.class_.__name__}")
            if response.status_code != 200:
                raise Exception(f"Failed to get inheritance from API: {response.status_code}")

            # Process the inheritance
            inheritance = response.json()
            if inheritance.get("error"):
                raise Exception(inheritance["error"])

            # Configure the inheritance
            if inheritance.get("type"):
                self.add_inheritance(
                    inheritance["parent"],
                    inheritance["type"],
                    polymorphic_on=inheritance.get("polymorphic_on", None),
                    polymorphic_identity=inheritance.get("polymorphic_identity", None)
                )

            logger.info(f"Configured inheritance for {self.class_.__name__}")
        except Exception as e:
            logger.error(f"Error configuring inheritance for {self.class_.__name__}: {e}")
            raise 