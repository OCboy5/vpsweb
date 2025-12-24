# Alembic Migration Guide for VPSWeb

**Date**: 2025-10-19
**Version**: v0.3.1
**Purpose**: Complete guide to database migrations using Alembic

## 🎯 Overview

Alembic is a database migration tool for SQLAlchemy that provides version control for your database schema. This guide covers how to use Alembic effectively in the VPSWeb repository system.

## 📁 Migration File Structure

```
src/vpsweb/repository/migrations/
├── alembic.ini              # Alembic configuration file
├── env.py                   # Migration environment setup
├── script.py.mako           # Template for new migration files
├── README                   # Alembic documentation
└── versions/
    ├── 001_initial_schema.py
    ├── 94bcac9585c9_add_composite_indexes_for_performance_.py
    └── [future migrations].py
```

## 🚀 Quick Start

### 1. Install Dependencies

```bash
# Alembic is included in the project dependencies
poetry install
```

### 2. Run the Interactive Demo

```bash
# Run the comprehensive Alembic demonstration
python scripts/demo_alembic_migrations.py --action demo

# Show migration history
python scripts/demo_alembic_migrations.py --action history

# Check current migration status
python scripts/demo_alembic_migrations.py --action current
```

### 3. Basic Alembic Commands

```bash
# Navigate to repository directory
cd src/vpsweb/repository

# Create a new migration
alembic revision --autogenerate -m "add_new_field_to_table"

# Upgrade database to latest
alembic upgrade head

# Downgrade database by one version
alembic downgrade -1

# Show migration history
alembic history

# Show current version
alembic current

# Show SQL for migration (without executing)
alembic upgrade head --sql
```

## 📝 Creating Migrations

### Method 1: Autogenerate (Recommended)

```bash
cd src/vpsweb/repository

# Detect model changes and create migration
alembic revision --autogenerate -m "descriptive_message"
```

### Method 2: Manual Migration

```bash
cd src/vpsweb/repository

# Create empty migration file
alembic revision -m "manual_migration_message"
```

Then edit the generated file manually:

```python
"""Manual Migration Example

Revision ID: abc123def456
Revises: 94bcac9585c9
Create Date: 2025-10-19 20:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers
revision: str = 'abc123def456'
down_revision: Union[str, Sequence[str], None] = '94bcac9585c9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add new column
    op.add_column('poems', sa.Column('is_featured', sa.Boolean(), nullable=True))

    # Create index
    op.create_index('idx_poems_featured', 'poems', ['is_featured'])


def downgrade() -> None:
    """Downgrade schema."""
    # Remove index
    op.drop_index('idx_poems_featured', table_name='poems')

    # Remove column
    op.drop_column('poems', 'is_featured')
```

## 🔧 Common Migration Patterns

### Adding a New Column

```python
def upgrade() -> None:
    op.add_column('poems', sa.Column('word_count', sa.Integer(), nullable=True))

def downgrade() -> None:
    op.drop_column('poems', 'word_count')
```

### Creating an Index

```python
def upgrade() -> None:
    op.create_index('idx_poems_created_at', 'poems', ['created_at'])

def downgrade() -> None:
    op.drop_index('idx_poems_created_at', table_name='poems')
```

### Adding a New Table

```python
def upgrade() -> None:
    op.create_table('new_table',
        sa.Column('id', sa.String(length=26), nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )

def downgrade() -> None:
    op.drop_table('new_table')
```

### Modifying Column Type

```python
def upgrade() -> None:
    # SQLite doesn't support ALTER COLUMN directly
    # Use batch mode for SQLite
    with op.batch_alter_table('poems') as batch_op:
        batch_op.alter_column('title',
                            existing_type=sa.String(),
                            type_=sa.String(length=500))

def downgrade() -> None:
    with op.batch_alter_table('poems') as batch_op:
        batch_op.alter_column('title',
                            existing_type=sa.String(length=500),
                            type_=sa.String())
```

## 🏗️ Migration Best Practices

### 1. Descriptive Messages

```bash
# Good
alembic revision -m "add_poet_birth_year_to_poems_table"

# Bad
alembic revision -m "update"
```

### 2. Review Generated Migrations

Always review the generated migration file before applying:

```bash
# Generate and review
alembic revision --autogenerate -m "add_poet_lifespan"

# Review the file in src/vpsweb/repository/versions/

# Apply if correct
alembic upgrade head
```

### 3. Test Migrations

```bash
# Test on development database first
export DATABASE_URL="sqlite:///dev_test.db"
alembic upgrade head

# Generate SQL to review changes
alembic upgrade head --sql > migration_review.sql
```

