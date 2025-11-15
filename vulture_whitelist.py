# Vulture whitelist for known false positives
# These are items that appear unused but are actually used through dynamic access
# or are part of public APIs that should be kept

# CLI interfaces and services - methods may be used by external callers
src/vpsweb/cli/interfaces.py validate_configuration
src/vpsweb/cli/interfaces.py get_workflow_modes
src/vpsweb/cli/interfaces.py format_workflow_progress
src/vpsweb/cli/interfaces.py extract_article_metadata
src/vpsweb/cli/services.py validate_configuration
src/vpsweb/cli/services.py get_workflow_modes
src/vpsweb/cli/services.py format_workflow_progress
src/vpsweb/cli/services.py extract_article_metadata

# DI container - unused infrastructure that may be needed later
src/vpsweb/core/container.py register_transient
src/vpsweb/core/container.py register_scoped
src/vpsweb/core/container.py register_factory
src/vpsweb/core/container.py create_scope
src/vpsweb/core/container.py get_registrations
src/vpsweb/core/container.py ServiceLocator
src/vpsweb/core/container.py injectable
src/vpsweb/core/container.py auto_register

# Interface definitions - may be used by external implementations
src/vpsweb/core/interfaces.py is_final
src/vpsweb/core/interfaces.py generate_stream
src/vpsweb/core/interfaces.py get_available_models
src/vpsweb/core/interfaces.py list_providers
src/vpsweb/core/interfaces.py register_provider
src/vpsweb/core/interfaces.py validate_template
src/vpsweb/core/interfaces.py register_template
src/vpsweb/core/interfaces.py parse_json
src/vpsweb/core/interfaces.py extract_code_blocks
src/vpsweb/core/interfaces.py get_config
src/vpsweb/core/interfaces.py set_config
src/vpsweb/core/interfaces.py reload_config
src/vpsweb/core/interfaces.py IStorageService
src/vpsweb/core/interfaces.py save
src/vpsweb/core/interfaces.py list_keys
src/vpsweb/core/interfaces.py LogEntry
src/vpsweb/core/interfaces.py log_async
src/vpsweb/core/interfaces.py set_gauge
src/vpsweb/core/interfaces.py get_metrics
src/vpsweb/core/interfaces.py should_retry

# Repository interfaces - may be used by future implementations
src/vpsweb/repository/interfaces.py add_item
src/vpsweb/repository/interfaces.py get_items
src/vpsweb/repository/interfaces.py delete_item
src/vpsweb/repository/interfaces.py update_item
src/vpsweb/repository/interfaces.py get_item
src/vpsweb/repository/interfaces.py search_items
src/vpsweb/repository/interfaces.py count_items
src/vpsweb/repository/interfaces.py update_ai_logs
src/vpsweb/repository/interfaces.py add_human_note
src/vpsweb/repository/interfaces.py get_stats
src/vpsweb/repository/interfaces.py query
src/vpsweb/repository/interfaces.py PaginatedResult
src/vpsweb/repository/interfaces.py IPoemRepository
src/vpsweb/repository/interfaces.py add_poem
src/vpsweb/repository/interfaces.py get_poem_by_id
src/vpsweb/repository/interfaces.py get_poem_by_unique_identifier
src/vpsweb/repository/interfaces.py get_poems_by_author
src/vpsweb/repository/interfaces.py update_poem
src/vpsweb/repository/interfaces.py delete_poem
src/vpsweb/repository/interfaces.py get_all_poems
src/vpsweb/repository/interfaces.py ITranslationRepository
src/vpsweb/repository/interfaces.py add_translation
src/vpsweb/repository/interfaces.py get_translation_by_id
src/vpsweb/repository/interfaces.py get_translations_by_poem_id
src/vpsweb/repository/interfaces.py update_translation
src/vpsweb/repository/interfaces.py delete_translation
src/vpsweb/repository/interfaces.py get_all_translations
src/vpsweb/repository/interfaces.py IAiLogRepository
src/vpsweb/repository/interfaces.py IHumanNoteRepository
src/vpsweb/repository/interfaces.py INoteRepository

