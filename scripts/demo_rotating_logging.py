#!/usr/bin/env python3
"""
Rotating File Logging Demonstration Script

This script demonstrates the rotating file logging capabilities
in VPSWeb, including both size-based and time-based rotation.

Usage:
    python scripts/demo_rotating_logging.py [--mode MODE]

Modes:
    demo     - Run complete logging demonstration (default)
    test     - Generate test log entries to demonstrate rotation
    status   - Show current logging configuration and log files
    cleanup  - Clean up old log files
"""

import argparse
import asyncio
import logging
import logging.handlers
import os
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from src.vpsweb.utils.logger import (
    setup_logging, get_logger, get_log_file_info, is_logging_initialized
)
from src.vpsweb.models.config import LoggingConfig, LogLevel


class RotatingLogDemo:
    """Demonstration class for rotating file logging."""

    def __init__(self, log_dir: str = "logs"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)

    async def run_demo(self) -> None:
        """Run the complete rotating logging demonstration."""
        print("=" * 70)
        print("📊 VPSWeb Rotating File Logging Demonstration")
        print("=" * 70)
        print()

        # Step 1: Show current logging configuration
        await self.show_logging_status()

        # Step 2: Demonstrate size-based rotation
        print("🔄 Step 2: Size-Based Rotation Demo")
        await self.demo_size_based_rotation()
        print()

        # Step 3: Demonstrate time-based rotation
        print("⏰ Step 3: Time-Based Rotation Demo")
        await self.demo_time_based_rotation()
        print()

        # Step 4: Show log file management
        print("📁 Step 4: Log File Management")
        await self.show_log_file_management()
        print()

        # Step 5: Demonstrate log levels
        print("📈 Step 5: Log Level Filtering Demo")
        await self.demo_log_levels()
        print()

        # Step 6: Show structured logging
        print("🏗️  Step 6: Structured Logging Demo")
        await self.demo_structured_logging()
        print()

        print("=" * 70)
        print("✅ Rotating Logging Demo Complete!")
        print("=" * 70)
        print()
        print("Key Features Demonstrated:")
        print("• Size-based log rotation (when file reaches max size)")
        print("• Time-based log rotation (daily/hourly)")
        print("• Configurable backup retention")
        print("• Structured logging with context")
        print("• Log level filtering")
        print("• Automatic log directory management")

    async def show_logging_status(self) -> None:
        """Show current logging configuration and status."""
        print("📊 Step 1: Current Logging Configuration")
        print("-" * 40)

        # Check if logging is initialized
        if is_logging_initialized():
            print("✅ Logging system is initialized")
        else:
            print("❌ Logging system not initialized")
            await self.initialize_logging()

        # Get log file information
        log_info = get_log_file_info()
        if log_info:
            print(f"Log file: {log_info['file_path']}")
            print(f"Current size: {log_info['file_size']:,} bytes")
            print(f"Max size: {log_info['max_size']:,} bytes")
            print(f"Backup count: {log_info['backup_count']}")
            print(f"Encoding: {log_info['encoding']}")
        else:
            print("No file logging configured")

        # Show existing log files
        await self.show_existing_log_files()

    async def show_existing_log_files(self) -> None:
        """Show existing log files in the log directory."""
        if self.log_dir.exists():
            log_files = list(self.log_dir.glob("*.log*"))
            if log_files:
                print(f"\n📁 Log files in {self.log_dir}:")
                for log_file in sorted(log_files):
                    stat = log_file.stat()
                    size_mb = stat.st_size / (1024 * 1024)
                    modified = datetime.fromtimestamp(stat.st_mtime)
                    print(f"  • {log_file.name} ({size_mb:.2f}MB, modified {modified.strftime('%Y-%m-%d %H:%M')})")
            else:
                print(f"\n📁 No log files found in {self.log_dir}")
        else:
            print(f"\n📁 Log directory {self.log_dir} does not exist")

    async def initialize_logging(self) -> None:
        """Initialize the logging system."""
        print("Initializing logging system...")

        # Create a comprehensive logging configuration
        log_config = LoggingConfig(
            level=LogLevel.INFO,
            format="%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s",
            file="logs/vpsweb_demo.log",
            max_file_size=1024 * 1024,  # 1MB for demo
            backup_count=3,
        )

        setup_logging(log_config)

    async def demo_size_based_rotation(self) -> None:
        """Demonstrate size-based log rotation."""
        print("Generating log entries to demonstrate size-based rotation...")

        if not is_logging_initialized():
            await self.initialize_logging()

        logger = get_logger("vpsweb.demo.size_rotation")

        # Generate enough log entries to potentially trigger rotation
        for i in range(50):
            logger.info(f"Size-based rotation test entry #{i+1}: " +
                       "This is a longer log message to help demonstrate how the log file grows and eventually rotates when it reaches the maximum size limit.")

            if i % 10 == 0:
                logger.warning(f"Warning message #{i//10 + 1}: This warning demonstrates different log levels in the rotating file system.")

        logger.info("Size-based rotation demo completed. Check log files for rotation.")

        # Show current log file status
        log_info = get_log_file_info()
        if log_info:
            print(f"  Current log file size: {log_info['file_size']:,} bytes")
            print(f"  Size limit: {log_info['max_size']:,} bytes")
            print(f"  Utilization: {(log_info['file_size']/log_info['max_size']*100):.1f}%")

    async def demo_time_based_rotation(self) -> None:
        """Demonstrate time-based log rotation."""
        print("Setting up time-based logging rotation...")

        # Create a time-based rotating handler
        time_based_handler = logging.handlers.TimedRotatingFileHandler(
            filename=self.log_dir / "vpsweb_timed.log",
            when="midnight",  # Rotate at midnight
            interval=1,  # Every day
            backupCount=7,  # Keep 7 days of backups
            encoding="utf-8",
        )

        # Set up formatter
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        time_based_handler.setFormatter(formatter)

        # Get logger and add handler
        logger = get_logger("vpsweb.demo.time_rotation")
        logger.addHandler(time_based_handler)

        # Generate some log entries
        logger.info("Time-based rotation logging initialized")
        logger.info("This log file will rotate at midnight")
        logger.info("Backups will be kept for 7 days")

        # Show rotation schedule
        now = datetime.now()
        next_rotation = now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
        print(f"  Next rotation: {next_rotation.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"  Backup retention: 7 days")
        print(f"  Log file: {self.log_dir}/vpsweb_timed.log")

        # Remove the handler after demo
        logger.removeHandler(time_based_handler)

    async def demo_log_levels(self) -> None:
        """Demonstrate different log levels."""
        print("Demonstrating different log levels...")

        logger = get_logger("vpsweb.demo.log_levels")

        logger.debug("This is a DEBUG message - detailed information for troubleshooting")
        logger.info("This is an INFO message - general application information")
        logger.warning("This is a WARNING message - something unexpected but not fatal")
        logger.error("This is an ERROR message - something went wrong")
        logger.critical("This is a CRITICAL message - serious error occurred")

        print("  ✓ Log levels demonstrated. Check log file for output.")

    async def demo_structured_logging(self) -> None:
        """Demonstrate structured logging with context."""
        print("Demonstrating structured logging with context...")

        logger = get_logger("vpsweb.demo.structured")

        # Simulate different application events
        events = [
            ("workflow_start", {
                "workflow_id": "demo-workflow-001",
                "source_lang": "English",
                "target_lang": "Chinese",
                "poem_length": 156,
                "user_id": "demo-user",
            }),
            ("api_call", {
                "provider": "tongyi",
                "model": "qwen-max",
                "prompt_length": 89,
                "response_length": 245,
                "tokens_used": 334,
                "duration_ms": 1250,
            }),
            ("workflow_complete", {
                "workflow_id": "demo-workflow-001",
                "total_tokens": 1250,
                "total_duration": 15.7,
                "success": True,
            }),
        ]

        for event_name, context in events:
            # Create structured log message
            context_str = " | ".join(f"{k}={v}" for k, v in context.items())
            logger.info(f"Event: {event_name} | {context_str}")

        print("  ✓ Structured logging demonstrated with contextual information.")

    async def show_log_file_management(self) -> None:
        """Show log file management features."""
        print("Log file management features...")

        # Show log directory contents
        await self.show_existing_log_files()

        # Demonstrate log file cleanup (if requested)
        print("\nLog file management commands:")
        print("  • python scripts/demo_rotating_logging.py --mode cleanup  # Clean old logs")
        print("  • python scripts/demo_rotating_logging.py --mode status    # Show status")

        # Show log rotation configuration
        log_info = get_log_file_info()
        if log_info:
            print(f"\nCurrent rotation settings:")
            print(f"  • Max file size: {log_info['max_size'] / (1024*1024):.1f}MB")
            print(f"  • Backup files: {log_info['backup_count']}")
            print(f"  • Encoding: {log_info['encoding']}")

    async def generate_test_logs(self, count: int = 100) -> None:
        """Generate test log entries."""
        print(f"Generating {count} test log entries...")

        if not is_logging_initialized():
            await self.initialize_logging()

        logger = get_logger("vpsweb.demo.test")

        for i in range(count):
            # Mix different log levels
            if i % 20 == 0:
                logger.warning(f"Periodic warning #{i//20 + 1}")
            elif i % 50 == 0:
                logger.error(f"Error simulation #{i//50 + 1}")
            else:
                logger.info(f"Test log entry #{i+1}: Application running normally, processing request {i+1}")

        print(f"✅ Generated {count} test log entries")

    async def cleanup_old_logs(self, days: int = 7) -> None:
        """Clean up old log files."""
        print(f"Cleaning up log files older than {days} days...")

        if not self.log_dir.exists():
            print(f"Log directory {self.log_dir} does not exist")
            return

        cutoff_date = datetime.now() - timedelta(days=days)
        cleaned_files = []

        for log_file in self.log_dir.glob("*.log*"):
            if log_file.is_file():
                file_time = datetime.fromtimestamp(log_file.stat().st_mtime)
                if file_time < cutoff_date:
                    try:
                        log_file.unlink()
                        cleaned_files.append(log_file.name)
                    except Exception as e:
                        print(f"Error deleting {log_file.name}: {e}")

        if cleaned_files:
            print(f"✅ Cleaned up {len(cleaned_files)} old log files:")
            for filename in cleaned_files:
                print(f"  • {filename}")
        else:
            print("✅ No old log files to clean up")

    async def show_detailed_status(self) -> None:
        """Show detailed logging status."""
        print("📊 Detailed Logging System Status")
        print("-" * 40)

        # System status
        print(f"Logging initialized: {'Yes' if is_logging_initialized() else 'No'}")

        if is_logging_initialized():
            # Root logger info
            root_logger = logging.getLogger()
            print(f"Root logger level: {logging.getLevelName(root_logger.level)}")
            print(f"Handlers: {len(root_logger.handlers)}")

            for i, handler in enumerate(root_logger.handlers, 1):
                handler_type = type(handler).__name__
                print(f"  Handler {i}: {handler_type}")
                if hasattr(handler, 'baseFilename'):
                    print(f"    File: {handler.baseFilename}")
                if hasattr(handler, 'level'):
                    print(f"    Level: {logging.getLevelName(handler.level)}")

            # Log file info
            log_info = get_log_file_info()
            if log_info:
                print(f"\n📁 Log File Information:")
                print(f"  Path: {log_info['file_path']}")
                print(f"  Size: {log_info['file_size']:,} bytes ({log_info['file_size']/1024:.1f}KB)")
                print(f"  Max Size: {log_info['max_size']:,} bytes ({log_info['max_size']/(1024*1024):.1f}MB)")
                print(f"  Backup Count: {log_info['backup_count']}")
                print(f"  Encoding: {log_info['encoding']}")

                # Check backup files
                log_file = Path(log_info['file_path'])
                if log_file.exists():
                    backup_files = list(log_file.parent.glob(f"{log_file.stem}.*"))
                    print(f"  Total Files: {len(backup_files)} (main + backups)")

        await self.show_existing_log_files()


async def main():
    """Main function to run the rotating logging demonstration."""
    parser = argparse.ArgumentParser(
        description="Rotating File Logging Demonstration for VPSWeb"
    )
    parser.add_argument(
        "--mode",
        choices=["demo", "test", "status", "cleanup"],
        default="demo",
        help="Action to perform (default: demo)"
    )
    parser.add_argument(
        "--count",
        type=int,
        default=100,
        help="Number of test log entries to generate (for test mode)"
    )
    parser.add_argument(
        "--days",
        type=int,
        default=7,
        help="Number of days to keep log files (for cleanup mode)"
    )

    args = parser.parse_args()

    demo = RotatingLogDemo()

    if args.mode == "demo":
        await demo.run_demo()
    elif args.mode == "test":
        await demo.generate_test_logs(args.count)
    elif args.mode == "status":
        await demo.show_detailed_status()
    elif args.mode == "cleanup":
        await demo.cleanup_old_logs(args.days)


if __name__ == "__main__":
    asyncio.run(main())