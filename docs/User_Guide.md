# VPSWeb Repository v0.3.1 - User Guide

**Version**: 0.3.1
**Date**: 2025-10-19
**System**: VPSWeb Repository System with Web Interface

## Table of Contents

1. [Overview](#overview)
2. [Installation & Setup](#installation--setup)
3. [Getting Started](#getting-started)
4. [Web Interface Guide](#web-interface-guide)
5. [API Reference](#api-reference)
6. [Data Management](#data-management)
7. [Backup & Restore](#backup--restore)
8. [Troubleshooting](#troubleshooting)
9. [Advanced Usage](#advanced-usage)

---

## Overview

VPSWeb Repository is a professional AI-powered poetry translation platform that provides a collaborative Translator→Editor→Translator workflow for producing high-fidelity translations between English and Chinese (and other languages).

### Key Features

- **Modern Web Interface**: Intuitive dashboard and management tools
- **AI-Powered Translation**: Integration with multiple LLM providers
- **Repository Management**: Centralized storage of poems and translations
- **Background Processing**: Non-blocking translation workflows
- **Quality Control**: Translation comparison and rating systems
- **Data Export**: Multiple export formats for translations

### System Architecture

```
VPSWeb Repository System
├── Web Interface (FastAPI + Jinja2)
├── Repository Layer (SQLite + SQLAlchemy)
├── VPSWeb Translation Engine
└── Background Task Processing
```

---

## Installation & Setup

### System Requirements

- **Python**: 3.8 or higher
- **Operating System**: macOS, Linux, or Windows (with WSL)
- **Memory**: 4GB RAM minimum
- **Storage**: 500MB free space minimum

### Installation Steps

#### 1. Clone the Repository

```bash
git clone <repository-url>
cd vpsweb/vpsweb
```

#### 2. Install Dependencies

```bash
# Using Poetry (recommended)
poetry install

# Or using pip
pip install -e .
```

#### 3. Set Up Environment

```bash
# Copy environment template
cp .env.local.template .env.local

# Edit environment file
nano .env.local
```

#### 4. Initialize Database

```bash
# Set Python path
export PYTHONPATH="$(pwd)/src:$PYTHONPATH"

# Run database migrations
cd src/vpsweb/repository
alembic upgrade head
cd - > /dev/null
```

#### 5. Start the Application

```bash
# Start the web interface
python -m vpsweb.webui.main

# Or use uvicorn for development
uvicorn vpsweb.webui.main:app --host 127.0.0.1 --port 8000 --reload
```

The application will be available at: **http://127.0.0.1:8000**

### Environment Configuration

Configure your `.env.local` file:

```bash
# Repository Configuration
REPO_ROOT=./repository_root
REPO_DATABASE_URL=sqlite+aiosqlite:///./repository_root/repo.db
REPO_HOST=127.0.0.1
REPO_PORT=8000
REPO_DEBUG=false
DEV_MODE=true

# Logging Configuration
VERBOSE_LOGGING=true
LOG_FORMAT=text

# LLM Provider Configuration
TONGYI_API_KEY=your_tongyi_api_key
DEEPSEEK_API_KEY=your_deepseek_api_key
```

---

## Getting Started

### First Time Setup

1. **Access the Web Interface**: Open http://127.0.0.1:8000 in your browser
2. **Add Your First Poem**: Click "Add New Poem" in the dashboard
3. **Create a Translation**: Select a poem and start the translation workflow
4. **Review Results**: View translated poems and provide feedback

### Basic Workflow

1. **Add Poems**: Import or manually add original poems
2. **Configure Translation**: Set source and target languages
3. **Start Workflow**: Launch AI translation in background
4. **Monitor Progress**: Track translation status in real-time
5. **Review & Edit**: Review translations and make improvements
6. **Export Results**: Download translations in desired format

---

## Web Interface Guide

### Dashboard

The dashboard provides an overview of your repository:

- **Statistics Cards**: Total poems, translations, and AI/human breakdown
- **Recent Poems**: Quick access to recently added poems
- **Quick Actions**: Add poems, start translations, view statistics
- **Navigation**: Access all major sections

### Poem Management

#### Adding a New Poem

1. Click **"Add New Poem"** on the dashboard
2. Fill in the poem details:
   - **Poet Name**: The author of the poem
   - **Poem Title**: The title of the poem
   - **Source Language**: Original language (ISO code: en, zh-CN, etc.)
   - **Original Text**: The complete poem text
   - **Metadata (Optional)**: JSON metadata for additional information
3. Click **"Save Poem"** to add it to the repository

#### Managing Existing Poems

- **View Details**: Click on any poem card to see full details
- **Edit Poem**: Use the edit button to modify poem information
- **Delete Poem**: Remove poems and associated translations
- **View Translations**: See all translations for a specific poem

### Translation Management

#### Starting a Translation

1. Navigate to a poem's detail page
2. Click **"Add Translation"**
3. Configure translation settings:
   - **Translation Type**: AI Translation or Human Translation
   - **Target Language**: Desired output language
   - **Workflow Mode**: reasoning, non_reasoning, or hybrid
4. Click **"Start Translation"**

#### Monitoring Progress

- **Real-time Updates**: Translation progress updates automatically
- **Task Status**: View pending, running, completed, or failed tasks
- **Detailed Information**: Access translation metadata and logs

#### Reviewing Translations

- **Quality Rating**: Rate translation quality (1-5 stars)
- **Add Notes**: Include human feedback and improvements
- **Compare Versions**: View different translation versions side-by-side
- **Export Results**: Download translations in various formats

### Comparison View

The comparison view allows side-by-side analysis:

- **Multiple Translations**: Compare different translation versions
- **Quality Metrics**: View automated quality assessments
- **Human Feedback**: Access human notes and ratings
- **Filter Options**: Filter by language, quality, or date

### API Documentation

Access comprehensive API documentation at:
- **Swagger UI**: http://127.0.0.1:8000/docs
- **ReDoc**: http://127.0.0.1:8000/redoc
- **OpenAPI JSON**: http://127.0.0.1:8000/openapi.json

---

## API Reference

### Authentication

Currently, the API uses basic authentication with API keys. Configure in your environment file.

### Core Endpoints

#### Poem Management

```http
GET    /api/v1/poems/                    # List poems
POST   /api/v1/poems/                    # Create poem
GET    /api/v1/poems/{id}                # Get poem details
PUT    /api/v1/poems/{id}                # Update poem
DELETE /api/v1/poems/{id}                # Delete poem
```

#### Translation Management

```http
GET    /api/v1/translations/             # List translations
POST   /api/v1/translations/             # Create translation
GET    /api/v1/translations/{id}         # Get translation details
PUT    /api/v1/translations/{id}         # Update translation
DELETE /api/v1/translations/{id}         # Delete translation
```

#### Workflow Management

```http
POST   /api/v1/workflow/translate         # Start translation workflow
GET    /api/v1/workflow/tasks/{id}        # Get task status
DELETE /api/v1/workflow/tasks/{id}        # Cancel task
GET    /api/v1/workflow/tasks             # List active tasks
```

### Example Usage

#### Create a New Poem

```bash
curl -X POST "http://127.0.0.1:8000/api/v1/poems/" \
  -H "Content-Type: application/json" \
  -d '{
    "poet_name": "Robert Frost",
    "poem_title": "The Road Not Taken",
    "source_language": "en",
    "original_text": "Two roads diverged in a yellow wood...",
    "metadata_json": null
  }'
```

#### Start Translation Workflow

```bash
curl -X POST "http://127.0.0.1:8000/api/v1/workflow/translate" \
  -H "Content-Type: application/json" \
  -d '{
    "poem_id": "01K7XW21RQBYR4Y8V7E24ZZ99V",
    "target_language": "zh-CN",
    "workflow_mode": "hybrid"
  }'
```

#### Check Task Status

```bash
curl -X GET "http://127.0.0.1:8000/api/v1/workflow/tasks/{task_id}"
```

---

## Data Management

### Database Schema

The system uses SQLite with the following main tables:

- **poems**: Original poems and metadata
- **translations**: Translation results and quality metrics
- **ai_logs**: AI processing logs and metadata
- **human_notes**: Human feedback and annotations

### Data Export

#### Manual Export

1. Navigate to the poem detail page
2. Click **"Export"** button
3. Choose export format:
   - **JSON**: Structured data format
   - **Markdown**: Formatted text
   - **Plain Text**: Simple text format

#### API Export

```bash
# Export poem with translations
curl -X GET "http://127.0.0.1:8000/api/v1/poems/{id}/translations" \
  -H "Accept: application/json"
```

### Data Import

#### Manual Import

1. Use the **"Add New Poem"** form
2. Paste or type the poem text
3. Fill in metadata
4. Save to repository

#### API Import

```bash
# Import new poem
curl -X POST "http://127.0.0.1:8000/api/v1/poems/" \
  -H "Content-Type: application/json" \
  -d '{"poet_name": "...", "poem_title": "...", ...}'
```

---

## Backup & Restore

### Creating Backups

#### Automated Backup

Use the provided backup script:

```bash
# Create a complete backup
./backup.sh

# View backup options
./backup.sh --help
```

The backup script creates:
- **Database Backup**: SQLite database with consistency check
- **Configuration Files**: Environment and configuration settings
- **Source Code**: Selected source files (optional)
- **Metadata**: System information and backup details

#### Manual Backup

```bash
# Backup database
cp repository_root/repo.db backup/repo.db

# Backup configuration
cp .env.local backup/
cp config/repository.yaml backup/
```

### Restoring from Backup

#### Automated Restore

Use the provided restore script:

```bash
# List available backups
./restore.sh --list

# Restore from backup
./restore.sh vpsweb_repo_backup_20231019_120000

# Restore with source code
./restore.sh --source vpsweb_repo_backup_20231019_120000

# Skip safety backup
./restore.sh --skip-safety vpsweb_repo_backup_20231019_120000
```

#### Manual Restore

```bash
# Stop the application
pkill -f "vpsweb.webui.main"

# Restore database
cp backup/repo.db repository_root/

# Restore configuration
cp backup/.env.local .env.local

# Restart application
python -m vpsweb.webui.main
```

### Backup Schedule

Recommended backup practices:

- **Daily Backups**: For active development environments
- **Weekly Backups**: For regular usage
- **Before Updates**: Always backup before system updates
- **Before Major Changes**: Backup before structural changes

---

## Troubleshooting

### Common Issues

#### Application Won't Start

**Problem**: Application fails to start with import errors

**Solution**:
```bash
# Check Python path
export PYTHONPATH="$(pwd)/src:$PYTHONPATH"

# Install dependencies
pip install -e .

# Check configuration
cat .env.local
```

#### Database Connection Errors

**Problem**: SQLite database connection fails

**Solution**:
```bash
# Check database file exists
ls -la repository_root/repo.db

# Check permissions
chmod 644 repository_root/repo.db

# Run migrations
cd src/vpsweb/repository
alembic upgrade head
```

#### Translation Workflow Fails

**Problem**: Translation tasks fail with API errors

**Solution**:
```bash
# Check API keys
cat .env.local | grep API_KEY

# Test API connectivity
curl -X POST "http://127.0.0.1:8000/api/v1/workflow/validate" \
  -d '{"poem_id": "...", "target_language": "zh-CN"}'

# Check logs
tail -f logs/vpsweb.log
```

#### Performance Issues

**Problem**: Slow response times or timeouts

**Solution**:
```bash
# Check system resources
top

# Clear old task logs
find repository_root -name "*.log" -mtime +7 -delete

# Restart application
pkill -f "vpsweb.webui.main"
python -m vpsweb.webui.main
```

### Error Messages

#### "Database file not found"

**Cause**: Database file missing or incorrect path

**Solution**:
```bash
# Check repository root
ls -la repository_root/

# Initialize database
mkdir -p repository_root
cd src/vpsweb/repository
alembic upgrade head
```

#### "API key not configured"

**Cause**: Missing or invalid LLM provider API keys

**Solution**:
```bash
# Edit environment file
nano .env.local

# Add valid API keys
TONGYI_API_KEY=your_valid_key
DEEPSEEK_API_KEY=your_valid_key
```

#### "Task failed with workflow error"

**Cause**: LLM provider error or configuration issue

**Solution**:
1. Check API key validity
2. Verify network connectivity
3. Review error logs for specific details
4. Test with different workflow mode

### Getting Help

#### System Information

For support, provide the following information:

```bash
# System information
uname -a
python --version

# Application version
python -c "import vpsweb; print(vpsweb.__version__)"

# Configuration
cat .env.local

# Logs
tail -n 50 logs/vpsweb.log
```

#### Support Resources

- **Documentation**: Check this user guide first
- **API Documentation**: http://127.0.0.1:8000/docs
- **System Logs**: Review application logs for error details
- **Configuration**: Verify environment settings

---

## Advanced Usage

### Custom Configuration

#### Database Configuration

Edit `config/repository.yaml`:

```yaml
database:
  url: "sqlite+aiosqlite:///./repository_root/repo.db"
  echo: false
  pool_pre_ping: true

workflow:
  default_mode: "hybrid"
  timeout_seconds: 300
  max_concurrent_tasks: 5
```

#### LLM Provider Configuration

Configure multiple providers:

```yaml
providers:
  tongyi:
    api_key: "${TONGYI_API_KEY}"
    model: "qwen-max"
    base_url: "https://dashscope.aliyuncs.com/compatible-mode/v1"

  deepseek:
    api_key: "${DEEPSEEK_API_KEY}"
    model: "deepseek-chat"
    base_url: "https://api.deepseek.com"
```

### Custom Workflow Modes

#### Reasoning Mode

Provides detailed analysis and step-by-step translation process.

#### Non-Reasoning Mode

Fast translation with minimal analysis.

#### Hybrid Mode

Balanced approach combining speed and quality.

### Development Setup

#### Development Environment

```bash
# Install development dependencies
poetry install --dev

# Run tests
pytest tests/

# Code formatting
black src/ tests/

# Type checking
mypy src/
```

#### Debug Mode

Enable debug logging:

```bash
# Set debug mode
export REPO_DEBUG=true
export VERBOSE_LOGGING=true

# Start application
python -m vpsweb.webui.main
```

### API Integration

#### Webhook Integration

Configure webhooks for translation completion:

```yaml
webhooks:
  on_translation_complete:
    url: "https://your-api.com/webhook"
    secret: "your-webhook-secret"
```

#### External API Usage

```python
import requests

# Start translation
response = requests.post("http://127.0.0.1:8000/api/v1/workflow/translate", json={
    "poem_id": "poem_id_here",
    "target_language": "zh-CN",
    "workflow_mode": "hybrid"
})

task_id = response.json()["task_id"]

# Check status
status = requests.get(f"http://127.0.0.1:8000/api/v1/workflow/tasks/{task_id}")
print(status.json())
```

### Performance Optimization

#### Database Optimization

```sql
-- Create indexes for better performance
CREATE INDEX idx_poems_created_at ON poems(created_at);
CREATE INDEX idx_translations_poem_id ON translations(poem_id);
CREATE INDEX idx_translations_target_lang ON translations(target_language);
```

#### Caching Configuration

Enable response caching:

```yaml
cache:
  enabled: true
  ttl_seconds: 300
  max_size: 1000
```

---

## FAQ

### Q: How many languages are supported?

A: Currently supports English (en) and Chinese (zh-CN) with plans for additional languages in future versions.

### Q: Can I use different LLM providers?

A: Yes, the system supports multiple providers including Tongyi (Alibaba) and DeepSeek. Configure API keys in your environment file.

### Q: How do I export all my data?

A: Use the backup script for complete system backup, or use the API endpoints for selective data export.

### Q: Is my data secure?

A: All data is stored locally in SQLite database. No data is transmitted to external services except for LLM API calls during translation.

### Q: Can I run multiple translation tasks simultaneously?

A: Yes, the system supports concurrent background tasks with configurable limits.

### Q: How do I update to a new version?

A: Always create a backup before updating, then follow the installation instructions for the new version.

---

## Appendix

### Environment Variables Reference

| Variable | Description | Default |
|----------|-------------|---------|
| `REPO_ROOT` | Repository data directory | `./repository_root` |
| `REPO_DATABASE_URL` | Database connection URL | `sqlite+aiosqlite:///./repository_root/repo.db` |
| `REPO_HOST` | Server host | `127.0.0.1` |
| `REPO_PORT` | Server port | `8000` |
| `REPO_DEBUG` | Debug mode | `false` |
| `DEV_MODE` | Development mode | `true` |
| `VERBOSE_LOGGING` | Verbose logging | `true` |
| `TONGYI_API_KEY` | Tongyi API key | Required |
| `DEEPSEEK_API_KEY` | DeepSeek API key | Required |

### File Structure

```
vpsweb/
├── src/vpsweb/           # Source code
│   ├── repository/       # Repository layer
│   ├── webui/           # Web interface
│   ├── models/          # Data models
│   └── core/            # Core functionality
├── config/               # Configuration files
├── repository_root/      # Database and data files
├── backups/             # Backup files
├── docs/                # Documentation
├── backup.sh            # Backup script
├── restore.sh           # Restore script
├── pyproject.toml       # Project configuration
└── .env.local           # Environment configuration
```

### Version History

- **v0.3.1**: Current version with web interface and workflow integration
- **v0.3.0**: Core translation workflow system
- **v0.2.x**: Early development versions

---

**Document Version**: 1.0
**Last Updated**: 2025-10-19
**For VPSWeb Repository v0.3.1**