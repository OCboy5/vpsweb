"""
VPSWeb Repository System - Base Repository Class

This module provides a base repository class with common database
operations that can be extended by specific repositories.

Features:
- Generic CRUD operations
- Async session management
- Query building utilities
- Error handling and logging
- Pagination support
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Generic, List, Optional, Type, TypeVar, Union

from pydantic import BaseModel
from sqlalchemy import Select, delete, func, select, update
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import DeclarativeBase, selectinload

logger = logging.getLogger(__name__)

# Generic type for model classes
ModelType = TypeVar("ModelType", bound=DeclarativeBase)
# Generic type for Pydantic schemas
CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=BaseModel)


class RepositoryError(Exception):
    """Base exception for repository operations."""

    pass


class NotFoundError(RepositoryError):
    """Raised when a resource is not found."""

    pass


class ValidationError(RepositoryError):
    """Raised when data validation fails."""

    pass


class BaseRepository(Generic[ModelType, CreateSchemaType, UpdateSchemaType]):
    """
    Base repository class providing common CRUD operations.

    This class implements the repository pattern and provides
    generic database operations that can be extended by
    specific repositories.
    """

    def __init__(self, model: Type[ModelType], session: AsyncSession):
        """
        Initialize the repository.

        Args:
            model: SQLAlchemy model class
            session: Async database session
        """
        self.model = model
        self.session = session

    async def create(self, obj_in: CreateSchemaType) -> ModelType:
        """
        Create a new record.

        Args:
            obj_in: Pydantic schema with creation data

        Returns:
            ModelType: Created model instance

        Raises:
            ValidationError: If data validation fails
            RepositoryError: If database operation fails
        """
        try:
            obj_data = obj_in.model_dump(exclude_unset=True)
            db_obj = self.model(**obj_data)
            self.session.add(db_obj)
            await self.session.commit()
            await self.session.refresh(db_obj)

            logger.info(f"Created {self.model.__name__} with id: {db_obj.id}")
            return db_obj

        except SQLAlchemyError as e:
            await self.session.rollback()
            logger.error(f"Failed to create {self.model.__name__}: {e}")
            raise RepositoryError(f"Failed to create {self.model.__name__}: {e}") from e

    async def get(self, id: Any) -> Optional[ModelType]:
        """
        Get a record by ID.

        Args:
            id: Record ID

        Returns:
            Optional[ModelType]: Found record or None

        Raises:
            RepositoryError: If database operation fails
        """
        try:
            stmt = select(self.model).where(self.model.id == id)
            result = await self.session.execute(stmt)
            db_obj = result.scalar_one_or_none()

            if db_obj:
                logger.debug(f"Retrieved {self.model.__name__} with id: {id}")
            else:
                logger.debug(f"{self.model.__name__} with id {id} not found")

            return db_obj

        except SQLAlchemyError as e:
            logger.error(f"Failed to get {self.model.__name__} with id {id}: {e}")
            raise RepositoryError(f"Failed to get {self.model.__name__}: {e}") from e

    async def get_by_field(self, field_name: str, value: Any) -> Optional[ModelType]:
        """
        Get a record by a specific field value.

        Args:
            field_name: Name of the field to query
            value: Value to match

        Returns:
            Optional[ModelType]: Found record or None

        Raises:
            RepositoryError: If database operation fails
        """
        try:
            field = getattr(self.model, field_name)
            stmt = select(self.model).where(field == value)
            result = await self.session.execute(stmt)
            return result.scalar_one_or_none()

        except SQLAlchemyError as e:
            logger.error(f"Failed to get {self.model.__name__} by {field_name}={value}: {e}")
            raise RepositoryError(f"Failed to get {self.model.__name__}: {e}") from e

    async def get_multi(
        self,
        skip: int = 0,
        limit: int = 100,
        order_by: Optional[str] = None,
        order_desc: bool = False,
        **filters: Any
    ) -> List[ModelType]:
        """
        Get multiple records with pagination and filtering.

        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            order_by: Field name to order by
            order_desc: Whether to order descending
            **filters: Additional filter conditions

        Returns:
            List[ModelType]: List of found records

        Raises:
            RepositoryError: If database operation fails
        """
        try:
            stmt = select(self.model)

            # Apply filters
            for field_name, value in filters.items():
                if hasattr(self.model, field_name):
                    field = getattr(self.model, field_name)
                    stmt = stmt.where(field == value)

            # Apply ordering
            if order_by and hasattr(self.model, order_by):
                order_field = getattr(self.model, order_by)
                if order_desc:
                    stmt = stmt.order_by(order_field.desc())
                else:
                    stmt = stmt.order_by(order_field)

            # Apply pagination
            stmt = stmt.offset(skip).limit(limit)

            result = await self.session.execute(stmt)
            db_objs = result.scalars().all()

            logger.debug(f"Retrieved {len(db_objs)} {self.model.__name__} records")
            return db_objs

        except SQLAlchemyError as e:
            logger.error(f"Failed to get multiple {self.model.__name__} records: {e}")
            raise RepositoryError(f"Failed to get {self.model.__name__} records: {e}") from e

    async def update(
        self,
        db_obj: ModelType,
        obj_in: Union[UpdateSchemaType, Dict[str, Any]]
    ) -> ModelType:
        """
        Update an existing record.

        Args:
            db_obj: Existing model instance
            obj_in: Update data (Pydantic schema or dict)

        Returns:
            ModelType: Updated model instance

        Raises:
            NotFoundError: If record doesn't exist
            ValidationError: If data validation fails
            RepositoryError: If database operation fails
        """
        try:
            if isinstance(obj_in, dict):
                update_data = obj_in
            else:
                update_data = obj_in.model_dump(exclude_unset=True)

            for field, value in update_data.items():
                if hasattr(db_obj, field):
                    setattr(db_obj, field, value)

            await self.session.commit()
            await self.session.refresh(db_obj)

            logger.info(f"Updated {self.model.__name__} with id: {db_obj.id}")
            return db_obj

        except SQLAlchemyError as e:
            await self.session.rollback()
            logger.error(f"Failed to update {self.model.__name__} with id {db_obj.id}: {e}")
            raise RepositoryError(f"Failed to update {self.model.__name__}: {e}") from e

    async def update_by_id(self, id: Any, obj_in: Union[UpdateSchemaType, Dict[str, Any]]) -> ModelType:
        """
        Update a record by ID.

        Args:
            id: Record ID
            obj_in: Update data (Pydantic schema or dict)

        Returns:
            ModelType: Updated model instance

        Raises:
            NotFoundError: If record doesn't exist
            RepositoryError: If database operation fails
        """
        db_obj = await self.get(id)
        if not db_obj:
            raise NotFoundError(f"{self.model.__name__} with id {id} not found")

        return await self.update(db_obj, obj_in)

    async def remove(self, db_obj: ModelType) -> ModelType:
        """
        Remove a record.

        Args:
            db_obj: Model instance to remove

        Returns:
            ModelType: Removed model instance

        Raises:
            RepositoryError: If database operation fails
        """
        try:
            await self.session.delete(db_obj)
            await self.session.commit()

            logger.info(f"Removed {self.model.__name__} with id: {db_obj.id}")
            return db_obj

        except SQLAlchemyError as e:
            await self.session.rollback()
            logger.error(f"Failed to remove {self.model.__name__} with id {db_obj.id}: {e}")
            raise RepositoryError(f"Failed to remove {self.model.__name__}: {e}") from e

    async def remove_by_id(self, id: Any) -> ModelType:
        """
        Remove a record by ID.

        Args:
            id: Record ID

        Returns:
            ModelType: Removed model instance

        Raises:
            NotFoundError: If record doesn't exist
            RepositoryError: If database operation fails
        """
        db_obj = await self.get(id)
        if not db_obj:
            raise NotFoundError(f"{self.model.__name__} with id {id} not found")

        return await self.remove(db_obj)

    async def count(self, **filters: Any) -> int:
        """
        Count records with optional filtering.

        Args:
            **filters: Filter conditions

        Returns:
            int: Number of matching records

        Raises:
            RepositoryError: If database operation fails
        """
        try:
            stmt = select(func.count()).select_from(self.model)

            # Apply filters
            for field_name, value in filters.items():
                if hasattr(self.model, field_name):
                    field = getattr(self.model, field_name)
                    stmt = stmt.where(field == value)

            result = await self.session.execute(stmt)
            count = result.scalar()

            logger.debug(f"Counted {count} {self.model.__name__} records")
            return count

        except SQLAlchemyError as e:
            logger.error(f"Failed to count {self.model.__name__} records: {e}")
            raise RepositoryError(f"Failed to count {self.model.__name__} records: {e}") from e

    async def exists(self, id: Any) -> bool:
        """
        Check if a record exists by ID.

        Args:
            id: Record ID

        Returns:
            bool: Whether record exists

        Raises:
            RepositoryError: If database operation fails
        """
        return await self.get(id) is not None

    async def exists_by_field(self, field_name: str, value: Any) -> bool:
        """
        Check if a record exists by field value.

        Args:
            field_name: Name of the field to query
            value: Value to match

        Returns:
            bool: Whether record exists

        Raises:
            RepositoryError: If database operation fails
        """
        return await self.get_by_field(field_name, value) is not None

    async def bulk_create(self, objects: List[CreateSchemaType]) -> List[ModelType]:
        """
        Create multiple records in bulk.

        Args:
            objects: List of Pydantic schemas with creation data

        Returns:
            List[ModelType]: List of created model instances

        Raises:
            ValidationError: If data validation fails
            RepositoryError: If database operation fails
        """
        try:
            db_objs = []
            for obj_in in objects:
                obj_data = obj_in.model_dump(exclude_unset=True)
                db_obj = self.model(**obj_data)
                db_objs.append(db_obj)

            self.session.add_all(db_objs)
            await self.session.commit()

            # Refresh all objects to get their IDs
            for db_obj in db_objs:
                await self.session.refresh(db_obj)

            logger.info(f"Bulk created {len(db_objs)} {self.model.__name__} records")
            return db_objs

        except SQLAlchemyError as e:
            await self.session.rollback()
            logger.error(f"Failed to bulk create {self.model.__name__} records: {e}")
            raise RepositoryError(f"Failed to bulk create {self.model.__name__} records: {e}") from e

    async def bulk_update(
        self,
        updates: List[Dict[str, Any]],
        filter_field: str = "id"
    ) -> int:
        """
        Update multiple records in bulk.

        Args:
            updates: List of update dictionaries
            filter_field: Field name to filter by (default: 'id')

        Returns:
            int: Number of updated records

        Raises:
            RepositoryError: If database operation fails
        """
        try:
            updated_count = 0

            for update_data in updates:
                if filter_field not in update_data:
                    raise ValidationError(f"Update data must contain filter field: {filter_field}")

                filter_value = update_data[filter_field]
                stmt = (
                    update(self.model)
                    .where(getattr(self.model, filter_field) == filter_value)
                    .values(**{k: v for k, v in update_data.items() if k != filter_field})
                )

                result = await self.session.execute(stmt)
                updated_count += result.rowcount

            await self.session.commit()
            logger.info(f"Bulk updated {updated_count} {self.model.__name__} records")
            return updated_count

        except SQLAlchemyError as e:
            await self.session.rollback()
            logger.error(f"Failed to bulk update {self.model.__name__} records: {e}")
            raise RepositoryError(f"Failed to bulk update {self.model.__name__} records: {e}") from e

    async def bulk_delete(self, ids: List[Any]) -> int:
        """
        Delete multiple records in bulk.

        Args:
            ids: List of record IDs to delete

        Returns:
            int: Number of deleted records

        Raises:
            RepositoryError: If database operation fails
        """
        try:
            stmt = delete(self.model).where(self.model.id.in_(ids))
            result = await self.session.execute(stmt)
            deleted_count = result.rowcount

            await self.session.commit()
            logger.info(f"Bulk deleted {deleted_count} {self.model.__name__} records")
            return deleted_count

        except SQLAlchemyError as e:
            await self.session.rollback()
            logger.error(f"Failed to bulk delete {self.model.__name__} records: {e}")
            raise RepositoryError(f"Failed to bulk delete {self.model.__name__} records: {e}") from e

    # Utility methods
    def build_query(self, **filters: Any) -> Select:
        """
        Build a query with filters.

        Args:
            **filters: Filter conditions

        Returns:
            Select: SQLAlchemy Select statement
        """
        stmt = select(self.model)

        for field_name, value in filters.items():
            if hasattr(self.model, field_name):
                field = getattr(self.model, field_name)
                stmt = stmt.where(field == value)

        return stmt

    async def execute_query(self, stmt: Select) -> List[ModelType]:
        """
        Execute a custom query.

        Args:
            stmt: SQLAlchemy Select statement

        Returns:
            List[ModelType]: Query results

        Raises:
            RepositoryError: If database operation fails
        """
        try:
            result = await self.session.execute(stmt)
            return result.scalars().all()

        except SQLAlchemyError as e:
            logger.error(f"Failed to execute query on {self.model.__name__}: {e}")
            raise RepositoryError(f"Failed to execute query: {e}") from e

    async def execute_query_with_relations(
        self, stmt: Select, *relations: str
    ) -> List[ModelType]:
        """
        Execute a query with eager loaded relations.

        Args:
            stmt: SQLAlchemy Select statement
            *relations: Relations to eager load

        Returns:
            List[ModelType]: Query results with loaded relations

        Raises:
            RepositoryError: If database operation fails
        """
        try:
            # Add selectinload options for each relation
            for relation in relations:
                stmt = stmt.options(selectinload(getattr(self.model, relation)))

            result = await self.session.execute(stmt)
            return result.scalars().all()

        except SQLAlchemyError as e:
            logger.error(f"Failed to execute query with relations on {self.model.__name__}: {e}")
            raise RepositoryError(f"Failed to execute query with relations: {e}") from e

    def __repr__(self) -> str:
        return f"<BaseRepository(model={self.model.__name__})>"