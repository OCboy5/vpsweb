# VPSWeb: AI-Powered Poetry Translation Platform

> Professional poetry translation with AI-enhanced contextual analysis and real-time collaborative workflow

[![Version](https://img.shields.io/badge/Version-0.7.0-blue.svg)](https://github.com/OCboy5/vpsweb/releases/tag/v0.7.0)
[![Python](https://img.shields.io/badge/Python-3.13-blue.svg)](https://python.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**VPSWeb** is a professional AI-powered poetry translation platform that provides sophisticated translation capabilities through a modern web interface. It combines AI-generated Background Briefing Reports (BBR) with real-time collaborative workflows to produce high-fidelity translations that preserve cultural context, aesthetic beauty, and emotional resonance.

## ✨ Key Features

### 🎨 **Modern Web Interface**
- **Primary Interface**: FastAPI-based web application with responsive design
- **Real-time Dashboard**: Live statistics and activity monitoring
- **Interactive Workflow Management**: Visual translation progress with Server-Sent Events
- **Mobile-Responsive**: Works seamlessly across all devices

### 🧠 **AI-Enhanced Translation**
- **Background Briefing Reports (BBR)**: AI-generated contextual analysis for enhanced translation quality
- **3-Step Collaborative Workflow**: Translator → Editor → Translator process
- **Multiple Translation Modes**: Hybrid, Manual, Reasoning, and Non-Reasoning modes
- **Multi-language Support**: English, Chinese, Japanese, and Korean

### 🔄 **Real-time Features**
- **Server-Sent Events (SSE)**: Live progress updates during translation workflows
- **Interactive BBR Modals**: Draggable, resizable interfaces for contextual analysis
- **Dynamic Content Loading**: AJAX-based updates without page refreshes
- **Toast Notifications**: Non-intrusive user feedback

### 📊 **Repository Management**
- **Centralized Storage**: SQLite database with comprehensive metadata
- **Poet & Poem Organization**: Structured content management
- **Translation Comparison**: Side-by-side analysis of different translations
- **Quality Rating System**: 0-10 scale with human notes and AI logs

## 🚀 Quick Start (5 Minutes)

### Prerequisites
- Python 3.9 or higher
- Git

### Automated Setup

```bash
# Clone the repository
git clone https://github.com/OCboy5/vpsweb.git
cd vpsweb

# One-command setup (installs dependencies, initializes database, starts web interface)
./scripts/setup.sh

# Initialize database
./scripts/setup-database.sh init

# Start the web application
./scripts/start.sh
```

**Access the web interface**: http://127.0.0.1:8000

## 🎯 Getting Started

### 1. **Dashboard Overview**
- View real-time statistics: total poems, translations, and AI/human breakdown
- Monitor recent activity with color-coded badges
- Quick access to all major sections

### 2. **Add Your First Poem**
1. Click **"Add Poem"** in the navigation
2. Fill in poet name, title, source language, and poem text
3. Click **"Save Poem"**

### 3. **Generate Background Briefing Report (Optional)**
1. On the poem detail page, click the **BBR button** (bottom-right)
2. AI generates contextual analysis including cultural background and linguistic insights
3. View in an interactive modal with drag/resize capabilities

### 4. **Start Translation**
1. Select target language (Chinese, English, Japanese, or Korean)
2. Choose workflow mode:
   - **Hybrid** (Recommended): Balanced approach
   - **Manual Mode**: Human-controlled with external LLM
   - **Reasoning Mode**: Detailed step-by-step analysis
   - **Non-Reasoning Mode**: Fast, direct translation
3. Click **"Start Translation"**
4. Watch real-time progress with 3-step indicators

### 5. **Review Results**
- View completed translations with quality ratings
- Compare different translation versions
- Add human notes and feedback
- Access detailed AI workflow logs

## 🏗️ Architecture

VPSWeb implements a modern web-centric architecture with real-time capabilities:

```
VPSWeb v0.7.0 Architecture
├── Web Interface Layer (FastAPI + Tailwind CSS + SSE)
│   ├── Real-time Dashboard with Statistics
│   ├── Poem Management Interface
│   ├── Translation Workflow with Live Progress
│   └── BBR Modal System
├── Translation Engine Layer
│   ├── 3-Step AI Workflow (Initial → Editor → Revision)
│   ├── Background Briefing Report Generation
│   └── Multiple LLM Provider Support
├── Real-time Communication Layer
│   ├── Server-Sent Events (SSE)
│   ├── Task State Management
│   └── Progress Tracking
└── Repository Layer (SQLite Database)
    ├── 5-Table Schema with BBR Support
    └── Dual-Storage Strategy
```

## ⚙️ Configuration

### Environment Setup

Copy the environment template and configure your API keys:

```bash
cp .env.local.template .env.local
```

Edit `.env.local` with your configuration:

```bash
# Repository Configuration
REPO_ROOT=./repository_root
REPO_DATABASE_URL=sqlite+aiosqlite:///./repository_root/repo.db
REPO_HOST=127.0.0.1
REPO_PORT=8000
REPO_DEBUG=false

# LLM Provider Configuration (required for translations)
TONGYI_API_KEY=your_tongyi_api_key
DEEPSEEK_API_KEY=your_deepseek_api_key

# Optional: OpenAI-compatible provider
OPENAI_API_KEY=your_openai_api_key
OPENAI_BASE_URL=https://api.openai.com/v1
```

### Provider Configuration

VPSWeb supports multiple LLM providers through YAML configuration:

```yaml
# config/models.yaml
providers:
  tongyi:
    api_key: "${TONGYI_API_KEY}"
    base_url: "https://dashscope.aliyuncs.com/compatible-mode/v1"
    model: "qwen-max"
  deepseek:
    api_key: "${DEEPSEEK_API_KEY}"
    base_url: "https://api.deepseek.com"
    model: "deepseek-chat"
```

## 🔧 Development

### Setup Development Environment

```bash
# Install dependencies
poetry install

# Set Python path
export PYTHONPATH="$(pwd)/src:$PYTHONPATH"

# Run tests
poetry run pytest tests/ -v

# Code formatting
poetry run black src/ tests/

# Type checking
poetry run mypy src/
```

### Daily Development Commands

```bash
# Start development server with auto-reload
uvicorn vpsweb.webui.main:app --host 127.0.0.1 --port 8000 --reload

# Clean restart
./scripts/clean-start.sh

# Stop server
./scripts/stop.sh

# Run test suite
./scripts/test.sh
```

## 📊 Translation Workflow Modes

### **Hybrid Mode** (Recommended)
- Optimal balance of speed and quality
- Uses reasoning for editorial review
- Uses standard models for translation steps
- Best for most poetry translation needs

### **Manual Mode**
- Human-controlled translation workflow
- External LLM integration through copy-paste
- Maximum flexibility for testing any AI model
- Session-based progress tracking

### **Reasoning Mode**
- Detailed step-by-step analysis
- Uses reasoning models for all steps
- Highest quality for complex analysis
- Comprehensive explanation generation

### **Non-Reasoning Mode**
- Fast, direct translation approach
- Uses standard models for all steps
- Cost-effective for high-volume translation
- Quick turnaround time

## 📖 Documentation

### **User Documentation**
- **[User Guide](docs/User_Guide.md)** - Complete user manual with WebUI walkthrough
- **[Development Setup Guide](docs/Development_Setup.md)** - Developer onboarding and setup
- **[Architecture Documentation](docs/ARCHITECTURE.md)** - System architecture and design

### **API Documentation**
- **[Interactive API Docs](http://127.0.0.1:8000/docs)** - Swagger UI (when running)
- **[API Patterns Documentation](docs/api-patterns.md)** - API integration patterns

### **Project Documentation**
- **[Release Process](CLAUDE_RELEASE_PROCESS.md)** - Standardized release procedure
- **[API Reference](http://127.0.0.1:8000/redoc)** - ReDoc documentation (when running)

## 🤝 Contributing

We welcome contributions! Please see our contributing guidelines:

1. **Fork the repository**
2. **Create a feature branch** (`git checkout -b feature/amazing-feature`)
3. **Commit your changes** (`git commit -m 'Add amazing feature'`)
4. **Push to the branch** (`git push origin feature/amazing-feature`)
5. **Open a Pull Request**

### Code Style
- Follow Python PEP 8
- Use `poetry run black` for formatting
- Include type hints
- Write tests for new features

## 📋 Requirements

- Python 3.13
- Poetry (package manager)
- API keys for LLM providers
- Modern web browser (for WebUI)

## 🚀 Production Deployment

### Database Setup

```bash
# Initialize database with migrations
./scripts/setup-database.sh init

# Create backup before first use
cp repository_root/repo.db repository_root/repo_backup_$(date +%Y%m%d_%H%M%S).db
```

### Server Management

```bash
# Production start
./scripts/start.sh

# Graceful stop
./scripts/stop.sh

# Health check
curl http://127.0.0.1:8000/health
```

### Backup and Restore

```bash
# Create complete backup
./scripts/backup.sh

# List available backups
./backup.sh --list

# Restore from backup
./restore.sh --clean backup_timestamp
```

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🏆 Release History

- **v0.7.0** - Manual Translation Workflow Release with BBR system
- **v0.6.x** - WebUI refinements and multi-language support
- **v0.5.x** - Script-based setup and management
- **v0.4.x** - Initial WebUI implementation
- **v0.3.x** - Core translation workflow system
- **v0.2.x** - Early development versions

## 🙏 Acknowledgments

- Built with modern Python best practices
- Inspired by professional translation workflows
- Enhanced by community contributions
- Powered by advanced AI language models

---

**VPSWeb** - Professional poetry translation with AI-powered contextual analysis and real-time collaborative workflows.

Access at: **http://127.0.0.1:8000**