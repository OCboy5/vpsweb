"""
Query Optimization for VPSWeb Repository System.

This module provides comprehensive query optimization to prevent N+1 problems
and improve database performance through efficient relationship loading strategies.

Features:
- N+1 query detection and prevention
- Optimized relationship loading (eager, selectin, joinedload)
- Query performance monitoring and analysis
- Automatic query optimization suggestions
- Batch loading strategies
- Relationship loading patterns for different use cases
"""

from typing import Any, Dict, List, Optional, Type, Union, Set, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import time
from collections import defaultdict

from sqlalchemy import (
    select, and_, or_, func, text, desc, asc,
    inspect, Index, case as sql_case
)
from sqlalchemy.orm import (
    Session, joinedload, selectinload, subqueryload,
    aliased, contains_eager, relationship,
    Load, with_entities, load_only, defaultload,
    lazyload, raiseload
)
from sqlalchemy.orm.exc import DetachedInstanceError
from sqlalchemy.sql import Select
from pydantic import BaseModel, Field

from .models import Poem, Translation, AiLog, HumanNote
from ..utils.logger import get_structured_logger

logger = get_structured_logger()


class LoadingStrategy(str, Enum):
    """Relationship loading strategies."""
    LAZY = "lazy"
    EAGER = "eager"
    SELECTIN = "selectin"
    JOINED = "joined"
    SUBQUERY = "subquery"
    RAISE = "raise"
    SELECTIN_POLYMORPHIC = "selectin_polymorphic"


class QueryPattern(str, Enum):
    """Common query patterns that may cause N+1 problems."""
    LIST_WITH_RELATIONSHIPS = "list_with_relationships"
    DETAIL_WITH_RELATIONSHIPS = "detail_with_relationships"
    SEARCH_WITH_RELATIONSHIPS = "search_with_relationships"
    BATCH_OPERATIONS = "batch_operations"
    TREE_STRUCTURE = "tree_structure"


@dataclass
class QueryMetrics:
    """Metrics for query performance analysis."""
    query_sql: str = ""
    execution_time_ms: float = 0.0
    rows_returned: int = 0
    queries_executed: int = 1
    relationships_loaded: List[str] = field(default_factory=list)
    loading_strategies: Dict[str, LoadingStrategy] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)
    query_hash: str = ""
    n1_queries_detected: int = 0
    optimization_applied: bool = False


@dataclass
class LoadingRecommendation:
    """Recommendation for query optimization."""
    pattern: QueryPattern
    current_issues: List[str] = field(default_factory=list)
    recommended_strategy: LoadingStrategy
    expected_improvement: str
    code_example: str = ""
    impact: str = "medium"  # low, medium, high, critical


