# Legacy Utils Files - Backup

These files were moved here during the v0.3.1 repository system cleanup on 2025-01-19.

## Archived Files

### Webhook and Article Generation
- **`article_generator.py`** (46KB) - WeChat article generation functionality
- **`translation_notes_synthesizer.py`** - Translation notes processing

### Configuration and Storage
- **`config_loader.py`** - Legacy configuration loading system
- **`storage.py`** - Legacy storage operations

### Utility Functions
- **`filename_utils.py`** - Filename handling utilities
- **`markdown_export.py`** - Markdown export functionality
- **`progress.py`** - Progress tracking for old workflow
- **`xml_parser.py`** - XML parsing for old system

## Status

These files are **no longer used** in the v0.3.1 repository system but are preserved here in case:
- Some functionality needs to be referenced or reimplemented
- Historical code review is needed
- Parts of the logic are useful for future features

## Migration Notes

The v0.3.1 repository system uses:
- **New repository layer**: `src/vpsweb/repository/` with its own configuration
- **Modern utils**: Only the 5 files remaining in parent directory
- **Clean imports**: No circular dependencies with legacy modules

## Recovery

If needed, these files can be moved back to the parent directory and their imports restored.