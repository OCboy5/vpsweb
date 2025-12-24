# VPSWeb Repository v0.7.0 - User Guide

**Version**: 0.7.0
**Date**: 2025-12-18
**System**: VPSWeb Repository System with Web Interface and Background Briefing Reports

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

- **Modern Web Interface**: Intuitive dashboard with real-time updates and responsive design
- **AI-Powered Translation**: 3-step T-E-T (Translator→Editor→Translator) workflow with multiple modes
- **Background Briefing Reports (BBR)**: AI-generated contextual analysis to enhance translation quality
- **Repository Management**: Centralized storage with poet and poem management
- **Real-time Progress**: Server-Sent Events (SSE) for live translation workflow updates
- **Quality Control**: Interactive quality rating system (0-10 scale) with translation notes
- **Multiple Translation Modes**: Hybrid, Manual, Reasoning, and Non-Reasoning workflows
- **Multi-language Support**: English, Chinese, Japanese, and Korean
- **Data Export**: Multiple export formats for translations and comparison views

### System Architecture

```
VPSWeb Repository System v0.7.0
├── Web Interface (FastAPI + Tailwind CSS)
│   ├── Dashboard with real-time statistics
│   ├── Poem management interface
│   ├── Translation workflow visualization
│   └── BBR modal system
├── Translation Engine
│   ├── 3-Step AI Workflow (Initial → Editor → Revision)
│   ├── Manual translation sessions
│   ├── BBR generation service
│   └── Multiple LLM provider support
├── Real-time Updates (SSE)
│   ├── Progress tracking
│   ├── Step indicators
│   └── Status notifications
└── Repository Layer (SQLite + SQLAlchemy)
    ├── Poems and poets
    ├── Translations with metadata
    ├── AI execution logs
    └── Human notes and ratings
```

---

## Installation & Setup

### System Requirements

- **Python**: 3.13
- **Operating System**: macOS, Linux, or Windows (with WSL)
- **Memory**: 4GB RAM minimum
- **Storage**: 500MB free space minimum

### Installation Steps

#### 1. Clone the Repository

```bash
git clone <repository-url>
cd vpsweb
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
# Start the web interface (recommended)
./scripts/start.sh

# Or manually:
python -m vpsweb.webui.main

# Or use uvicorn for development
uvicorn vpsweb.webui.main:app --host 127.0.0.1 --port 8000 --reload
```

The application will be available at: **http://127.0.0.1:8000**

The WebUI is the primary interface for all VPSWeb operations, providing a complete dashboard for poem management, translation workflows, and BBR generation.

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
2. **View the Dashboard**: See real-time statistics and recent activity
3. **Add Your First Poem**: Click "Add Poem" button in the navigation
4. **Generate a BBR** (Optional): On the poem detail page, click the BBR button for contextual analysis
5. **Create a Translation**: Select target language, choose workflow mode, and start translation
6. **Monitor Real-time Progress**: Watch the 3-step workflow with live updates

### Basic Workflow in WebUI

1. **Dashboard Overview**
   - View statistics: Total Poets, Poems, Translations
   - See recent activity with color-coded badges
   - Quick access to all major sections

2. **Poem Management**
   - Navigate to **Poems** section
   - Click "Add Poem" to create new entries
   - Fill in poet name, title, language, and poem text
   - Edit or delete existing poems

3. **Translation Workflow**
   - Click on any poem to view details
   - Select target language (Chinese, English, Japanese, Korean)
   - Choose workflow mode:
     - **Hybrid** (Recommended): Balanced approach
     - **Manual Mode**: Human-controlled translation
     - **Reasoning Mode**: Detailed analysis
     - **Non-Reasoning Mode**: Fast translation
   - Click "Start Translation" to begin
   - Monitor real-time progress with step indicators

4. **Background Briefing Reports (BBR)**
   - On poem detail page, click BBR button (bottom-right)
   - AI generates contextual analysis
   - View in interactive modal with drag/resize
   - Enhances translation quality with background information

5. **Review and Compare**
   - View completed translations with quality ratings
   - Add human notes and ratings
   - Use compare view for side-by-side analysis
   - Access translation notes with detailed AI logs