class RelationshipAnalyzer:
    """
    Analyzes SQLAlchemy relationships for optimization opportunities.

    Identifies potential N+1 problems and suggests optimal loading strategies.
    """

    def __init__(self):
        """Initialize relationship analyzer."""
        self.inspector = None
        self.relationship_cache = {}

    def analyze_model(self, model_class: Type) -> Dict[str, Any]:
        """
        Analyze a model's relationships.

        Args:
            model_class: SQLAlchemy model class to analyze

        Returns:
            Analysis results
        """
        # Get SQLAlchemy inspector
        if self.inspector is None:
            return {}

        try:
            relationships = self.inspector.get_relationships(model_class.__table__)
        except Exception as e:
            logger.error(f"Failed to inspect model {model_class.__name__}: {e}")
            return {}

        analysis = {
            "model": model_class.__name__,
            "table": model_class.__tablename__,
            "relationships": {}
        }

        for rel in relationships:
            rel_info = {
                "name": rel["name"],
                "direction": rel["direction"],
                "foreign_key": rel.get("foreign_keys", []),
                "target_class": rel.get("target"),
                "cardinality": self._determine_cardinality(rel),
                "current_loading": self._get_current_loading(model_class, rel["name"]),
                "recommended_strategy": self._recommend_strategy(rel),
                "usage_frequency": self._estimate_usage_frequency(model_class, rel["name"])
            }
            analysis["relationships"][rel["name"]] = rel_info

        return analysis

    def _determine_cardinality(self, relationship: Dict[str, Any]) -> str:
        """Determine relationship cardinality."""
        direction = relationship.get("direction", "")

        if direction == "ONETOMANY":
            return "many-to-one"
        elif direction == "MANYTOMANY":
            return "one-to-many"
        elif direction == "ONETOONE":
            return "one-to-one"
        else:
            return "unknown"

    def _get_current_loading(self, model_class: Type, relationship_name: str) -> LoadingStrategy:
        """Get current loading strategy for a relationship."""
        try:
            mapper = inspect(model_class)
            if relationship_name in mapper.relationships:
                prop = mapper.relationships[relationship_name]

                if prop.lazy == "selectin":
                    return LoadingStrategy.SELECTIN
                elif prop.lazy == "joined":
                    return LoadingStrategy.JOINED
                elif prop.lazy == "subquery":
                    return LoadingStrategy.SUBQUERY
                elif prop.lazy == "raise":
                    return LoadingStrategy.RAISE
                else:
                    return LoadingStrategy.LAZY
        except Exception:
            pass

        return LoadingStrategy.LAZY

    def _recommend_strategy(self, relationship: Dict[str, Any]) -> LoadingStrategy:
        """Recommend optimal loading strategy for a relationship."""
        direction = relationship.get("direction", "")
        cardinality = self._determine_cardinality(relationship)

        # One-to-many relationships: use selectin by default
        if direction == "ONETOMANY":
            return LoadingStrategy.SELECTIN

        # Many-to-many: use joinedload for small collections, selectin for large
        elif direction == "MANYTOMANY":
            return LoadingStrategy.JOINED

        # One-to-one: use joinedload
        elif direction == "ONETOONE":
            return LoadingStrategy.JOINED

        return LoadingStrategy.SELECTIN

    def _estimate_usage_frequency(self, model_class: Type, relationship_name: str) -> float:
        """Estimate how frequently a relationship is accessed."""
        # This would require access to actual usage data
        # For now, use heuristics based on relationship importance
        high_priority_relationships = {
            "Poem.translations": 0.9,
            "Translation.poem": 0.9,
            "Translation.ai_logs": 0.7,
            "Translation.human_notes": 0.6,
            "HumanNote.poem": 0.6,
            "HumanNote.translation": 0.6,
        }

        key = f"{model_class.__name__}.{relationship_name}"
        return high_priority_relationships.get(key, 0.5)


