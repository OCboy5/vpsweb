"""
Workflow Launch Service for VPSWeb v0.4.0

This service previously handled workflow execution integration with database-backed
WorkflowTask management. As of v0.4.0, workflow task tracking has been simplified
to use FastAPI's app.state for in-memory storage, eliminating database complexity
for this personal use system.

The VPSWeb workflow execution is now handled directly by:
- vpsweb.webui.services.vpsweb_adapter.py - Background task execution with app.state tracking
- vpsweb.webui.task_models.py - Enhanced TaskStatus dataclass for in-memory tracking
- vpsweb.webui.main.py - SSE endpoints for real-time progress streaming

This file is retained for reference but no longer used in the main application flow.
"""

# This service has been deprecated in favor of app.state-based task tracking
# All workflow execution is now handled directly by the VPSWebAdapter service
# with real-time progress reporting via Server-Sent Events (SSE)