# WebUI services - many methods are part of service interfaces
src/vpsweb/webui/services/interfaces.py get_stats
src/vpsweb/webui/services/interfaces.py get_poem_detail
src/vpsweb/webui/services/interfaces.py update_poem
src/vpsweb/webui/services/interfaces.py delete_poem
src/vpsweb/webui/services/interfaces.py get_poem_statistics
src/vpsweb/webui/services/interfaces.py get_translation_list
src/vpsweb/webui/services/interfaces.py create_translation
src/vpsweb/webui/services/interfaces.py delete_translation
src/vpsweb/webui/services/interfaces.py get_workflow_summary
src/vpsweb/webui/services/interfaces.py get_task_status
src/vpsweb/webui/services/interfaces.py cancel_task
src/vpsweb/webui/services/interfaces.py list_tasks
src/vpsweb/webui/services/interfaces.py get_workflow_modes
src/vpsweb/webui/services/interfaces.py get_template_list
src/vpsweb/webui/services/interfaces.py validate_template_data
src/vpsweb/webui/services/interfaces.py handle_http_error
src/vpsweb/webui/services/interfaces.py cleanup_expired_tasks
src/vpsweb/webui/services/interfaces.py create_sse_stream
src/vpsweb/webui/services/interfaces.py send_sse_event
src/vpsweb/webui/services/interfaces.py should_send_heartbeat
src/vpsweb/webui/services/interfaces.py get_all_settings
src/vpsweb/webui/services/interfaces.py update_setting
src/vpsweb/webui/services/interfaces.py send_heartbeat

# WebUI service implementations - interface methods that may be called externally
src/vpsweb/webui/services/services.py get_poem_detail
src/vpsweb/webui/services/services.py create_poem
src/vpsweb/webui/services/services.py update_poem
src/vpsweb/webui/services/services.py delete_poem
src/vpsweb/webui/services/services.py get_poem_statistics
src/vpsweb/webui/services/services.py get_translation_list
src/vpsweb/webui/services/services.py create_translation
src/vpsweb/webui/services/services.py delete_translation
src/vpsweb/webui/services/services.py get_workflow_summary
src/vpsweb/webui/services/services.py get_task_status
src/vpsweb/webui/services/services.py cancel_task
src/vpsweb/webui/services/services.py list_tasks
src/vpsweb/webui/services/services.py get_workflow_modes
src/vpsweb/webui/services/services.py cleanup_expired_tasks
src/vpsweb/webui/services/services.py get_template_list
src/vpsweb/webui/services/services.py validate_template_data
src/vpsweb/webui/services/services.py handle_http_error
src/vpsweb/webui/services/services.py create_sse_stream
src/vpsweb/webui/services/services.py send_sse_event
src/vpsweb/webui/services/services.py should_send_heartbeat
src/vpsweb/webui/services/services.py get_all_settings
src/vpsweb/webui/services/services.py update_setting

# Task management and SSE functionality
src/vpsweb/webui/sse_real.py cleanup_expired_tasks
src/vpsweb/webui/sse_real.py create_real_translation_events
src/vpsweb/webui/task_manager_instance.py get_task_manager
src/vpsweb/webui/task_manager_instance.py reset_task_manager

# Task model methods
src/vpsweb/webui/task_models.py set_progress
src/vpsweb/webui/task_models.py set_running

# Utility methods that may be used externally
src/vpsweb/webui/utils/translation_runner.py get_translation_summary
src/vpsweb/webui/utils/translation_runner.py batch_translate
src/vpsweb/webui/utils/wechat_article_runner.py batch_generate_articles
src/vpsweb/webui/utils/wechat_article_runner.py create_mock_article_result

# Test configuration and fixtures
tests/conftest_di_v2.py ILLMProvider
tests/unit/test_executor.py StepExecutorError