class QueryOptimizer:
    """
    Optimizes queries to prevent N+1 problems.

    Provides automatic query analysis and optimization suggestions
    for SQLAlchemy queries.
    """

    def __init__(self, relationship_analyzer: RelationshipAnalyzer):
        """
        Initialize query optimizer.

        Args:
            relationship_analyzer: Relationship analyzer instance
        """
        self.relationship_analyzer = relationship_analyzer
        self.query_metrics: List[QueryMetrics] = []
        self.optimization_cache = {}

    def optimize_query(
        self,
        query: Select,
        model_class: Type,
        context: str = "list"
    ) -> Tuple[Select, LoadingStrategy]:
        """
        Optimize a query based on context and model relationships.

        Args:
            query: SQLAlchemy query to optimize
            model_class: Primary model class
            context: Query context (list, detail, search, etc.)

        Returns:
            Tuple of (optimized query, recommended loading strategy)
        """
        pattern = self._detect_query_pattern(query, context)
        optimization_key = f"{model_class.__name__}_{pattern.value}"

        # Check cache first
        if optimization_key in self.optimization_cache:
            cached = self.optimization_cache[optimization_key]
            return self._apply_cached_optimization(query, cached)

        # Analyze model relationships
        model_analysis = self.relationship_analyzer.analyze_model(model_class)

        # Generate optimization based on pattern and analysis
        optimized_query, strategy = self._generate_optimization(
            query, model_class, model_analysis, pattern, context
        )

        # Cache the optimization for future use
        self.optimization_cache[optimization_key] = {
            "pattern": pattern,
            "model_analysis": model_analysis,
            "optimized_query": optimized_query,
            "strategy": strategy,
            "timestamp": datetime.utcnow()
        }

        return optimized_query, strategy

    def _detect_query_pattern(self, query: Select, context: str) -> QueryPattern:
        """Detect the query pattern based on context."""
        # Simple heuristic-based pattern detection
        if "limit" in str(query) or "offset" in str(query):
            if context in ["list", "index", "search"]:
                return QueryPattern.LIST_WITH_RELATIONSHIPS
            else:
                return QueryPattern.DETAIL_WITH_RELATIONSHIPS
        elif "join" in str(query).lower():
            return QueryPattern.SEARCH_WITH_RELATIONSHIPS
        else:
            return QueryPattern.DETAIL_WITH_RELATIONSHIPS

    def _apply_cached_optimization(self, query: Select, cache_entry: Dict[str, Any]) -> Tuple[Select, LoadingStrategy]:
        """Apply cached optimization to a query."""
        pattern = cache_entry["pattern"]
        strategy = cache_entry["strategy"]

        optimized_query = query

        # Apply the cached loading strategy
        if pattern == QueryPattern.LIST_WITH_RELATIONSHIPS:
            optimized_query = self._apply_list_optimization(
                query, cache_entry["model_analysis"]
            )
        elif pattern == QueryPattern.DETAIL_WITH_RELATIONSHIPS:
            optimized_query = self._apply_detail_optimization(
                query, cache_entry["model_analysis"]
            )

        return optimized_query, strategy

    def _generate_optimization(
        self,
        query: Select,
        model_class: Type,
        model_analysis: Dict[str, Any],
        pattern: QueryPattern,
        context: str
    ) -> Tuple[Select, LoadingStrategy]:
        """Generate query optimization."""
        relationships = model_analysis.get("relationships", {})

        if pattern == QueryPattern.LIST_WITH_RELATIONSHIPS:
            return self._optimize_list_query(query, model_class, relationships)
        elif pattern == QueryPattern.DETAIL_WITH_RELATIONSHIPS:
            return self._optimize_detail_query(query, model_class, relationships)
        elif pattern == QueryPattern.SEARCH_WITH_RELATIONSHIPS:
            return self._optimize_search_query(query, model_class, relationships)
        else:
            return query, LoadingStrategy.LAZY

    def _optimize_list_query(
        self,
        query: Select,
        model_class: Type,
        relationships: Dict[str, Any]
    ) -> Tuple[Select, LoadingStrategy]:
        """Optimize query for listing operations."""
        optimized_query = query
        loading_strategies = {}
        primary_strategy = LoadingStrategy.SELECTIN

        # Identify commonly accessed relationships in lists
        high_usage_relationships = [
            "translations", "ai_logs", "human_notes"
        ]

        for rel_name, rel_info in relationships.items():
            if rel_name in high_usage_relationships:
                strategy = rel_info["recommended_strategy"]
                loading_strategies[rel_name] = strategy

                # Apply the loading strategy
                if strategy == LoadingStrategy.SELECTIN:
                    optimized_query = optimized_query.options(
                        selectinload(rel_name)
                    )
                elif strategy == LoadingStrategy.JOINED:
                    optimized_query = optimized_query.options(
                        joinedload(rel_name)
                    )

        return optimized_query, primary_strategy

    def _optimize_detail_query(
        self,
        query: Select,
        model_class: Type,
        relationships: Dict[str, Any]
    ) -> Tuple[Select, LoadingStrategy]:
        """Optimize query for detail operations."""
        optimized_query = query

        # For detail views, eager load most relationships
        eager_loads = []
        for rel_name, rel_info in relationships.items():
            if rel_info["cardinality"] in ["one-to-many", "many-to-many"]:
                eager_loads.append(selectinload(rel_name))
            else:
                eager_loads.append(joinedload(rel_name))

        if eager_loads:
            optimized_query = optimized_query.options(*eager_loads)

        return optimized_query, LoadingStrategy.EAGER

    def _optimize_search_query(
        self,
        query: Select,
        model_class: Type,
        relationships: Dict[str, Any]
    ) -> Tuple[Select, LoadingStrategy]:
        """Optimize query for search operations."""
        optimized_query = query

        # For search, load only essential relationships
        search_relationships = ["translations"]
        essential_loads = []

        for rel_name in search_relationships:
            if rel_name in relationships:
                strategy = relationships[rel_name]["recommended_strategy"]
                essential_loads.append(selectinload(rel_name))

        if essential_loads:
            optimized_query = optimized_query.options(*essential_loads)

        return optimized_query, LoadingStrategy.SELECTIN

    def _apply_list_optimization(
        self,
        query: Select,
        model_analysis: Dict[str, Any]
    ) -> Select:
        """Apply list-specific optimizations."""
        optimized_query = query

        relationships = model_analysis.get("relationships", {})

        # Add selectin loads for one-to-many relationships
        for rel_name, rel_info in relationships.items():
            if rel_info["cardinality"] in ["one-to-many", "many-to-many"]:
                optimized_query = optimized_query.options(
                    selectinload(rel_name)
                )

        return optimized_query

    def _apply_detail_optimization(
        self,
        query: Select,
        model_analysis: Dict[str, Any]
    ) -> Select:
        """Apply detail-specific optimizations."""
        optimized_query = query

        relationships = model_analysis.get("relationships", {})
        eager_loads = []

        # Add appropriate loads based on relationship type
        for rel_name, rel_info in relationships.items():
            if rel_info["cardinality"] in ["one-to-many", "many-to-many"]:
                eager_loads.append(selectinload(rel_name))
            else:
                eager_loads.append(joinedload(rel_name))

        if eager_loads:
            optimized_query = optimized_query.options(*eager_loads)

        return optimized_query

    def detect_n1_problems(self, metrics: QueryMetrics) -> List[str]:
        """
        Detect N+1 problems in query metrics.

        Args:
            metrics: Query metrics to analyze

        Returns:
            List of detected issues
        """
        issues = []

        if metrics.queries_executed > 1:
            issues.append(
                f"Multiple queries executed ({metrics.queries_executed}) "
                f"for a single request - potential N+1 problem"
            )

        if metrics.n1_queries_detected > 0:
            issues.append(
                f"N+1 query pattern detected: {metrics.n1_queries_detected} queries "
                f"executed for {metrics.rows_returned} rows returned"
            )

        return issues

    def get_optimization_recommendations(
        self,
        model_class: Type,
        current_metrics: List[QueryMetrics] = None
    ) -> List[LoadingRecommendation]:
        """
        Get optimization recommendations for a model.

        Args:
            model_class: Model class to analyze
            current_metrics: Current query metrics

        Returns:
            List of optimization recommendations
        """
        recommendations = []
        model_analysis = self.relationship_analyzer.analyze_model(model_class)

        # Analyze relationships for optimization opportunities
        for rel_name, rel_info in model_analysis.get("relationships", {}).items():
            current_strategy = rel_info["current_loading"]
            recommended_strategy = rel_info["recommended_strategy"]

            if current_strategy != recommended_strategy:
                recommendations.append(LoadingRecommendation(
                    pattern=QueryPattern.LIST_WITH_RELATIONSHIPS,
                    current_issues=[
                        f"Using {current_strategy.value} for {rel_name}"
                    ],
                    recommended_strategy=recommended_strategy,
                    expected_improvement="Reduced query count",
                    code_example=f"""
# Current:
query = session.query({model_class.__name__})
results = query.all()

# Optimized:
query = session.query({model_class.__name__}).options(
    selectinload({rel_name})
)
results = query.all()
                    """.strip(),
                    impact="high"
                ))

        return recommendations


