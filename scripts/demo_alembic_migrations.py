#!/usr/bin/env python3
"""
Alembic Migration Demonstration Script

This script demonstrates how to use Alembic for database migrations
in the VPSWeb repository system. It shows best practices for creating,
applying, and managing database schema changes.

Usage:
    python scripts/demo_alembic_migrations.py [--action ACTION]

Actions:
    demo     - Run full migration demonstration (default)
    create   - Create a new sample migration
    upgrade  - Upgrade database to latest version
    downgrade - Downgrade database by one version
    history  - Show migration history
    current  - Show current migration version
"""

import argparse
import asyncio
import os
import subprocess
import sys
from pathlib import Path
from typing import List, Optional

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from src.vpsweb.repository.settings import settings
from src.vpsweb.utils.logger import get_logger

logger = get_logger(__name__)


class AlembicDemo:
    """Demonstration class for Alembic migrations."""

    def __init__(self, database_url: str = settings.database_url):
        self.database_url = database_url
        self.alembic_dir = Path("src/vpsweb/repository/migrations")
        self.versions_dir = self.alembic_dir / "versions"

    async def run_demo(self) -> None:
        """Run the complete Alembic migration demonstration."""
        print("=" * 70)
        print("🚀 VPSWeb Alembic Migration Demonstration")
        print("=" * 70)
        print()

        # Step 1: Show current migration status
        await self.show_current_status()

        # Step 2: Show migration history
        await self.show_migration_history()

        # Step 3: Create a sample migration (demonstration only)
        print("📝 Step 3: Creating Sample Migration (Demo)")
        await self.create_sample_migration()
        print()

        # Step 4: Demonstrate upgrade process
        print("⬆️  Step 4: Demonstrating Migration Upgrade")
        await self.upgrade_database()
        print()

        # Step 5: Show database schema after migration
        await self.show_database_schema()

        # Step 6: Demonstrate downgrade process
        print("⬇️  Step 6: Demonstrating Migration Downgrade")
        await self.downgrade_database()
        print()

        print("=" * 70)
        print("✅ Alembic Migration Demo Complete!")
        print("=" * 70)
        print()
        print("Key Takeaways:")
        print("• Alembic provides version control for your database schema")
        print("• Always review migrations before applying them")
        print("• Test migrations on development databases first")
        print("• Keep migration descriptions clear and informative")
        print("• Use meaningful revision IDs for tracking")

    async def show_current_status(self) -> None:
        """Show the current migration status."""
        print("📊 Step 1: Current Migration Status")
        print("-" * 40)

        try:
            # Check if alembic_version table exists
            engine = create_async_engine(self.database_url)
            async with engine.begin() as conn:
                try:
                    result = await conn.execute(text(
                        "SELECT version_num FROM alembic_version"
                    ))
                    current_version = result.scalar()
                    print(f"Current Migration: {current_version}")
                except Exception:
                    print("No migrations applied yet (alembic_version table missing)")

                # Show tables in database
                result = await conn.execute(text(
                    "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
                ))
                tables = [row[0] for row in result.fetchall()]
                print(f"Database Tables: {len(tables)}")
                for table in tables:
                    print(f"  • {table}")

            await engine.dispose()

        except Exception as e:
            print(f"Error checking status: {e}")

        print()

    async def show_migration_history(self) -> None:
        """Show the migration history."""
        print("📚 Step 2: Migration History")
        print("-" * 40)

        try:
            # Use alembic to show history
            result = subprocess.run(
                ["alembic", "history", "--verbose"],
                cwd="src/vpsweb/repository",
                capture_output=True,
                text=True
            )

            if result.returncode == 0:
                print(result.stdout)
            else:
                print("Error getting migration history:")
                print(result.stderr)

        except Exception as e:
            print(f"Error getting history: {e}")

        print()

    async def create_sample_migration(self) -> None:
        """Create a sample migration for demonstration."""
        print("Creating sample migration file...")

        try:
            # Generate a new migration file
            result = subprocess.run([
                "alembic", "revision", "--autogenerate",
                "-m", "demo_add_poem_metadata_field"
            ], cwd="src/vpsweb/repository", capture_output=True, text=True)

            if result.returncode == 0:
                print("✅ Sample migration created successfully!")
                print("Migration file created:")

                # Find the new migration file
                migration_files = list(self.versions_dir.glob("*demo_add_poem_metadata_field*"))
                if migration_files:
                    latest_file = migration_files[0]
                    print(f"  📄 {latest_file.name}")

                    # Show the migration content
                    print("\nMigration Content (Preview):")
                    print("-" * 30)
                    with open(latest_file, 'r') as f:
                        lines = f.readlines()
                        for i, line in enumerate(lines[:20]):  # Show first 20 lines
                            print(f"{i+1:2d}: {line.rstrip()}")
                        if len(lines) > 20:
                            print(f"... ({len(lines) - 20} more lines)")

                    # Remove the demo migration file (it's just for demonstration)
                    os.remove(latest_file)
                    print(f"\n🗑️  Demo migration file removed (was just for demonstration)")

            else:
                print("❌ Error creating migration:")
                print(result.stderr)

        except Exception as e:
            print(f"Error creating migration: {e}")

    async def upgrade_database(self) -> None:
        """Demonstrate database upgrade."""
        print("Upgrading database to latest migration...")

        try:
            result = subprocess.run(
                ["alembic", "upgrade", "head"],
                cwd="src/vpsweb/repository",
                capture_output=True,
                text=True
            )

            if result.returncode == 0:
                print("✅ Database upgraded successfully!")
                if result.stdout.strip():
                    print("Output:", result.stdout)
            else:
                print("❌ Error upgrading database:")
                print(result.stderr)

        except Exception as e:
            print(f"Error upgrading: {e}")

    async def downgrade_database(self) -> None:
        """Demonstrate database downgrade."""
        print("Downgrading database by one version...")

        try:
            result = subprocess.run(
                ["alembic", "downgrade", "-1"],
                cwd="src/vpsweb/repository",
                capture_output=True,
                text=True
            )

            if result.returncode == 0:
                print("✅ Database downgraded successfully!")
                if result.stdout.strip():
                    print("Output:", result.stdout)
            else:
                print("❌ Error downgrading database:")
                print(result.stderr)

        except Exception as e:
            print(f"Error downgrading: {e}")

    async def show_database_schema(self) -> None:
        """Show the current database schema."""
        print("🏗️  Database Schema After Migration")
        print("-" * 40)

        try:
            engine = create_async_engine(self.database_url)
            async with engine.begin() as conn:
                # Show table schemas
                tables = ["poems", "translations", "ai_logs", "human_notes", "workflow_tasks"]

                for table in tables:
                    print(f"\n📋 Table: {table.upper()}")
                    try:
                        result = await conn.execute(text(f"PRAGMA table_info({table})"))
                        columns = result.fetchall()

                        print("Columns:")
                        for col in columns:
                            cid, name, type_name, not_null, default_val, pk = col
                            pk_mark = " (PK)" if pk else ""
                            null_mark = " NOT NULL" if not_null else ""
                            default_mark = f" DEFAULT {default_val}" if default_val else ""
                            print(f"  • {name}: {type_name}{null_mark}{default_mark}{pk_mark}")

                        # Show indexes
                        result = await conn.execute(text(
                            f"SELECT name, sql FROM sqlite_master "
                            f"WHERE type='index' AND tbl_name='{table}' "
                            f"AND name NOT LIKE 'sqlite_%' "
                            f"ORDER BY name"
                        ))
                        indexes = result.fetchall()

                        if indexes:
                            print("Indexes:")
                            for idx_name, idx_sql in indexes:
                                print(f"  • {idx_name}")

                    except Exception as e:
                        print(f"  Error getting schema for {table}: {e}")

            await engine.dispose()

        except Exception as e:
            print(f"Error showing schema: {e}")

        print()

    async def create_migration(self, message: str) -> str:
        """Create a new migration with the given message."""
        try:
            result = subprocess.run([
                "alembic", "revision", "--autogenerate", "-m", message
            ], cwd="src/vpsweb/repository", capture_output=True, text=True)

            if result.returncode == 0:
                print(f"✅ Migration created: {message}")
                return result.stdout
            else:
                print(f"❌ Error creating migration: {result.stderr}")
                return ""

        except Exception as e:
            print(f"Error creating migration: {e}")
            return ""

    async def upgrade_to_head(self) -> None:
        """Upgrade database to the latest migration."""
        try:
            result = subprocess.run(
                ["alembic", "upgrade", "head"],
                cwd="src/vpsweb/repository",
                capture_output=True,
                text=True
            )

            if result.returncode == 0:
                print("✅ Upgraded to latest migration")
            else:
                print(f"❌ Error upgrading: {result.stderr}")

        except Exception as e:
            print(f"Error upgrading: {e}")

    async def downgrade_to_base(self) -> None:
        """Downgrade database to base version."""
        try:
            result = subprocess.run(
                ["alembic", "downgrade", "base"],
                cwd="src/vpsweb/repository",
                capture_output=True,
                text=True
            )

            if result.returncode == 0:
                print("✅ Downgraded to base migration")
            else:
                print(f"❌ Error downgrading: {result.stderr}")

        except Exception as e:
            print(f"Error downgrading: {e}")


async def main():
    """Main function to run the Alembic demonstration."""
    parser = argparse.ArgumentParser(
        description="Alembic Migration Demonstration for VPSWeb"
    )
    parser.add_argument(
        "--action",
        choices=["demo", "create", "upgrade", "downgrade", "history", "current"],
        default="demo",
        help="Action to perform (default: demo)"
    )
    parser.add_argument(
        "--message",
        type=str,
        help="Migration message (used with create action)"
    )

    args = parser.parse_args()

    demo = AlembicDemo()

    if args.action == "demo":
        await demo.run_demo()
    elif args.action == "create":
        if not args.message:
            print("❌ Migration message required for create action")
            print("Usage: python demo_alembic_migrations.py --action create --message 'your message'")
            return
        await demo.create_migration(args.message)
    elif args.action == "upgrade":
        await demo.upgrade_to_head()
    elif args.action == "downgrade":
        await demo.downgrade_to_base()
    elif args.action == "history":
        await demo.show_migration_history()
    elif args.action == "current":
        await demo.show_current_status()


if __name__ == "__main__":
    asyncio.run(main())