### 4. Handle Data Migrations

```python
def upgrade() -> None:
    # Add new column first
    op.add_column('poems', sa.Column('word_count', sa.Integer(), nullable=True))

    # Migrate data
    connection = op.get_bind()
    connection.execute(
        "UPDATE poems SET word_count = LENGTH(original_text)"
    )

    # Make column non-nullable if needed
    with op.batch_alter_table('poems') as batch_op:
        batch_op.alter_column('word_count', nullable=False)
```

## 🔄 Workflow Integration

### Development Workflow

1. **Make Model Changes**
   ```python
   # src/vpsweb/repository/models.py
   class Poem(Base):
       # ... existing fields ...
       word_count = Column(Integer, nullable=True)
   ```

2. **Generate Migration**
   ```bash
   cd src/vpsweb/repository
   alembic revision --autogenerate -m "add_word_count_to_poems"
   ```

3. **Review and Apply**
   ```bash
   # Review the generated file
   alembic upgrade head
   ```

4. **Test Changes**
   ```bash
   python scripts/demo_alembic_migrations.py --action current
   ```

### Production Deployment

1. **Backup Database**
   ```bash
   ./scripts/backup.sh
   ```

2. **Review Migrations**
   ```bash
   # Check pending migrations
   alembic current
   alembic history
   ```

3. **Apply Migrations**
   ```bash
   # Apply in production
   alembic upgrade head
   ```

4. **Verify**
   ```bash
   # Check application health
   python scripts/demo_alembic_migrations.py --action current
   ```

## 🚨 Troubleshooting

### Common Issues

#### 1. Autogenerate Not Detecting Changes

**Problem**: Alembic doesn't detect model changes.

**Solution**: Ensure models are imported correctly in `env.py`:

```python
# src/vpsweb/repository/migrations/env.py
from vpsweb.repository.models import Base  # noqa
target_metadata = Base.metadata
```

#### 2. SQLite ALTER TABLE Limitations

**Problem**: SQLite doesn't support all ALTER TABLE operations.

**Solution**: Use batch mode:

```python
def upgrade() -> None:
    with op.batch_alter_table('poems') as batch_op:
        batch_op.alter_column('title', type_=sa.String(length=500))
```

#### 3. Migration Conflicts

**Problem**: Multiple developers create migrations with conflicting changes.

**Solution**:
- Communicate schema changes with the team
- Create a single comprehensive migration
- Consider using `--autogenerate` after merging changes

#### 4. Downgrade Issues

**Problem**: Migration can't be downgraded safely.

**Solution**: Ensure downgrade logic is implemented:

```python
def upgrade() -> None:
    op.add_column('poems', sa.Column('new_field', sa.String()))

def downgrade() -> None:
    op.drop_column('poems', 'new_field')  # Must be implemented!
```

### Debugging Commands

```bash
# Show migration plan without executing
alembic upgrade head --sql

# Check current migration state
alembic current

# Show detailed history
alembic history --verbose

# Check specific revision
alembic show <revision_id>
```

## 📊 Current Migrations

The VPSWeb repository currently includes these migrations:

1. **001_initial_schema.py** - Creates the initial database schema
   - Tables: poems, translations, ai_logs, human_notes, workflow_tasks
   - Basic indexes and constraints

2. **94bcac9585c9_add_composite_indexes_for_performance_.py** - Performance optimization
   - Adds 15 composite indexes for common query patterns
   - Optimizes queries for poet search, language filtering, and date sorting

## 🛠️ Advanced Usage

### Custom Migration Functions

```python
def upgrade() -> None:
    # Custom data processing
    connection = op.get_bind()

    # Calculate and update word counts
    poems = connection.execute("SELECT id, original_text FROM poems").fetchall()
    for poem_id, text in poems:
        word_count = len(text.split())
        connection.execute(
            "UPDATE poems SET word_count = ? WHERE id = ?",
            (word_count, poem_id)
        )
```

### Conditional Migrations

```python
def upgrade() -> None:
    # Check if column exists before adding
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [c['name'] for c in inspector.get_columns('poems')]

    if 'word_count' not in columns:
        op.add_column('poems', sa.Column('word_count', sa.Integer()))
```

## 📚 Additional Resources

- [Alembic Official Documentation](https://alembic.sqlalchemy.org/)
- [SQLAlchemy Alembic Tutorial](https://docs.sqlalchemy.org/en/14/orm/tutorial.html)
- [FastAPI Database Migrations](https://fastapi.tiangolo.com/tutorial/sql-databases/#alembic-sqlalchemy-migrations)

---

**Last Updated**: 2025-10-19
**Maintainer**: VPSWeb Development Team