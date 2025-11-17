# Changelog

All notable changes to VPSWeb will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [0.5.2] - 2025-01-17

### 🎭 Major Features
- **V2 BBR Integration**: Full Background Briefing Report integration in B-T-E-T workflow
- **Enhanced Prompt Templates**: V2 templates with improved instructions and strategy dials
- **Centralized Configuration**: Translation strategy dials moved to default.yaml

### 🔧 Core Changes
- **BackgroundBriefingReport Model**: New model with comprehensive metadata (timestamps, tokens, cost, duration)
- **Strategy Dials System**: Centralized translation strategy configuration with fallback logic
- **BBR Retrieval**: Database integration for BBR content in workflow
- **JSON Output Order**: BBR section positioned after input, before translation steps

### 📋 Technical Updates
- **Executor._get_strategy_value()**: Helper method for centralized strategy access
- **Workflow BBR Integration**: BBR content retrieval, validation, and error handling
- **JSON Serialization**: Enhanced serialization/deserialization for BBR with type conversion
- **Debug Improvements**: Comprehensive debug printouts for prompts and BBR content
- **Error Handling**: Robust JSON parsing and type conversion for model_info fields

### 🎯 Translation Enhancement
- **BBR Content**: Automatically populated in initial_translation prompts from database
- **Strategy Variables**: All strategy variables (adaptation_level, repetition_policy, etc.) from config
- **Template Simplification**: Removed redundant explanations from prompt templates
- **Enhanced Debugging**: Better visibility into prompt generation and variable substitution

### 🛠️ Breaking Changes
- **Configuration**: Strategy dials now required in default.yaml (with sensible defaults)
- **JSON Structure**: New background_briefing_report section in output (optional)
- **Dependencies**: Updated model relationships for BBR integration

### 📝 Documentation
- Updated README.md with v0.5.2 version
- Added comprehensive BBR integration documentation
- Enhanced configuration examples for strategy dials

### 🐛 Bug Fixes
- Fixed model_info JSON string parsing for BBR (Dict[str, str] type requirements)
- Fixed field mapping (time_spent → duration) for BBR model creation
- Improved error handling for malformed BBR JSON data

---

## [0.5.1] - 2025-01-XX

### 🎭 Enhanced Features
- **Enhanced Pagination**: Improved pagination system for web UI and API
- **BBR LLM Integration**: Advanced integration with Background Briefing Reports

### 🔧 Core Changes
- **Repository System**: Enhanced database operations and queries
- **Web UI Improvements**: Better user experience and interface polish

### 📋 Technical Updates
- **Performance Optimizations**: Improved query performance and response times
- **Code Quality**: Enhanced code structure and maintainability

---

## [0.5.0] - 2025-01-XX

### 🎭 Major Release
- **BBR Integration**: Complete Background Briefing Report system
- **V2 Prompt Templates**: Enhanced prompt templates with improved instructions
- **Repository System**: Full database integration for poem and translation management

### 🔧 Core Changes
- **Background Briefing Reports**: Comprehensive analysis and contextual information
- **Enhanced Workflow**: Improved T-E-T workflow with better step coordination
- **Database Integration**: SQLite-based storage with proper relationships

### 📋 Technical Updates
- **API Improvements**: Enhanced REST API with comprehensive endpoints
- **Web UI**: Improved user interface with better navigation and functionality

---

[Unreleased]: Planned changes for future releases