class N1QueryDetector:
    """
    Detects N+1 query patterns in real-time.

    Monitors query execution and identifies when multiple
    queries are being executed for what should be a single request.
    """

    def __init__(self):
        """Initialize N+1 detector."""
        self.active_queries: Dict[str, QueryMetrics] = {}
        self.query_thresholds = {
            "max_queries_per_request": 5,
            "max_time_per_request_ms": 1000.0
        }

    def start_query_tracking(
        self,
        query_sql: str,
        request_id: str = None
    ) -> str:
        """
        Start tracking a query.

        Args:
            query_sql: SQL query string
            request_id: Request identifier

        Returns:
            Query tracking ID
        """
        query_id = self._hash_query(query_sql)

        metrics = QueryMetrics(
            query_sql=query_sql,
            query_hash=query_id,
            timestamp=datetime.utcnow(),
            queries_executed=1
        )

        if request_id:
            self.active_queries[request_id] = metrics

        return query_id

    def end_query_tracking(
        self,
        query_id: str,
        rows_returned: int,
        execution_time_ms: float,
        request_id: str = None
    ) -> Optional[QueryMetrics]:
        """
        End tracking for a query.

        Args:
            query_id: Query tracking ID
            rows_returned: Number of rows returned
            execution_time_ms: Execution time in milliseconds
            request_id: Request identifier

        Returns:
            Updated query metrics or None if not found
        """
        if request_id and request_id in self.active_queries:
            metrics = self.active_queries[request_id]
        else:
            # Find metrics by query ID
            metrics = None
            for req_id, req_metrics in self.active_queries.items():
                if req_metrics.query_hash == query_id:
                    metrics = req_metrics
                    break

        if metrics:
            metrics.rows_returned = rows_returned
            metrics.execution_time_ms = execution_time_ms

            # Detect N+1 problems
            if request_id in self.active_queries:
                total_queries = sum(
                    m.queries_executed for m in self.active_queries[request_id].values()
                )
                if total_queries > self.query_thresholds["max_queries_per_request"]:
                    metrics.n1_queries_detected = total_queries - 1

            self.query_metrics.append(metrics)

        return metrics

    def _hash_query(self, query_sql: str) -> str:
        """Create a hash of the query for tracking."""
        import hashlib
        return hashlib.md5(query_sql.encode()).hexdigest()[:12]


