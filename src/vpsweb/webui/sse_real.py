"""
SSE (Server-Sent Events) module for real-time translation progress updates.

This module provides enhanced SSE functionality that connects to real translation tasks
and provides accurate progress updates based on the actual translation workflow state.
"""

import asyncio
import json
import time
from typing import Dict, Any, Optional
from fastapi import Request
from sse_starlette import EventSourceResponse


class TranslationTaskManager:
    """Manages translation task state for SSE streaming."""

    def __init__(self):
        self.tasks: Dict[str, Dict[str, Any]] = {}
        self.subscribers: Dict[str, asyncio.Queue] = {}
        self.task_retention_time = 300  # Keep completed tasks for 5 minutes

    def create_task(self, task_id: str, poem_id: str, target_lang: str, workflow_mode: str) -> Dict[str, Any]:
        """Create a new translation task."""
        task = {
            "task_id": task_id,
            "poem_id": poem_id,
            "target_lang": target_lang,
            "workflow_mode": workflow_mode,
            "status": "pending",
            "current_step": 0,
            "total_steps": 3,
            "progress": 0,
            "message": "Translation task created",
            "created_at": time.time(),
            "started_at": None,
            "completed_at": None,
            "steps": [
                "Initial Translation",
                "Editor Review",
                "Translator Revision"
            ]
        }
        self.tasks[task_id] = task
        return task

    def update_task_status(self, task_id: str, status: str, message: str = None, step: int = None):
        """Update task status and notify subscribers."""
        if task_id not in self.tasks:
            return

        task = self.tasks[task_id]
        old_status = task["status"]
        task["status"] = status
        if message:
            task["message"] = message
        if step is not None:
            task["current_step"] = step
            task["progress"] = int((step / task["total_steps"]) * 100)

        if status == "running" and not task["started_at"]:
            task["started_at"] = time.time()
        elif status == "completed":
            task["completed_at"] = time.time()
            task["progress"] = 100

        # Notify all subscribers on status change
        if old_status != status:
            if task_id in self.subscribers:
                asyncio.create_task(self._notify_subscribers(task_id))

    async def _notify_subscribers(self, task_id: str):
        """Notify all subscribers of task updates."""
        if task_id in self.subscribers:
            task = self.tasks[task_id]
            try:
                await self.subscribers[task_id].put(task)
            except Exception as e:
                print(f"Error notifying subscribers for task {task_id}: {e}")

    def subscribe(self, task_id: str) -> asyncio.Queue:
        """Subscribe to task updates."""
        if task_id not in self.subscribers:
            self.subscribers[task_id] = asyncio.Queue(maxsize=10)
        return self.subscribers[task_id]

    def unsubscribe(self, task_id: str):
        """Unsubscribe from task updates."""
        if task_id in self.subscribers:
            del self.subscribers[task_id]

    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get task status."""
        return self.tasks.get(task_id)

    def cleanup_expired_tasks(self):
        """Remove expired completed tasks."""
        current_time = time.time()
        expired_tasks = []
        for task_id, task in self.tasks.items():
            if (task["status"] == "completed" and
                task.get("completed_at") and
                current_time - task["completed_at"] > self.task_retention_time):
                expired_tasks.append(task_id)

        for task_id in expired_tasks:
            del self.tasks[task_id]
            if task_id in self.subscribers:
                del self.subscribers[task_id]


async def create_real_translation_events(request: Request, task_id: str, task_manager: TranslationTaskManager):
    """Create real translation progress events from actual task status."""
    try:
        # TODO: Temporarily disable cleanup to debug task retention issue
        # task_manager.cleanup_expired_tasks()

        # Debug: Print task manager info
        print(f"[SSE DEBUG] TaskManager ID: {id(task_manager)}, Tasks in manager: {list(task_manager.tasks.keys())}")
        print(f"[SSE DEBUG] Looking for task: {task_id}")

        # Check if task exists
        task = task_manager.get_task(task_id)
        if not task:
            yield {
                "event": "error",
                "data": json.dumps({
                    "task_id": task_id,
                    "message": "Task not found",
                    "timestamp": asyncio.get_event_loop().time()
                })
            }
            return

        # Subscribe to task updates
        queue = task_manager.subscribe(task_id)

        # Send initial connection event
        yield {
            "event": "connected",
            "data": json.dumps({
                "task_id": task_id,
                "message": f"Connected to translation progress stream for task {task_id}",
                "status": task["status"],
                "progress": task["progress"],
                "timestamp": asyncio.get_event_loop().time()
            })
        }

        # Send current task status
        yield {
            "event": "status",
            "data": json.dumps({
                "task_id": task_id,
                "status": task["status"],
                "current_step": task["current_step"],
                "total_steps": task["total_steps"],
                "progress": task["progress"],
                "message": task["message"],
                "timestamp": asyncio.get_event_loop().time()
            })
        }

        # If task is already completed, send completion event and exit
        if task["status"] == "completed":
            yield {
                "event": "completed",
                "data": json.dumps({
                    "task_id": task_id,
                    "message": "✅ Translation workflow completed successfully!",
                    "progress": 100,
                    "timestamp": asyncio.get_event_loop().time()
                })
            }
            return

        # Listen for task updates
        while True:
            # Check if client disconnected
            if await request.is_disconnected():
                print(f"Client disconnected from task {task_id}")
                break

            try:
                # Wait for task updates with timeout
                updated_task = await asyncio.wait_for(queue.get(), timeout=2.0)

                # Send update event based on task status
                if updated_task["status"] == "running":
                    # Send step start event for new step
                    if updated_task["current_step"] > 0 and updated_task["current_step"] <= len(updated_task["steps"]):
                        step_name = updated_task["steps"][updated_task["current_step"] - 1]
                        yield {
                            "event": "step_start",
                            "data": json.dumps({
                                "task_id": task_id,
                                "step": updated_task["current_step"],
                                "message": f"Step {updated_task['current_step']}/3: {step_name}",
                                "progress": updated_task["progress"],
                                "timestamp": asyncio.get_event_loop().time()
                            })
                        }

                elif updated_task["status"] == "completed":
                    # Send step complete event before completion
                    if updated_task["current_step"] > 0:
                        step_name = updated_task["steps"][updated_task["current_step"] - 1]
                        yield {
                            "event": "step_complete",
                            "data": json.dumps({
                                "task_id": task_id,
                                "step": updated_task["current_step"],
                                "message": f"Step {updated_task['current_step']}/3: {step_name} completed",
                                "progress": updated_task["progress"],
                                "timestamp": asyncio.get_event_loop().time()
                            })
                        }

                    # Send final status update
                    yield {
                        "event": "status",
                        "data": json.dumps({
                            "task_id": task_id,
                            "status": updated_task["status"],
                            "current_step": updated_task["current_step"],
                            "total_steps": updated_task["total_steps"],
                            "progress": updated_task["progress"],
                            "message": updated_task["message"],
                            "timestamp": asyncio.get_event_loop().time()
                        })
                    }

                    # Send completion event
                    yield {
                        "event": "completed",
                        "data": json.dumps({
                            "task_id": task_id,
                            "message": "✅ Translation workflow completed successfully!",
                            "progress": 100,
                            "timestamp": asyncio.get_event_loop().time()
                        })
                    }
                    # After completion, keep connection alive for a bit more for any late subscribers
                    continue

            except asyncio.TimeoutError:
                # Timeout occurred, check if task still exists and send heartbeat
                current_task = task_manager.get_task(task_id)
                if not current_task:
                    yield {
                        "event": "error",
                        "data": json.dumps({
                            "task_id": task_id,
                            "message": "Task disappeared",
                            "timestamp": asyncio.get_event_loop().time()
                        })
                    }
                    break

                # Send heartbeat to keep connection alive
                yield {
                    "event": "heartbeat",
                    "data": json.dumps({
                        "task_id": task_id,
                        "message": "Task status check",
                        "timestamp": asyncio.get_event_loop().time()
                    })
                }
                # Continue loop to check for disconnection

    except Exception as e:
        print(f"Error generating translation events for task {task_id}: {e}")
        yield {
            "event": "error",
            "data": json.dumps({
                "task_id": task_id,
                "message": f"Error: {str(e)}",
                "timestamp": asyncio.get_event_loop().time()
            })
        }
    finally:
        # Unsubscribe when done
        try:
            task_manager.unsubscribe(task_id)
        except:
            pass