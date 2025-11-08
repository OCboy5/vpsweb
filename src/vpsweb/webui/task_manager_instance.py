"""
Global task manager instance for translation tasks.
This module provides a singleton instance that can be imported across the application.
"""

from .sse_real import TranslationTaskManager

# Global instance
_task_manager = None

def get_task_manager() -> TranslationTaskManager:
    """Get the global task manager instance."""
    global _task_manager
    if _task_manager is None:
        _task_manager = TranslationTaskManager()
    return _task_manager

def reset_task_manager():
    """Reset the global task manager (mainly for testing)."""
    global _task_manager
    _task_manager = None