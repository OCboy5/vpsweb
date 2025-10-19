"""
Database Optimization and Indexing for VPSWeb Repository System.

This module provides comprehensive database optimization including
index management, query optimization, and performance monitoring.

Features:
- Automatic index creation and management
- Query performance analysis and optimization
- Database statistics and monitoring
- Query plan analysis
- Performance metrics collection
- Connection pooling optimization
"""

from typing import Any, Dict, List, Optional, Tuple, Type
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
import time

from sqlalchemy import (
    Index, create_index, text, func, desc, asc,
    inspect, event, DDL
)
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import Select
from pydantic import BaseModel, Field

from .models import Poem, Translation, AiLog, HumanNote
from .database import DatabaseManager
from ..utils.logger import get_structured_logger

logger = get_structured_logger()


class IndexType(str, Enum):
    """Types of database indexes."""
    BTREE = "btree"
    HASH = "hash"
    GIN = "gin"
    GIST = "gist"
    PARTIAL = "partial"
    EXPRESSION = "expression"


class IndexPriority(str, Enum):
    """Priority levels for indexes."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class IndexDefinition:
    """Definition of a database index."""
    name: str
    table_name: str
    columns: List[str]
    index_type: IndexType = IndexType.BTREE
    unique: bool = False
    where_clause: Optional[str] = None
    priority: IndexPriority = IndexPriority.MEDIUM
    description: str = ""
    estimated_size_mb: float = 0.0
    usage_frequency: float = 0.0
    created_at: Optional[datetime] = None


@dataclass
class QueryPerformanceMetrics:
    """Performance metrics for a query."""
    query_sql: str
    execution_time_ms: float
    rows_examined: int
    rows_returned: int
    index_used: bool
    index_name: Optional[str]
    timestamp: datetime
    query_hash: str


class DatabaseIndexManager:
    """
    Manages database indexes for optimal performance.

    Provides automatic index creation, monitoring, and maintenance
    for the VPSWeb repository system.
    """

    def __init__(self, db_manager: DatabaseManager):
        """
        Initialize index manager.

        Args:
            db_manager: Database manager instance
        """
        self.db_manager = db_manager
        self.index_definitions = self._define_indexes()
        self.performance_metrics: List[QueryPerformanceMetrics] = []
        self.index_usage_stats: Dict[str, Dict[str, Any]] = {}

    def _define_indexes(self) -> List[IndexDefinition]:
        """
        Define all necessary database indexes.

        Returns:
            List of index definitions
        """
        indexes = []

        # Poem table indexes
        indexes.extend([
            # Primary search fields
            IndexDefinition(
                name="idx_poems_poet_name",
                table_name="poems",
                columns=["poet_name"],
                priority=IndexPriority.CRITICAL,
                description="Index for searching poems by poet name",
                usage_frequency=0.8
            ),
            IndexDefinition(
                name="idx_poems_title",
                table_name="poems",
                columns=["poem_title"],
                priority=IndexPriority.CRITICAL,
                description="Index for searching poems by title",
                usage_frequency=0.7
            ),
            IndexDefinition(
                name="idx_poems_language",
                table_name="poems",
                columns=["source_language"],
                priority=IndexPriority.HIGH,
                description="Index for filtering poems by language",
                usage_frequency=0.6
            ),
            IndexDefinition(
                name="idx_poems_active",
                table_name="poems",
                columns=["is_active"],
                priority=IndexPriority.HIGH,
                where_clause="is_active = 1",
                description="Partial index for active poems only",
                usage_frequency=0.9
            ),
            IndexDefinition(
                name="idx_poems_created_at",
                table_name="poems",
                columns=["created_at"],
                priority=IndexPriority.MEDIUM,
                description="Index for sorting poems by creation date",
                usage_frequency=0.4
            ),
            # Composite indexes
            IndexDefinition(
                name="idx_poems_language_active",
                table_name="poems",
                columns=["source_language", "is_active"],
                priority=IndexPriority.HIGH,
                description="Composite index for language and active status filtering",
                usage_frequency=0.8
            ),
            IndexDefinition(
                name="idx_poems_poet_created",
                table_name="poems",
                columns=["poet_name", "created_at"],
                priority=IndexPriority.MEDIUM,
                description="Composite index for poet and date sorting",
                usage_frequency=0.3
            ),
        ])

        # Translation table indexes
        indexes.extend([
            # Foreign key indexes
            IndexDefinition(
                name="idx_translations_poem_id",
                table_name="translations",
                columns=["poem_id"],
                priority=IndexPriority.CRITICAL,
                description="Foreign key index for poem relationship",
                usage_frequency=0.9
            ),
            # Search and filter indexes
            IndexDefinition(
                name="idx_translations_language",
                table_name="translations",
                columns=["target_language"],
                priority=IndexPriority.HIGH,
                description="Index for filtering translations by target language",
                usage_frequency=0.7
            ),
            IndexDefinition(
                name="idx_translations_published",
                table_name="translations",
                columns=["is_published"],
                priority=IndexPriority.HIGH,
                where_clause="is_published = 1",
                description="Partial index for published translations",
                usage_frequency=0.8
            ),
            IndexDefinition(
                name="idx_translations_version",
                table_name="translations",
                columns=["poem_id", "version"],
                priority=IndexPriority.HIGH,
                description="Index for finding latest translation version",
                usage_frequency=0.6
            ),
            # Quality and type indexes
            IndexDefinition(
                name="idx_translations_quality",
                table_name="translations",
                columns=["quality_score"],
                priority=IndexPriority.MEDIUM,
                description="Index for sorting translations by quality",
                usage_frequency=0.3
            ),
            IndexDefinition(
                name="idx_translations_type",
                table_name="translations",
                columns=["translator_type"],
                priority=IndexPriority.MEDIUM,
                description="Index for filtering by translator type",
                usage_frequency=0.4
            ),
            # Composite indexes
            IndexDefinition(
                name="idx_translations_language_published",
                table_name="translations",
                columns=["target_language", "is_published"],
                priority=IndexPriority.HIGH,
                description="Composite index for language and published status",
                usage_frequency=0.8
            ),
        ])

        # AI Log table indexes
        indexes.extend([
            # Foreign key indexes
            IndexDefinition(
                name="idx_ai_logs_poem_id",
                table_name="ai_logs",
                columns=["poem_id"],
                priority=IndexPriority.HIGH,
                description="Foreign key index for poem relationship",
                usage_frequency=0.7
            ),
            IndexDefinition(
                name="idx_ai_logs_translation_id",
                table_name="ai_logs",
                columns=["translation_id"],
                priority=IndexPriority.HIGH,
                description="Foreign key index for translation relationship",
                usage_frequency=0.6
            ),
            # Status and provider indexes
            IndexDefinition(
                name="idx_ai_logs_status",
                table_name="ai_logs",
                columns=["status"],
                priority=IndexPriority.HIGH,
                description="Index for filtering AI logs by status",
                usage_frequency=0.5
            ),
            IndexDefinition(
                name="idx_ai_logs_provider",
                table_name="ai_logs",
                columns=["provider"],
                priority=IndexPriority.MEDIUM,
                description="Index for filtering AI logs by provider",
                usage_frequency=0.4
            ),
            IndexDefinition(
                name="idx_ai_logs_model",
                table_name="ai_logs",
                columns=["model_name"],
                priority=IndexPriority.MEDIUM,
                description="Index for filtering AI logs by model",
                usage_frequency=0.3
            ),
            # Performance indexes
            IndexDefinition(
                name="idx_ai_logs_duration",
                table_name="ai_logs",
                columns=["duration_seconds"],
                priority=IndexPriority.LOW,
                description="Index for sorting AI logs by duration",
                usage_frequency=0.2
            ),
            IndexDefinition(
                name="idx_ai_logs_cost",
                table_name="ai_logs",
                columns=["cost"],
                priority=IndexPriority.LOW,
                description="Index for sorting AI logs by cost",
                usage_frequency=0.2
            ),
            # Time-based indexes
            IndexDefinition(
                name="idx_ai_logs_created_at",
                table_name="ai_logs",
                columns=["created_at"],
                priority=IndexPriority.MEDIUM,
                description="Index for sorting AI logs by creation time",
                usage_frequency=0.4
            ),
            # Composite indexes
            IndexDefinition(
                name="idx_ai_logs_status_created",
                table_name="ai_logs",
                columns=["status", "created_at"],
                priority=IndexPriority.MEDIUM,
                description="Composite index for status and time filtering",
                usage_frequency=0.5
            ),
        ])

        # Human Note table indexes
        indexes.extend([
            # Foreign key indexes
            IndexDefinition(
                name="idx_human_notes_poem_id",
                table_name="human_notes",
                columns=["poem_id"],
                priority=IndexPriority.HIGH,
                description="Foreign key index for poem relationship",
                usage_frequency=0.7
            ),
            IndexDefinition(
                name="idx_human_notes_translation_id",
                table_name="human_notes",
                columns=["translation_id"],
                priority=IndexPriority.HIGH,
                description="Foreign key index for translation relationship",
                usage_frequency=0.6
            ),
            # Content and type indexes
            IndexDefinition(
                name="idx_human_notes_type",
                table_name="human_notes",
                columns=["note_type"],
                priority=IndexPriority.MEDIUM,
                description="Index for filtering notes by type",
                usage_frequency=0.4
            ),
            IndexDefinition(
                name="idx_human_notes_public",
                table_name="human_notes",
                columns=["is_public"],
                priority=IndexPriority.HIGH,
                where_clause="is_public = 1",
                description="Partial index for public notes",
                usage_frequency=0.8
            ),
            IndexDefinition(
                name="idx_human_notes_author",
                table_name="human_notes",
                columns=["author_name"],
                priority=IndexPriority.MEDIUM,
                description="Index for filtering notes by author",
                usage_frequency=0.3
            ),
            # Time-based indexes
            IndexDefinition(
                name="idx_human_notes_created_at",
                table_name="human_notes",
                columns=["created_at"],
                priority=IndexPriority.MEDIUM,
                description="Index for sorting notes by creation time",
                usage_frequency=0.4
            ),
            # Composite indexes
            IndexDefinition(
                name="idx_human_notes_public_created",
                table_name="human_notes",
                columns=["is_public", "created_at"],
                priority=IndexPriority.HIGH,
                description="Composite index for public notes and time",
                usage_frequency=0.6
            ),
        ])

        # Full-text search indexes (for SQLite FTS5)
        if self.db_manager.database_url.startswith("sqlite"):
            indexes.extend([
                IndexDefinition(
                    name="idx_poems_fts",
                    table_name="poems",
                    columns=["poet_name", "poem_title", "original_text"],
                    index_type=IndexType.EXPRESSION,
                    description="Full-text search index for poems",
                    priority=IndexPriority.CRITICAL,
                    usage_frequency=0.9
                ),
                IndexDefinition(
                    name="idx_translations_fts",
                    table_name="translations",
                    columns=["translated_text"],
                    index_type=IndexType.EXPRESSION,
                    description="Full-text search index for translations",
                    priority=IndexPriority.HIGH,
                    usage_frequency=0.8
                ),
                IndexDefinition(
                    name="idx_human_notes_fts",
                    table_name="human_notes",
                    columns=["title", "content"],
                    index_type=IndexType.EXPRESSION,
                    description="Full-text search index for human notes",
                    priority=IndexPriority.MEDIUM,
                    usage_frequency=0.6
                ),
            ])

        return indexes

    async def create_indexes(self) -> None:
        """
        Create all defined indexes in the database.

        This should be called after database initialization
        to ensure optimal query performance.
        """
        if not self.db_manager.engine:
            raise RuntimeError("Database not initialized")

        logger.info("Creating database indexes...")

        async with self.db_manager.get_session_context() as session:
            # Sort indexes by priority (critical first)
            sorted_indexes = sorted(
                self.index_definitions,
                key=lambda x: (
                    {"critical": 0, "high": 1, "medium": 2, "low": 3}[x.priority.value],
                    x.priority.value
                )
            )

            for index_def in sorted_indexes:
                try:
                    await self._create_single_index(session, index_def)
                    logger.info(f"Created index: {index_def.name}")
                except Exception as e:
                    logger.error(f"Failed to create index {index_def.name}: {e}")

            await session.commit()

    async def _create_single_index(self, session: Session, index_def: IndexDefinition) -> None:
        """
        Create a single index in the database.

        Args:
            session: Database session
            index_def: Index definition
        """
        # Create index based on type
        if index_def.index_type == IndexType.EXPRESSION:
            # For SQLite FTS5
            if self.db_manager.database_url.startswith("sqlite"):
                await self._create_fts_index(session, index_def)
        elif index_def.index_type == IndexType.PARTIAL:
            await self._create_partial_index(session, index_def)
        else:
            # Standard index
            index = Index(
                index_def.name,
                *index_def.columns,
                unique=index_def.unique,
                postgresql_where=index_def.where_clause
            )
            index.create(session.bind)

        # Update metadata
        index_def.created_at = datetime.utcnow()

    async def _create_fts_index(self, session: Session, index_def: IndexDefinition) -> None:
        """Create full-text search index for SQLite."""
        # SQLite FTS5 implementation
        columns_str = ", ".join(index_def.columns)
        fts_table = f"fts_{index_def.table_name}"

        # Create FTS virtual table
        await session.execute(text(f"""
            CREATE VIRTUAL TABLE IF NOT EXISTS {fts_table}
            USING fts5({columns_str}, content='{index_def.table_name}', content_rowid='rowid')
        """))

        # Create triggers to keep FTS table in sync
        await session.execute(text(f"""
            CREATE TRIGGER IF NOT EXISTS {index_def.table_name}_ai AFTER INSERT ON {index_def.table_name} BEGIN
                INSERT INTO {fts_table}(rowid, {columns_str})
                VALUES (new.rowid, {", ".join([f"new.{col}" for col in index_def.columns])});
            END
        """))

        await session.execute(text(f"""
            CREATE TRIGGER IF NOT EXISTS {index_def.table_name}_ad AFTER DELETE ON {index_def.table_name} BEGIN
                INSERT INTO {fts_table}(fts_table, rowid, {columns_str})
                VALUES ('delete', old.rowid, {", ".join([f"old.{col}" for col in index_def.columns])});
            END
        """))

        await session.execute(text(f"""
            CREATE TRIGGER IF NOT EXISTS {index_def.table_name}_au AFTER UPDATE ON {index_def.table_name} BEGIN
                INSERT INTO {fts_table}(fts_table, rowid, {columns_str})
                VALUES ('delete', old.rowid, {", ".join([f"old.{col}" for col in index_def.columns])});
                INSERT INTO {fts_table}(rowid, {columns_str})
                VALUES (new.rowid, {", ".join([f"new.{col}" for col in index_def.columns])});
            END
        """))

    async def _create_partial_index(self, session: Session, index_def: IndexDefinition) -> None:
        """Create partial index."""
        if not index_def.where_clause:
            raise ValueError("Partial index requires where_clause")

        index = Index(
            index_def.name,
            *index_def.columns,
            unique=index_def.unique,
            postgresql_where=index_def.where_clause
        )
        index.create(session.bind)

    async def analyze_index_usage(self) -> Dict[str, Dict[str, Any]]:
        """
        Analyze index usage statistics.

        Returns:
            Dictionary with index usage information
        """
        if not self.db_manager.engine:
            raise RuntimeError("Database not initialized")

        async with self.db_manager.get_session_context() as session:
            # Get index statistics (PostgreSQL specific)
            if self.db_manager.database_url.startswith("postgresql"):
                result = await session.execute(text("""
                    SELECT
                        schemaname,
                        tablename,
                        indexname,
                        idx_scan,
                        idx_tup_read,
                        idx_tup_fetch,
                        pg_size_pretty(indexname::text) as size
                    FROM pg_stat_user_indexes
                    ORDER BY idx_scan DESC, idx_tup_read DESC
                """))

                usage_stats = {}
                for row in result:
                    index_key = f"{row.tablename}.{row.indexname}"
                    usage_stats[index_key] = {
                        "schema": row.schemaname,
                        "table": row.tablename,
                        "index": row.indexname,
                        "scans": row.idx_scan,
                        "tuples_read": row.idx_tup_read,
                        "tuples_fetched": row.idx_tup_fetch,
                        "size": row.size
                    }

                return usage_stats

            # SQLite specific analysis
            elif self.db_manager.database_url.startswith("sqlite"):
                result = await session.execute(text("""
                    SELECT name, sql
                    FROM sqlite_master
                    WHERE type = 'index'
                    ORDER BY name
                """))

                usage_stats = {}
                for row in result:
                    usage_stats[row.name] = {
                        "sql": row.sql,
                        "estimated_usage": self._estimate_index_usage(row.name)
                    }

                return usage_stats

        return {}

    def _estimate_index_usage(self, index_name: str) -> float:
        """Estimate index usage based on defined frequency."""
        for index_def in self.index_definitions:
            if index_def.name == index_name:
                return index_def.usage_frequency
        return 0.0

    async def analyze_query_performance(
        self,
        query: Select,
        session: Session
    ) -> QueryPerformanceMetrics:
        """
        Analyze query performance.

        Args:
            query: SQLAlchemy query to analyze
            session: Database session

        Returns:
            Query performance metrics
        """
        start_time = time.time()
        query_str = str(query.compile(compile_kwargs={"literal_binds": True}))

        # Execute EXPLAIN ANALYZE (PostgreSQL) or EXPLAIN QUERY PLAN (SQLite)
        if self.db_manager.database_url.startswith("postgresql"):
            explain_query = text(f"EXPLAIN (ANALYZE, BUFFERS) {query_str}")
        else:
            explain_query = text(f"EXPLAIN QUERY PLAN {query_str}")

        try:
            explain_result = await session.execute(explain_query)
            explain_output = explain_result.fetchall()

            # Parse explain output
            index_used, index_name = self._parse_explain_output(explain_output)

            # Execute actual query
            result = await session.execute(query)
            rows_returned = len(result.fetchall())

            execution_time = (time.time() - start_time) * 1000

            metrics = QueryPerformanceMetrics(
                query_sql=query_str,
                execution_time_ms=execution_time,
                rows_examined=self._estimate_rows_examined(explain_output),
                rows_returned=rows_returned,
                index_used=index_used,
                index_name=index_name,
                timestamp=datetime.utcnow(),
                query_hash=self._hash_query(query_str)
            )

            self.performance_metrics.append(metrics)
            return metrics

        except Exception as e:
            logger.error(f"Query performance analysis failed: {e}")
            # Return basic metrics if analysis fails
            execution_time = (time.time() - start_time) * 1000
            return QueryPerformanceMetrics(
                query_sql=query_str,
                execution_time_ms=execution_time,
                rows_examined=0,
                rows_returned=0,
                index_used=False,
                index_name=None,
                timestamp=datetime.utcnow(),
                query_hash=self._hash_query(query_str)
            )

    def _parse_explain_output(self, explain_output: List) -> Tuple[bool, Optional[str]]:
        """Parse EXPLAIN output to extract index usage."""
        index_used = False
        index_name = None

        for row in explain_output:
            output_str = str(row).lower()
            if "index" in output_str:
                index_used = True
                # Extract index name (simplified)
                words = output_str.split()
                for i, word in enumerate(words):
                    if "index" in word and i + 1 < len(words):
                        index_name = words[i + 1].strip(",:;")
                        break

        return index_used, index_name

    def _estimate_rows_examined(self, explain_output: List) -> int:
        """Estimate number of rows examined from EXPLAIN output."""
        # Simplified estimation
        return len(explain_output)

    def _hash_query(self, query_str: str) -> str:
        """Create a hash of the query for identification."""
        import hashlib
        return hashlib.md5(query_str.encode()).hexdigest()[:16]

    async def get_slow_queries(
        self,
        threshold_ms: float = 1000.0,
        limit: int = 10
    ) -> List[QueryPerformanceMetrics]:
        """
        Get slow queries based on execution time.

        Args:
            threshold_ms: Minimum execution time to consider slow
            limit: Maximum number of queries to return

        Returns:
            List of slow query metrics
        """
        slow_queries = [
            metric for metric in self.performance_metrics
            if metric.execution_time_ms >= threshold_ms
        ]

        # Sort by execution time (slowest first)
        slow_queries.sort(key=lambda x: x.execution_time_ms, reverse=True)

        return slow_queries[:limit]

    async def get_index_recommendations(self) -> List[Dict[str, Any]]:
        """
        Get recommendations for index optimization.

        Returns:
            List of index recommendations
        """
        recommendations = []

        # Analyze slow queries for missing indexes
        slow_queries = await self.get_slow_queries()
        for metric in slow_queries:
            if not metric.index_used:
                recommendations.append({
                    "type": "missing_index",
                    "query": metric.query_sql,
                    "execution_time_ms": metric.execution_time_ms,
                    "recommendation": "Consider adding an index for commonly filtered columns",
                    "priority": "high"
                })

        # Check for unused indexes
        index_usage = await self.analyze_index_usage()
        for index_name, usage in index_usage.items():
            if usage.get("scans", 0) == 0:
                recommendations.append({
                    "type": "unused_index",
                    "index": index_name,
                    "recommendation": "Consider dropping unused index to save space",
                    "priority": "medium"
                })

        return recommendations

    async def optimize_database(self) -> Dict[str, Any]:
        """
        Perform database optimization tasks.

        Returns:
            Optimization results
        """
        results = {
            "vacuum": await self._vacuum_database(),
            "analyze": await self._analyze_database(),
            "reindex": await self._reindex_database(),
            "recommendations": await self.get_index_recommendations()
        }

        logger.info("Database optimization completed", results=results)
        return results

    async def _vacuum_database(self) -> bool:
        """Run VACUUM to optimize storage."""
        try:
            async with self.db_manager.get_session_context() as session:
                await session.execute(text("VACUUM"))
                await session.commit()
            return True
        except Exception as e:
            logger.error(f"VACUUM failed: {e}")
            return False

    async def _analyze_database(self) -> bool:
        """Run ANALYZE to update statistics."""
        try:
            async with self.db_manager.get_session_context() as session:
                await session.execute(text("ANALYZE"))
                await session.commit()
            return True
        except Exception as e:
            logger.error(f"ANALYZE failed: {e}")
            return False

    async def _reindex_database(self) -> bool:
        """Run REINDEX to rebuild indexes."""
        try:
            async with self.db_manager.get_session_context() as session:
                await session.execute(text("REINDEX"))
                await session.commit()
            return True
        except Exception as e:
            logger.error(f"REINDEX failed: {e}")
            return False


class QueryOptimizer:
    """
    Optimizes database queries for better performance.

    Provides query analysis, optimization suggestions,
    and automatic query improvements.
    """

    def __init__(self, index_manager: DatabaseIndexManager):
        """
        Initialize query optimizer.

        Args:
            index_manager: Index manager instance
        """
        self.index_manager = index_manager

    def optimize_query(self, query: Select, model_class: Type) -> Select:
        """
        Optimize a query based on available indexes.

        Args:
            query: SQLAlchemy query to optimize
            model_class: Model class for the query

        Returns:
            Optimized query
        """
        # Add appropriate ordering based on available indexes
        if not query.column_descriptions:
            # Try to add ordering based on primary key or indexed columns
            indexed_columns = self._get_indexed_columns(model_class)
            if indexed_columns:
                query = query.order_by(desc(indexed_columns[0]))

        return query

    def _get_indexed_columns(self, model_class: Type) -> List[str]:
        """Get indexed columns for a model class."""
        table_name = model_class.__tablename__
        indexed_columns = []

        for index_def in self.index_manager.index_definitions:
            if index_def.table_name == table_name:
                indexed_columns.extend(index_def.columns)

        return indexed_columns


# Global instances
_index_manager: Optional[DatabaseIndexManager] = None
_query_optimizer: Optional[QueryOptimizer] = None


def get_index_manager(db_manager: DatabaseManager) -> DatabaseIndexManager:
    """Get or create the global index manager."""
    global _index_manager
    if _index_manager is None:
        _index_manager = DatabaseIndexManager(db_manager)
    return _index_manager


def get_query_optimizer(db_manager: DatabaseManager) -> QueryOptimizer:
    """Get or create the global query optimizer."""
    global _query_optimizer
    if _query_optimizer is None:
        _query_optimizer = QueryOptimizer(get_index_manager(db_manager))
    return _query_optimizer