---

## Web Interface Guide

### Web Interface Navigation

The VPSWeb WebUI provides a modern, responsive interface accessible at **http://127.0.0.1:8000**.

#### Main Navigation

- **Dashboard**: Real-time statistics and recent activity overview
- **Poets**: Manage poet information and browse by poet
- **Poems**: View and manage all poems in the repository
- **Translations**: Browse all translations with filtering options
- **Selected**: View poems marked as selected/favorites

### Dashboard

The dashboard provides an at-a-glance overview of your repository:

- **Statistics Cards**:
  - Total Poets, Poems, Translations
  - AI vs Human translation breakdown
  - Real-time data updates
- **Recent Activity**:
  - Last 6 poems with activity badges
  - Color-coded indicators (Green: New Poem, Blue: New Translation, Purple: New BBR)
- **Quick Actions**:
  - "Add Poem" primary action button
  - Quick navigation to all major sections

### Poem Management

#### Adding a New Poem

1. Click **"Add Poem"** button in navigation
2. Fill in the poem details:
   - **Poet Name**: The author of the poem
   - **Poem Title**: The title of the poem
   - **Source Language**: Original language (English, Chinese, etc.)
   - **Original Text**: The complete poem text
   - **Metadata (Optional)**: JSON metadata for additional information
3. Click **"Save Poem"** to add it to the repository

#### Poem Detail Page

Click any poem to view comprehensive details:

- **Poem Header**: Title, poet, language badge, creation date
- **Selection Toggle**: Star icon to mark poems as favorites
- **Poem Content**: Beautifully formatted text with poetry styling
- **Action Buttons**: Edit, Delete, and BBR generation

#### BBR (Background Briefing Report)

Enhance your translations with AI-generated context:

1. Click the **BBR button** (bottom-right of poem detail page)
2. AI analyzes the poem and generates:
   - Cultural context and references
   - Linguistic analysis
   - Historical background
   - Translation considerations
3. View in an interactive modal:
   - Drag to reposition
   - Resize handles for custom sizing
   - Close when done

### Translation Workflows

#### Starting a Translation

1. From poem detail page, scroll to **AI Translation Workflow** section
2. Configure settings:
   - **Target Language**: Chinese, English, Japanese, or Korean
   - **Workflow Mode**:
     - **Hybrid** (Recommended): Balanced speed and quality
     - **Manual Mode**: Human-controlled with external LLM
     - **Reasoning Mode**: Detailed step-by-step analysis
     - **Non-Reasoning Mode**: Fast, direct translation
3. Click **"Start Translation"**

#### Real-time Progress Monitoring

Watch your translation progress in real-time:

- **Progress Bar**: Visual percentage completion
- **3-Step Indicators**:
  1. **Initial Translation** - First AI translation pass
  2. **Editor Review** - AI acts as editor to review and refine
  3. **Translator Revision** - Final revision by AI translator
- **Status Messages**: Real-time updates on current activity
- **Timing Information**: Duration for each step
- **Cancel Option**: Stop workflow if needed

This real-time update uses Server-Sent Events (SSE) for instant communication between the server and your browser.

### Translation Review and Management

#### Viewing Completed Translations

- **Translation Cards**: Display with metadata
  - Translator type badge (AI/Human)
  - Target language
  - Quality rating (0-10 scale, 0 = unrated)
  - Translation preview
- **Action Buttons**:
  - **View Poem**: Return to original poem
  - **Translation Notes**: Detailed AI workflow logs
  - **Compare**: Side-by-side comparison view

#### Translation Notes

Access comprehensive workflow information:

- **Step-by-step logs** for each workflow phase
- **Performance metrics**: Tokens used, costs, duration
- **Quality assessment breakdown**
- **AI model information** and settings

#### Compare View

Analyze translations side-by-side:

- **Multiple translation support**: Compare different versions
- **Visual comparison**: Clear formatting for easy analysis
- **Quality indicators**: Ratings and metadata displayed
- **Human feedback**: Access notes and ratings

### Multi-language Support

VPSWeb supports translation between multiple languages:

