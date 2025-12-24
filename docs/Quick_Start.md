# VPSWeb Repository v0.4.1 - Quick Start Guide

**Get started in 5 minutes!**

## Prerequisites

- Python 3.8+
- 4GB RAM
- 500MB free space

## Installation

```bash
# 1. Clone and navigate
git clone <repository-url>
cd vpsweb/vpsweb

# 2. Install dependencies
poetry install
# or: pip install -e .

# 3. Configure environment
cp .env.local.template .env.local
# Edit .env.local with your API keys

# 4. Initialize database
export PYTHONPATH="$(pwd)/src:$PYTHONPATH"
cd src/vpsweb/repository && alembic upgrade head && cd - > /dev/null

# 5. Start the application
python -m vpsweb.webui.main
```

Visit: **http://127.0.0.1:8000**

## First Steps

### 1. Add a Poem

1. Click **"Add New Poem"**
2. Enter poem details:
   - Poet: "Robert Frost"
   - Title: "The Road Not Taken"
   - Language: "en"
   - Text: "Two roads diverged in a yellow wood..."
3. Click **"Save Poem"**

### 2. Start Translation

1. Click on your poem
2. Click **"Add Translation"**
3. Set target language: "zh-CN"
4. Choose workflow: "Hybrid"
5. Click **"Start Translation"**

### 3. Monitor Progress

- Translation runs in background
- Status updates automatically
- View progress in real-time

## Basic Commands

```bash
# Start application
python -m vpsweb.webui.main

# Create backup
./backup.sh

# View help
./backup.sh --help
./restore.sh --help
```

## Need Help?

- **Full Guide**: See [User_Guide.md](User_Guide.md)
- **API Docs**: http://127.0.0.1:8000/docs
- **Troubleshooting**: Check User Guide troubleshooting section

## Environment Setup

Edit `.env.local`:

```bash
# Required API Keys
TONGYI_API_KEY=your_tongyi_key
DEEPSEEK_API_KEY=your_deepseek_key

# Optional Settings
REPO_DEBUG=false
VERBOSE_LOGGING=true
```

**That's it! You're ready to translate poetry with AI assistance.** 🚀