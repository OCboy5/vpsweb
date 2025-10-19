"""
AI Log Repository Implementation

This module provides the AI log repository with comprehensive CRUD operations,
performance tracking, and specialized queries for AI translation operations.

Features:
- CRUD operations for AI logs
- Performance metrics tracking
- Cost analysis
- Provider-specific analytics
- Processing status monitoring
"""

from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, timezone, timedelta
from sqlalchemy import select, func, and_, or_, desc, asc, cast, Float
from sqlalchemy.ext.asyncio import AsyncSession

from .base import BaseRepository, NotFoundError, ValidationError
from .models import AiLog, Poem, Translation
from .schemas import AiLogCreate, AiLogUpdate, AiLogStatus, WorkflowMode
from .exceptions import (
    DatabaseException, ResourceNotFoundException,
    ErrorCode
)
from ..utils.logger import get_structured_logger


class AiLogRepository(BaseRepository[AiLog, AiLogCreate, AiLogUpdate]):
    """
    Repository for AI log operations with specialized analytics functionality.
    """

    def __init__(self, session: AsyncSession):
        """
        Initialize AI log repository.

        Args:
            session: Async database session
        """
        super().__init__(AiLog, session)
        self.logger = get_structured_logger()

    async def create(self, obj_in: AiLogCreate, created_by: Optional[str] = None) -> AiLog:
        """
        Create a new AI log entry.

        Args:
            obj_in: AI log creation data
            created_by: User who created the log

        Returns:
            Created AI log

        Raises:
            ValidationError: If validation fails
            DatabaseException: If database operation fails
        """
        # Verify poem exists
        poem_stmt = select(Poem).where(Poem.id == obj_in.poem_id)
        poem_result = await self.session.execute(poem_stmt)
        poem = poem_result.scalar_one_or_none()

        if not poem:
            raise ResourceNotFoundException(
                f"Poem not found: {obj_in.poem_id}",
                resource_id=obj_in.poem_id
            )

        # Verify translation exists if provided
        if obj_in.translation_id:
            translation_stmt = select(Translation).where(Translation.id == obj_in.translation_id)
            translation_result = await self.session.execute(translation_stmt)
            translation = translation_result.scalar_one_or_none()

            if not translation:
                raise ResourceNotFoundException(
                    f"Translation not found: {obj_in.translation_id}",
                    resource_id=obj_in.translation_id
                )

        try:
            # Create AI log with additional validation
            log_data = obj_in.dict()

            # Add system fields
            log_data['created_by'] = created_by
            log_data['updated_by'] = created_by

            db_log = self.model(**log_data)
            self.session.add(db_log)
            await self.session.commit()
            await self.session.refresh(db_log)

            self.logger.info(
                "AI log created",
                log_id=db_log.id,
                poem_id=obj_in.poem_id,
                translation_id=obj_in.translation_id,
                provider=obj_in.provider,
                model=obj_in.model_name,
                workflow_mode=obj_in.workflow_mode,
                status=obj_in.status,
                created_by=created_by
            )

            return db_log

        except Exception as e:
            await self.session.rollback()
            self.logger.error(
                "Failed to create AI log",
                error=str(e),
                poem_id=obj_in.poem_id,
                provider=obj_in.provider
            )
            raise DatabaseException(f"Failed to create AI log: {str(e)}")

    async def get_by_poem(self, poem_id: str, include_completed: bool = True) -> List[AiLog]:
        """
        Get AI logs for a specific poem.

        Args:
            poem_id: Poem ID
            include_completed: Whether to include completed logs

        Returns:
            List of AI logs
        """
        try:
            conditions = [self.model.poem_id == poem_id]

            if not include_completed:
                conditions.append(self.model.status != AiLogStatus.COMPLETED)

            stmt = select(self.model).where(and_(*conditions)).order_by(
                desc(self.model.created_at)
            )

            result = await self.session.execute(stmt)
            logs = result.scalars().all()

            return list(logs)

        except Exception as e:
            self.logger.error(
                "Failed to get AI logs by poem",
                error=str(e),
                poem_id=poem_id
            )
            raise DatabaseException(f"Failed to get AI logs: {str(e)}")

    async def get_by_status(
        self,
        status: AiLogStatus,
        limit: int = 50,
        offset: int = 0
    ) -> Tuple[List[AiLog], int]:
        """
        Get AI logs by status.

        Args:
            status: AI log status
            limit: Maximum number of results
            offset: Number of results to skip

        Returns:
            Tuple of (logs, total count)
        """
        try:
            conditions = [self.model.status == status]

            # Query and count
            stmt = select(self.model).where(and_(*conditions)).order_by(
                desc(self.model.created_at)
            ).offset(offset).limit(limit)

            count_stmt = select(func.count()).select_from(self.model).where(and_(*conditions))

            # Execute queries
            result = await self.session.execute(stmt)
            logs = result.scalars().all()

            count_result = await self.session.execute(count_stmt)
            total = count_result.scalar()

            return list(logs), total

        except Exception as e:
            self.logger.error(
                "Failed to get AI logs by status",
                error=str(e),
                status=status
            )
            raise DatabaseException(f"Failed to get AI logs: {str(e)}")

    async def get_by_provider(
        self,
        provider: str,
        days: int = 30,
        limit: int = 50,
        offset: int = 0
    ) -> Tuple[List[AiLog], int]:
        """
        Get AI logs by provider.

        Args:
            provider: AI provider name
            days: Number of days to look back
            limit: Maximum number of results
            offset: Number of results to skip

        Returns:
            Tuple of (logs, total count)
        """
        try:
            # Calculate date threshold
            threshold_date = datetime.now(timezone.utc) - timedelta(days=days)

            conditions = [
                self.model.provider == provider,
                self.model.created_at >= threshold_date
            ]

            # Query and count
            stmt = select(self.model).where(and_(*conditions)).order_by(
                desc(self.model.created_at)
            ).offset(offset).limit(limit)

            count_stmt = select(func.count()).select_from(self.model).where(and_(*conditions))

            # Execute queries
            result = await self.session.execute(stmt)
            logs = result.scalars().all()

            count_result = await self.session.execute(count_stmt)
            total = count_result.scalar()

            return list(logs), total

        except Exception as e:
            self.logger.error(
                "Failed to get AI logs by provider",
                error=str(e),
                provider=provider
            )
            raise DatabaseException(f"Failed to get AI logs: {str(e)}")

    async def update_status(
        self,
        log_id: str,
        status: AiLogStatus,
        error_message: Optional[str] = None,
        translation_id: Optional[str] = None,
        updated_by: Optional[str] = None
    ) -> AiLog:
        """
        Update AI log status and related fields.

        Args:
            log_id: AI log ID
            status: New status
            error_message: Error message if failed
            translation_id: Resulting translation ID
            updated_by: User who made the update

        Returns:
            Updated AI log

        Raises:
            ResourceNotFoundException: If log not found
        """
        try:
            # Get existing log
            existing = await self.get(log_id)
            if not existing:
                raise ResourceNotFoundException(
                    f"AI log not found: {log_id}",
                    resource_id=log_id
                )

            # Update fields
            update_data = {
                'status': status,
                'updated_by': updated_by,
                'updated_at': datetime.now(timezone.utc)
            }

            if error_message:
                update_data['error_message'] = error_message

            if translation_id:
                update_data['translation_id'] = translation_id

            # Apply updates
            for field, value in update_data.items():
                if hasattr(existing, field):
                    setattr(existing, field, value)

            await self.session.commit()
            await self.session.refresh(existing)

            self.logger.info(
                "AI log status updated",
                log_id=log_id,
                old_status=existing.status,
                new_status=status,
                updated_by=updated_by
            )

            return existing

        except ResourceNotFoundException:
            raise
        except Exception as e:
            await self.session.rollback()
            self.logger.error(
                "Failed to update AI log status",
                error=str(e),
                log_id=log_id
            )
            raise DatabaseException(f"Failed to update AI log status: {str(e)}")

    async def get_performance_metrics(
        self,
        days: int = 30,
        provider: Optional[str] = None,
        model_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get performance metrics for AI operations.

        Args:
            days: Number of days to analyze
            provider: Optional provider filter
            model_name: Optional model filter

        Returns:
            Performance metrics dictionary
        """
        try:
            # Calculate date threshold
            threshold_date = datetime.now(timezone.utc) - timedelta(days=days)

            # Build base query conditions
            conditions = [
                self.model.created_at >= threshold_date,
                self.model.status == AiLogStatus.COMPLETED
            ]

            if provider:
                conditions.append(self.model.provider == provider)

            if model_name:
                conditions.append(self.model.model_name == model_name)

            # Performance metrics query
            stmt = select(
                func.count().label('total_operations'),
                func.avg(cast(self.model.duration_seconds, Float)).label('avg_duration'),
                func.min(cast(self.model.duration_seconds, Float)).label('min_duration'),
                func.max(cast(self.model.duration_seconds, Float)).label('max_duration'),
                func.sum(self.model.total_tokens).label('total_tokens'),
                func.avg(self.model.total_tokens).label('avg_tokens'),
                func.sum(cast(self.model.cost, Float)).label('total_cost')
            ).where(and_(*conditions))

            result = await self.session.execute(stmt)
            row = result.first()

            if not row or row.total_operations == 0:
                return {
                    'total_operations': 0,
                    'avg_duration': 0,
                    'min_duration': 0,
                    'max_duration': 0,
                    'total_tokens': 0,
                    'avg_tokens': 0,
                    'total_cost': 0,
                    'success_rate': 0
                }

            # Get success rate
            success_conditions = conditions.copy()
            success_conditions.append(self.model.status == AiLogStatus.COMPLETED)

            success_stmt = select(func.count()).where(and_(*success_conditions))
            success_result = await self.session.execute(success_stmt)
            successful_operations = success_result.scalar()

            total_stmt = select(func.count()).where(and_(*conditions))
            total_result = await self.session.execute(total_stmt)
            total_operations = total_result.scalar()

            return {
                'total_operations': total_operations,
                'successful_operations': successful_operations,
                'success_rate': (successful_operations / total_operations * 100) if total_operations > 0 else 0,
                'avg_duration': float(row.avg_duration) if row.avg_duration else 0,
                'min_duration': float(row.min_duration) if row.min_duration else 0,
                'max_duration': float(row.max_duration) if row.max_duration else 0,
                'total_tokens': row.total_tokens or 0,
                'avg_tokens': float(row.avg_tokens) if row.avg_tokens else 0,
                'total_cost': float(row.total_cost) if row.total_cost else 0
            }

        except Exception as e:
            self.logger.error(
                "Failed to get performance metrics",
                error=str(e),
                days=days,
                provider=provider
            )
            raise DatabaseException(f"Failed to get performance metrics: {str(e)}")

    async def get_provider_statistics(self, days: int = 30) -> List[Dict[str, Any]]:
        """
        Get statistics by AI provider.

        Args:
            days: Number of days to analyze

        Returns:
            List of provider statistics
        """
        try:
            # Calculate date threshold
            threshold_date = datetime.now(timezone.utc) - timedelta(days=days)

            stmt = select(
                self.model.provider,
                self.model.model_name,
                func.count().label('total_operations'),
                func.sum(self.model.total_tokens).label('total_tokens'),
                func.sum(cast(self.model.cost, Float)).label('total_cost'),
                func.avg(cast(self.model.duration_seconds, Float)).label('avg_duration')
            ).where(
                self.model.created_at >= threshold_date
            ).group_by(
                self.model.provider,
                self.model.model_name
            ).order_by(desc('total_operations'))

            result = await self.session.execute(stmt)
            rows = result.all()

            return [
                {
                    'provider': row.provider,
                    'model_name': row.model_name,
                    'total_operations': row.total_operations,
                    'total_tokens': row.total_tokens or 0,
                    'total_cost': float(row.total_cost) if row.total_cost else 0,
                    'avg_duration': float(row.avg_duration) if row.avg_duration else 0
                }
                for row in rows
            ]

        except Exception as e:
            self.logger.error(
                "Failed to get provider statistics",
                error=str(e),
                days=days
            )
            raise DatabaseException(f"Failed to get provider statistics: {str(e)}")

    async def get_workflow_mode_statistics(self, days: int = 30) -> List[Dict[str, Any]]:
        """
        Get statistics by workflow mode.

        Args:
            days: Number of days to analyze

        Returns:
            List of workflow mode statistics
        """
        try:
            # Calculate date threshold
            threshold_date = datetime.now(timezone.utc) - timedelta(days=days)

            stmt = select(
                self.model.workflow_mode,
                func.count().label('total_operations'),
                func.count(func.nullif(self.model.status != AiLogStatus.COMPLETED, True)).label('successful_operations'),
                func.sum(self.model.total_tokens).label('total_tokens'),
                func.sum(cast(self.model.cost, Float)).label('total_cost'),
                func.avg(cast(self.model.duration_seconds, Float)).label('avg_duration')
            ).where(
                self.model.created_at >= threshold_date
            ).group_by(self.model.workflow_mode).order_by(desc('total_operations'))

            result = await self.session.execute(stmt)
            rows = result.all()

            return [
                {
                    'workflow_mode': row.workflow_mode,
                    'total_operations': row.total_operations,
                    'successful_operations': row.successful_operations or 0,
                    'success_rate': ((row.successful_operations or 0) / row.total_operations * 100) if row.total_operations > 0 else 0,
                    'total_tokens': row.total_tokens or 0,
                    'total_cost': float(row.total_cost) if row.total_cost else 0,
                    'avg_duration': float(row.avg_duration) if row.avg_duration else 0
                }
                for row in rows
            ]

        except Exception as e:
            self.logger.error(
                "Failed to get workflow mode statistics",
                error=str(e),
                days=days
            )
            raise DatabaseException(f"Failed to get workflow mode statistics: {str(e)}")

    async def get_recent_failures(
        self,
        hours: int = 24,
        limit: int = 20
    ) -> List[AiLog]:
        """
        Get recent AI operation failures.

        Args:
            hours: Number of hours to look back
            limit: Maximum number of results

        Returns:
            List of failed AI logs
        """
        try:
            # Calculate date threshold
            threshold_date = datetime.now(timezone.utc) - timedelta(hours=hours)

            stmt = select(self.model).where(
                and_(
                    self.model.created_at >= threshold_date,
                    self.model.status == AiLogStatus.FAILED
                )
            ).order_by(desc(self.model.created_at)).limit(limit)

            result = await self.session.execute(stmt)
            logs = result.scalars().all()

            return list(logs)

        except Exception as e:
            self.logger.error(
                "Failed to get recent failures",
                error=str(e),
                hours=hours
            )
            raise DatabaseException(f"Failed to get recent failures: {str(e)}")

    async def cleanup_old_logs(self, days: int = 90) -> int:
        """
        Clean up old AI logs (completed logs older than specified days).

        Args:
            days: Number of days after which to clean up logs

        Returns:
            Number of deleted logs
        """
        try:
            # Calculate date threshold
            threshold_date = datetime.now(timezone.utc) - timedelta(days=days)

            # Delete old completed logs
            stmt = select(self.model).where(
                and_(
                    self.model.created_at < threshold_date,
                    self.model.status == AiLogStatus.COMPLETED
                )
            )

            result = await self.session.execute(stmt)
            old_logs = result.scalars().all()

            # Delete logs
            for log in old_logs:
                await self.session.delete(log)

            await self.session.commit()

            self.logger.info(
                "Cleaned up old AI logs",
                deleted_count=len(old_logs),
                days=days
            )

            return len(old_logs)

        except Exception as e:
            await self.session.rollback()
            self.logger.error(
                "Failed to cleanup old AI logs",
                error=str(e),
                days=days
            )
            raise DatabaseException(f"Failed to cleanup old AI logs: {str(e)}")

    def __repr__(self) -> str:
        return "<AiLogRepository>"