- **English** (en)
- **Chinese** (zh-CN)
- **Japanese** (ja)
- **Korean** (ko)

All translations maintain cultural and linguistic integrity through the sophisticated 3-step workflow process.

### API Documentation

For developers, comprehensive API documentation is available:

- **Swagger UI**: http://127.0.0.1:8000/docs
  - Interactive API exploration
  - Test endpoints directly
- **ReDoc**: http://127.0.0.1:8000/redoc
  - Clean, readable API documentation
- **OpenAPI JSON**: http://127.0.0.1:8000/openapi.json
  - Machine-readable specification

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
./scripts/stop.sh
./scripts/start.sh
```

### WebUI Issues

#### Real-time Updates Not Working

**Problem**: Translation progress not updating

**Solution**:
1. Check browser console for SSE errors
2. Refresh the page and restart translation
3. Ensure browser supports EventSource (modern browsers)
4. Check network connectivity

#### BBR Modal Not Working

**Problem**: BBR button doesn't open modal

**Solution**:
1. Check if JavaScript is enabled in browser
2. Look for console errors (F12 → Console)
3. Try refreshing the page
4. Ensure BBR generation completed successfully

#### Translation Workflow Stuck

**Problem**: Translation progress stuck at a step

**Solution**:
1. Click "Cancel" and restart translation
2. Try a different workflow mode
3. Check API key configuration
4. View browser network tab for failed requests

### BBR Issues

#### BBR Generation Fails

**Problem**: BBR button doesn't generate report

**Solution**:
```bash
# Check API keys
cat .env.local | grep API_KEY

# Test API connectivity
# Try a simple translation first

# Check logs for errors
tail -f logs/vpsweb.log
```

#### BBR Content Poor Quality

**Problem**: Generated BBR not helpful

**Solution**:
1. Try regenerating the BBR
2. Check if poem text is complete
3. Different LLM providers may give different results
4. Provide feedback for improvement

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

A: VPSWeb supports English, Chinese, Japanese, and Korean with more languages planned for future versions.

### Q: Can I use different LLM providers?

A: Yes, the system supports multiple providers including Tongyi (Alibaba), DeepSeek, and OpenAI-compatible providers. Configure API keys in your environment file.

### Q: What is a Background Briefing Report (BBR)?

A: BBR is an AI-generated contextual analysis that provides cultural background, linguistic insights, and historical context for poems. It enhances translation quality by giving the AI translator deeper understanding of the poem.

### Q: How do I use BBR effectively?

A: Click the BBR button on any poem detail page to generate a report. Review the generated context before starting translation. The BBR modal can be dragged and resized for your convenience.

### Q: What are the different translation modes?

A:
- **Hybrid** (Recommended): Balanced approach combining speed and quality
- **Manual Mode**: Human-controlled translation using external LLM tools
- **Reasoning Mode**: Detailed step-by-step analysis with explanations
- **Non-Reasoning Mode**: Fast, direct translation

### Q: Can I run multiple translation tasks simultaneously?

A: Yes, the system supports concurrent background tasks. Monitor progress in real-time on the poem detail page.

### Q: My translation progress is stuck. What should I do?

A: Click "Cancel" and restart with a different workflow mode. Check your API connectivity and browser console for errors.

### Q: How do I export all my data?

A: Use the backup script (`./scripts/backup.sh`) for complete system backup, or use the WebUI to export individual translations in various formats.

### Q: Is my data secure?

A: All data is stored locally in SQLite database. No data is transmitted to external services except for LLM API calls during translation and BBR generation.

### Q: How do I update to a new version?

A: Always create a backup using `./save-version.sh` before updating, then follow the installation instructions for the new version.

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

- **v0.7.0**: Current version with Background Briefing Report (BBR) system, real-time SSE updates, and enhanced WebUI
- **v0.6.x**: WebUI refinements and multi-language support
- **v0.5.x**: Script-based setup and management
- **v0.4.x**: Initial WebUI implementation
- **v0.3.x**: Core translation workflow system
- **v0.2.x**: Early development versions

---

**Document Version**: 2.0
**Last Updated**: 2025-12-18
**For VPSWeb Repository v0.7.0**