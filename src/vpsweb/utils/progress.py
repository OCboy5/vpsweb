"""
Progress tracking and display utilities for VPSWeb workflow.

This module provides simple CLI progress display with step-by-step results.
"""

import time
import logging
from typing import Dict, Any, Optional, Callable
from enum import Enum
from dataclasses import dataclass

logger = logging.getLogger(__name__)


class StepStatus(Enum):
    """Step status enumeration."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class StepProgress:
    """Progress information for a single step."""

    name: str
    status: StepStatus
    display_name: str
    result: Optional[Dict[str, Any]] = None
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    error: Optional[str] = None

    @property
    def duration(self) -> float:
        """Calculate step duration in seconds."""
        if self.start_time and self.end_time:
            return self.end_time - self.start_time
        return 0.0


class ProgressTracker:
    """Simple progress tracker for workflow execution."""

    def __init__(self, steps: list):
        """
        Initialize progress tracker with workflow steps.

        Args:
            steps: List of step names in execution order
        """
        self.steps = {
            step: StepProgress(
                name=step,
                status=StepStatus.PENDING,
                display_name=self._format_display_name(step),
            )
            for step in steps
        }
        self.step_order = steps
        self.display_callback: Optional[Callable] = None

    def _format_display_name(self, step_name: str) -> str:
        """Convert step name to display format."""
        return step_name.replace("_", " ").title()

    def _get_status_icon(self, status: StepStatus) -> str:
        """Get icon for step status."""
        icons = {
            StepStatus.PENDING: "⏸️",
            StepStatus.IN_PROGRESS: "⏳",
            StepStatus.COMPLETED: "✅",
            StepStatus.FAILED: "❌",
        }
        return icons.get(status, "❓")

    def _format_step_line(self, step_name: str) -> str:
        """Format a single step line for display."""
        step = self.steps[step_name]
        icon = self._get_status_icon(step.status)
        base_line = f"  Step {self.step_order.index(step_name) + 1}: {step.display_name}... {icon} {step.status.value.replace('_', ' ').title()}"

        # Add model info for in-progress steps
        if (
            step.status == StepStatus.IN_PROGRESS
            and step.result
            and "model_info" in step.result
        ):
            model_info = step.result["model_info"]
            provider = model_info.get("provider", "Unknown")
            model = model_info.get("model", "Unknown")
            temp = model_info.get("temperature", "Unknown")
            # Determine if reasoning model
            is_reasoning = model.lower() in [
                "deepseek-reasoner",
                "o1",
                "o1-mini",
                "o3-mini",
            ]
            model_type = "Reasoning" if is_reasoning else "Non-Reasoning"

            # Add model info on next line with indentation
            model_line = f"      🤖 Provider: {provider.title()} | 🧠 Model: {model} | 🌡️ Temp: {temp} | ⚡ {model_type}"
            return base_line + "\n" + model_line

        return base_line

    def start_step(
        self, step_name: str, model_info: Optional[Dict[str, Any]] = None
    ) -> None:
        """Mark a step as in progress."""
        if step_name in self.steps:
            self.steps[step_name].status = StepStatus.IN_PROGRESS
            self.steps[step_name].start_time = time.time()
            # Store model info for this step
            if model_info:
                self.steps[step_name].result = {"model_info": model_info}
            self._update_display()

    def complete_step(self, step_name: str, result: Dict[str, Any]) -> None:
        """Mark a step as completed with results."""
        if step_name in self.steps:
            self.steps[step_name].status = StepStatus.COMPLETED
            self.steps[step_name].end_time = time.time()
            self.steps[step_name].result = result
            self._update_display()
            self._display_step_result(step_name)

    def fail_step(self, step_name: str, error: str) -> None:
        """Mark a step as failed with error message."""
        if step_name in self.steps:
            self.steps[step_name].status = StepStatus.FAILED
            self.steps[step_name].end_time = time.time()
            self.steps[step_name].error = error
            self._update_display()
            print(f"\n  ❌ Step failed: {error}")

    def _update_display(self) -> None:
        """Update the progress display."""
        print("\n🎭 Poetry Translation Progress")
        print("=" * 50)

        # Find current step (in progress or failed)
        current_step = None
        completed_steps = []
        upcoming_steps = []

        for step_name in self.step_order:
            step = self.steps[step_name]
            if (
                step.status == StepStatus.IN_PROGRESS
                or step.status == StepStatus.FAILED
            ):
                current_step = step_name
            elif step.status == StepStatus.COMPLETED:
                completed_steps.append(step_name)
            else:  # PENDING
                upcoming_steps.append(step_name)

        # Show all steps in order
        for step_name in self.step_order:
            if step_name in completed_steps:
                # Show completed steps
                print(self._format_step_line(step_name))
            elif step_name == current_step:
                # Show current step with model info
                print(self._format_step_line(step_name))
            elif step_name in upcoming_steps:
                # Show upcoming steps
                print(self._format_step_line(step_name))

        print()  # Add spacing

    def _display_step_result(self, step_name: str) -> None:
        """Display results for a completed step."""
        step = self.steps[step_name]
        result = step.result

        if not result:
            return

        print(f"\n📝 {step.display_name} Results:")
        print("-" * 30)

        if step_name == "initial_translation":
            self._display_initial_translation(result)
        elif step_name == "editor_review":
            self._display_editor_review(result)
        elif step_name == "translator_revision":
            self._display_translator_revision(result)
        else:
            # Generic display
            for key, value in result.items():
                if value:
                    print(f"  {key.replace('_', ' ').title()}: {value}")

        print("-" * 30)

    def _display_model_info(self, result: Dict[str, Any]) -> None:
        """Display model configuration information."""
        if "model_info" in result:
            model_info = result["model_info"]
            provider = model_info.get("provider", "Unknown")
            model = model_info.get("model", "Unknown")
            temp = model_info.get("temperature", "Unknown")

            # Determine if reasoning model
            is_reasoning = model.lower() in [
                "deepseek-reasoner",
                "o1",
                "o1-mini",
                "o3-mini",
            ]
            model_type = "Reasoning" if is_reasoning else "Non-Reasoning"

            print(f"  🤖 Model Provider: {provider.title()}")
            print(f"  🧠 Model Name: {model}")
            print(f"  🌡️  Temperature: {temp}")
            print(f"  ⚡ Type: {model_type}")

    def _display_initial_translation(self, result: Dict[str, Any]) -> None:
        """Display initial translation results."""
        self._display_model_info(result)

        # Display token breakdown like WeChat workflow
        tokens_used = result.get("tokens_used", "N/A")
        prompt_tokens = result.get("prompt_tokens", "N/A")
        completion_tokens = result.get("completion_tokens", "N/A")

        print(f"  🧮 Tokens Used: {tokens_used}")
        if prompt_tokens != "N/A" and completion_tokens != "N/A":
            print(f"      ⬇️ Prompt: {prompt_tokens}")
            print(f"      ⬆️ Completion: {completion_tokens}")

        if result.get("duration"):
            print(f"  ⏱️  Time Spent: {result['duration']:.2f}s")
        if result.get("cost"):
            print(f"  💰 Cost: ¥{result['cost']:.6f}")
        # Show a preview of the translation (first 100 chars)
        translation = result.get("initial_translation", "N/A")
        if translation != "N/A" and len(translation) > 100:
            translation = translation[:100] + "..."
        print(f"  📝 Translation Preview: {translation}")

    def _display_editor_review(self, result: Dict[str, Any]) -> None:
        """Display editor review results."""
        self._display_model_info(result)

        # Display token breakdown like WeChat workflow
        tokens_used = result.get("tokens_used", "N/A")
        prompt_tokens = result.get("prompt_tokens", "N/A")
        completion_tokens = result.get("completion_tokens", "N/A")

        print(f"  🧮 Tokens Used: {tokens_used}")
        if prompt_tokens != "N/A" and completion_tokens != "N/A":
            print(f"      ⬇️ Prompt: {prompt_tokens}")
            print(f"      ⬆️ Completion: {completion_tokens}")

        if result.get("duration"):
            print(f"  ⏱️  Time Spent: {result['duration']:.2f}s")
        if result.get("cost"):
            print(f"  💰 Cost: ¥{result['cost']:.6f}")

        # Count editor suggestions more accurately
        suggestions = result.get("editor_suggestions", "")
        if suggestions:
            # Count lines that start with numbers (1., 2., 3., etc.)
            suggestion_count = len(
                [
                    line
                    for line in suggestions.split("\n")
                    if line.strip() and line.strip()[0].isdigit()
                ]
            )
            print(f"  📋 Editor Suggestions: {suggestion_count}")

            # Show first 2-3 suggestions as preview
            suggestion_lines = [
                line
                for line in suggestions.split("\n")
                if line.strip() and line.strip()[0].isdigit()
            ]
            if suggestion_lines:
                print(f"  💬 Sample Suggestions:")
                for i, line in enumerate(suggestion_lines[:3]):  # Show first 3
                    print(f"     {line.strip()}")
                if len(suggestion_lines) > 3:
                    print(f"     ... and {len(suggestion_lines) - 3} more")
        else:
            print(f"  📋 Editor Suggestions: 0")

    def _display_translator_revision(self, result: Dict[str, Any]) -> None:
        """Display translator revision results."""
        self._display_model_info(result)

        # Display token breakdown like WeChat workflow
        tokens_used = result.get("tokens_used", "N/A")
        prompt_tokens = result.get("prompt_tokens", "N/A")
        completion_tokens = result.get("completion_tokens", "N/A")

        print(f"  🧮 Tokens Used: {tokens_used}")
        if prompt_tokens != "N/A" and completion_tokens != "N/A":
            print(f"      ⬇️ Prompt: {prompt_tokens}")
            print(f"      ⬆️ Completion: {completion_tokens}")

        if result.get("duration"):
            print(f"  ⏱️  Time Spent: {result['duration']:.2f}s")
        if result.get("cost"):
            print(f"  💰 Cost: ¥{result['cost']:.6f}")
        # Show a preview of the revised translation (first 100 chars)
        revision = result.get("revised_translation", "N/A")
        if revision != "N/A" and len(revision) > 100:
            revision = revision[:100] + "..."
        print(f"  📝 Revision Preview: {revision}")

    def get_summary(self) -> Dict[str, Any]:
        """Get overall progress summary."""
        completed_steps = [
            s for s in self.steps.values() if s.status == StepStatus.COMPLETED
        ]
        total_duration = sum(s.duration for s in completed_steps)
        total_tokens = sum(
            s.result.get("tokens_used", 0) for s in completed_steps if s.result
        )

        return {
            "total_steps": len(self.step_order),
            "completed_steps": len(completed_steps),
            "total_duration": total_duration,
            "total_tokens": total_tokens,
        }


def create_progress_tracker(workflow_steps: list) -> ProgressTracker:
    """
    Create a progress tracker for the given workflow steps.

    Args:
        workflow_steps: List of workflow step names

    Returns:
        ProgressTracker instance
    """
    return ProgressTracker(workflow_steps)