class BatchLoader:
    """
    Handles batch loading of related objects to prevent N+1 problems.

    Provides utilities for loading multiple objects efficiently
    in batch operations.
    """

    def __init__(self, session: Session):
        """
        Initialize batch loader.

        Args:
            session: Database session
        """
        self.session = session
        self.load_cache = {}

    async def load_related_objects(
        self,
        objects: List[Any],
        relationship_name: str,
        model_class: Type
    ) -> Dict[str, List[Any]]:
        """
        Load related objects for a list of objects in batch.

        Args:
            objects: List of objects to load relationships for
            relationship_name: Name of the relationship to load
            model_class: Model class of related objects

        Returns:
            Dictionary mapping object IDs to lists of related objects
        """
        if not objects:
            return {}

        # Extract primary keys
        primary_keys = []
        for obj in objects:
            if hasattr(obj, 'id'):
                primary_keys.append(obj.id)

        if not primary_keys:
            return {}

        # Load related objects in batch
        related_model = self._get_related_model(model_class, relationship_name)
        if not related_model:
            return {}

        try:
            # Use selectin loading for efficiency
            query = select(related_model).where(
                related_model.poem_id.in_(primary_keys)
            )

            result = await self.session.execute(query)
            related_objects = result.scalars().all()

            # Group by primary key
            grouped_objects = defaultdict(list)
            for related_obj in related_objects:
                if hasattr(related_obj, 'poem_id'):
                    grouped_objects[related_obj.poem_id].append(related_obj)

            return dict(grouped_objects)

        except Exception as e:
            logger.error(f"Batch loading failed for {relationship_name}: {e}")
            return {}

    def _get_related_model(self, model_class: Type, relationship_name: str) -> Optional[Type]:
        """Get the related model class for a relationship."""
        try:
            mapper = inspect(model_class)
            if relationship_name in mapper.relationships:
                prop = mapper.relationships[relationship_name]
                return prop.mapper.class_
        except Exception:
            pass

        return None


# Global instances
_relationship_analyzer = RelationshipAnalyzer()
_query_optimizer = QueryOptimizer(_relationship_analyzer)
_n1_detector = N1QueryDetector()


def get_relationship_analyzer() -> RelationshipAnalyzer:
    """Get the global relationship analyzer."""
    return _relationship_analyzer


def get_query_optimizer() -> QueryOptimizer:
    """Get the global query optimizer."""
    return _query_optimizer


def get_n1_detector() -> N1QueryDetector:
    """Get the global N+1 query detector."""
    return _n1_detector


def get_batch_loader(session: Session) -> BatchLoader:
    """Create a batch loader for the given session."""
    return BatchLoader(session)