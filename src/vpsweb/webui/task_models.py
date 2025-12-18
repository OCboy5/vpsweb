"""
VPSWeb Web UI - Task Models for In-Memory Tracking v1.0

Data models for in-memory task tracking using FastAPI app.state.
This replaces the database-backed task management with a simplified
approach suitable for personal use systems.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional


class TaskStatusEnum(str, Enum):
    """Task status enumeration for in-memory tracking"""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class TaskStatus:
    """
    In-memory task status for tracking translation workflow progress.

    This replaces the database-backed WorkflowTask model with a simple
    in-memory representation suitable for personal use systems.
    """

    task_id: str
    status: TaskStatusEnum = TaskStatusEnum.PENDING
    progress: int = 0  # Overall progress 0-100

    # Step tracking
    current_step: str = (
        ""  # "Initial Translation", "Editor Review", "Translator Revision"
    )
    step_details: Optional[Dict[str, Any]] = None  # Step-specific details
    step_progress: Optional[Dict[str, int]] = (
        None  # Individual step percentages
    )
    step_states: Optional[Dict[str, str]] = (
        None  # Individual step states: "waiting", "running", "completed"
    )

    # Metadata
    message: str = ""
    error: Optional[str] = None
    result: Optional[Dict[str, Any]] = None

    # Timestamps
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    updated_at: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        """Initialize step states for standard workflow steps"""
        if self.step_states is None:
            self.step_states = {
                "Initial Translation": "waiting",
                "Editor Review": "waiting",
                "Translator Revision": "waiting",
            }

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "task_id": self.task_id,
            "status": self.status.value,
            "progress": self.progress,
            "current_step": self.current_step,
            "step_details": self.step_details,
            "step_progress": self.step_progress,
            "step_states": self.step_states,
            "message": self.message,
            "error": self.error,
            "result": self.result,
            "created_at": self.created_at.isoformat(),
            "started_at": (
                self.started_at.isoformat() if self.started_at else None
            ),
            "completed_at": (
                self.completed_at.isoformat() if self.completed_at else None
            ),
            "updated_at": self.updated_at.isoformat(),
        }

    def update_step(
        self,
        step_name: str,
        step_details: Dict[str, Any],
        step_percent: int = None,
        message: str = "",
        step_state: str = None,
    ):
        """Update current step information"""
        self.current_step = step_name
        self.step_details = step_details
        if step_percent is not None:
            self.step_progress = self.step_progress or {}
            self.step_progress[step_name] = step_percent
        if step_state:
            self.step_states = self.step_states or {}
            self.step_states[step_name] = step_state
        if message:
            self.message = message
        self.updated_at = datetime.now()

    def set_progress(self, progress: int, message: str = ""):
        """Set overall progress percentage"""
        self.progress = max(0, min(100, progress))
        if message:
            self.message = message
        self.updated_at = datetime.now()

    def set_running(self, message: str = "Task started"):
        """Mark task as running"""
        self.status = TaskStatusEnum.RUNNING
        self.started_at = datetime.now()
        if message:
            self.message = message
        self.updated_at = datetime.now()

    def set_completed(
        self,
        result: Optional[Dict[str, Any]] = None,
        message: str = "Task completed successfully",
    ):
        """Mark task as completed"""
        self.status = TaskStatusEnum.COMPLETED
        self.progress = 100
        self.completed_at = datetime.now()
        self.result = result
        if message:
            self.message = message
        self.updated_at = datetime.now()

    def set_failed(self, error: str, message: str = "Task failed"):
        """Mark task as failed"""
        self.status = TaskStatusEnum.FAILED
        self.completed_at = datetime.now()
        self.error = error
        if message:
            self.message = message
        self.updated_at = datetime.now()


@dataclass
class WorkflowStep:
    """Individual workflow step information"""

    name: str
    status: str  # "pending", "in_progress", "completed", "failed"
    provider: Optional[str] = None
    model: Optional[str] = None
    temperature: Optional[float] = None
    message: str = ""
    details: Dict[str, Any] = field(default_factory=dict)
    progress_percent: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "name": self.name,
            "status": self.status,
            "provider": self.provider,
            "model": self.model,
            "temperature": self.temperature,
            "message": self.message,
            "details": self.details,
            "progress_percent": self.progress_percent,
        }
