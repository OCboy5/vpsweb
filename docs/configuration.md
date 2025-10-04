# Configuration Guide

VPSWeb uses YAML configuration files to manage workflow settings, LLM providers, logging, and storage options. This guide covers all available configuration options and how to customize them for your needs.

## Configuration Structure

VPSWeb configuration follows this hierarchical structure:

```yaml
main:
  workflow:
    name: "professional_poetry_translation"
    version: "1.0.0"
    steps:
      - name: "initial_translation"
        provider: "tongyi"
        model: "qwen-max"
        temperature: 0.7
        max_tokens: 1000
      - name: "editor_review"
        provider: "deepseek"
        model: "deepseek-chat"
        temperature: 0.5
        max_tokens: 800
      - name: "translator_revision"
        provider: "tongyi"
        model: "qwen-max"
        temperature: 0.6
        max_tokens: 1000
  storage:
    output_dir: "./output"
  logging:
    level: "INFO"
    format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    file: "logs/vpsweb.log"
    max_file_size: 10485760
    backup_count: 5

providers:
  providers:
    tongyi:
      api_key: "${TONGYI_API_KEY}"
      base_url: "https://dashscope.aliyuncs.com/compatible-mode/v1"
    deepseek:
      api_key: "${DEEPSEEK_API_KEY}"
      base_url: "https://api.deepseek.com"
```

## Main Configuration

### Workflow Configuration

The `workflow` section defines the translation pipeline steps:

```yaml
workflow:
  name: "professional_poetry_translation"  # Workflow identifier
  version: "1.0.0"                         # Workflow version
  steps:                                   # Ordered list of workflow steps
    - name: "initial_translation"          # Step name (required)
      provider: "tongyi"                   # LLM provider (required)
      model: "qwen-max"                    # Model name (required)
      temperature: 0.7                     # Creativity level (0.0-1.0)
      max_tokens: 1000                     # Maximum tokens per response
      timeout: 60                          # Request timeout in seconds (optional)
```

#### Available Step Names

- `initial_translation`: First translation pass
- `editor_review`: Professional editing and suggestions
- `translator_revision`: Final translation incorporating editor feedback

#### Step Configuration Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `name` | string | required | Step identifier |
| `provider` | string | required | LLM provider name |
| `model` | string | required | Model identifier |
| `temperature` | float | 0.7 | Creativity (0.0-1.0) |
| `max_tokens` | integer | 1000 | Maximum response length |
| `timeout` | integer | 60 | Request timeout in seconds |
| `system_prompt` | string | null | Custom system prompt (optional) |

### Storage Configuration

```yaml
storage:
  output_dir: "./output"                    # Directory for translation outputs
  create_dirs: true                         # Auto-create directories
  file_format: "json"                       # Output file format (json/yaml)
  timestamp_format: "%Y%m%d_%H%M%S"         # Timestamp format for files
```

### Logging Configuration

```yaml
logging:
  level: "INFO"                            # Log level: DEBUG, INFO, WARNING, ERROR
  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
  file: "logs/vpsweb.log"                  # Log file path
  max_file_size: 10485760                  # 10MB max file size
  backup_count: 5                          # Number of backup files
  console: true                            # Enable console output
  json_format: false                       # Use JSON format for logs
```

## Provider Configuration

### Supported LLM Providers

VPSWeb supports multiple LLM providers through a unified interface:

#### Tongyi (Alibaba Cloud)

```yaml
tongyi:
  api_key: "${TONGYI_API_KEY}"              # Environment variable reference
  base_url: "https://dashscope.aliyuncs.com/compatible-mode/v1"
  timeout: 60                               # Request timeout
  max_retries: 3                            # Maximum retry attempts
```

#### DeepSeek

```yaml
deepseek:
  api_key: "${DEEPSEEK_API_KEY}"
  base_url: "https://api.deepseek.com"
  timeout: 60
  max_retries: 3
```

#### OpenAI-Compatible Providers

Any provider with OpenAI-compatible API can be configured:

```yaml
custom_provider:
  api_key: "${CUSTOM_API_KEY}"
  base_url: "https://api.custom-provider.com/v1"
  timeout: 60
  max_retries: 3
```

## Environment Variables

VPSWeb supports environment variable substitution in configuration files:

```yaml
providers:
  providers:
    tongyi:
      api_key: "${TONGYI_API_KEY}"          # Will be replaced with env var value
```

Set environment variables before running VPSWeb:

```bash
export TONGYI_API_KEY="your-tongyi-key"
export DEEPSEEK_API_KEY="your-deepseek-key"
```

## Configuration File Locations

VPSWeb searches for configuration files in this order:

1. `--config` command-line argument
2. `./config/default.yaml`
3. `./config/local.yaml` (for local overrides)
4. `~/.config/vpsweb/default.yaml`

### Example Directory Structure

```
config/
├── default.yaml           # Main configuration
├── local.yaml            # Local overrides (gitignored)
└── production.yaml       # Production configuration
```

## Configuration Examples

### Basic Configuration

```yaml
# config/default.yaml
main:
  workflow:
    name: "basic_poetry_translation"
    version: "1.0.0"
    steps:
      - name: "initial_translation"
        provider: "tongyi"
        model: "qwen-max"
        temperature: 0.7
        max_tokens: 1000
      - name: "editor_review"
        provider: "deepseek"
        model: "deepseek-chat"
        temperature: 0.5
        max_tokens: 800
      - name: "translator_revision"
        provider: "tongyi"
        model: "qwen-max"
        temperature: 0.6
        max_tokens: 1000
  storage:
    output_dir: "./translations"
  logging:
    level: "INFO"
    file: "logs/vpsweb.log"

providers:
  providers:
    tongyi:
      api_key: "${TONGYI_API_KEY}"
      base_url: "https://dashscope.aliyuncs.com/compatible-mode/v1"
    deepseek:
      api_key: "${DEEPSEEK_API_KEY}"
      base_url: "https://api.deepseek.com"
```

### Advanced Configuration

```yaml
# config/advanced.yaml
main:
  workflow:
    name: "advanced_poetry_translation"
    version: "2.0.0"
    steps:
      - name: "initial_translation"
        provider: "tongyi"
        model: "qwen-max"
        temperature: 0.8
        max_tokens: 1500
        timeout: 120
        system_prompt: "You are a professional poetry translator..."
      - name: "editor_review"
        provider: "deepseek"
        model: "deepseek-chat"
        temperature: 0.4
        max_tokens: 1200
        timeout: 90
      - name: "translator_revision"
        provider: "tongyi"
        model: "qwen-max"
        temperature: 0.7
        max_tokens: 1500
        timeout: 120
  storage:
    output_dir: "./output/translations"
    create_dirs: true
    file_format: "json"
    timestamp_format: "%Y%m%d_%H%M%S"
  logging:
    level: "DEBUG"
    format: "%(asctime)s | %(levelname)-8s | %(name)-20s | %(message)s"
    file: "logs/vpsweb_debug.log"
    max_file_size: 20971520
    backup_count: 10
    console: true
    json_format: true

providers:
  providers:
    tongyi:
      api_key: "${TONGYI_API_KEY}"
      base_url: "https://dashscope.aliyuncs.com/compatible-mode/v1"
      timeout: 120
      max_retries: 5
    deepseek:
      api_key: "${DEEPSEEK_API_KEY}"
      base_url: "https://api.deepseek.com"
      timeout: 90
      max_retries: 3
    openai:
      api_key: "${OPENAI_API_KEY}"
      base_url: "https://api.openai.com/v1"
      timeout: 60
      max_retries: 3
```

### Local Override Configuration

```yaml
# config/local.yaml
main:
  logging:
    level: "DEBUG"  # Override log level for development
  storage:
    output_dir: "./local_output"  # Different output directory

providers:
  providers:
    tongyi:
      api_key: "local_test_key"  # Use test key locally
```

## Adding New LLM Providers

### 1. Update Provider Configuration

Add the new provider to your configuration:

```yaml
providers:
  providers:
    new_provider:
      api_key: "${NEW_PROVIDER_API_KEY}"
      base_url: "https://api.new-provider.com/v1"
      timeout: 60
      max_retries: 3
```

### 2. Use in Workflow Steps

Reference the new provider in workflow steps:

```yaml
steps:
  - name: "initial_translation"
    provider: "new_provider"
    model: "new-model"
    temperature: 0.7
    max_tokens: 1000
```

### 3. Set Environment Variable

```bash
export NEW_PROVIDER_API_KEY="your-api-key"
```

## Configuration Validation

VPSWeb validates configuration files on startup. Common validation errors:

- Missing required fields
- Invalid provider names
- Invalid model names for providers
- Invalid temperature values
- Missing API keys

### Validation Example

```bash
# Dry run to validate configuration
vpsweb translate --source English --target Chinese --dry-run

# Output:
# Validating configuration and input...
# ✓ Configuration validation passed
# ✓ Provider validation passed
# ✓ Workflow validation passed
# Dry run completed successfully
```

## Troubleshooting

### Common Issues

1. **Missing API Keys**
   ```
   Error: Missing API key for provider 'tongyi'
   Solution: Set TONGYI_API_KEY environment variable
   ```

2. **Invalid Configuration**
   ```
   Error: Invalid workflow step configuration
   Solution: Check step names and provider configurations
   ```

3. **Network Timeouts**
   ```
   Error: Request timeout for provider 'deepseek'
   Solution: Increase timeout value in configuration
   ```

### Debug Mode

Enable debug logging for detailed troubleshooting:

```yaml
logging:
  level: "DEBUG"
  console: true
```

## Best Practices

1. **Use Environment Variables** for API keys
2. **Create Local Overrides** for development
3. **Version Control** your main configuration
4. **Gitignore** local.yaml files
5. **Use Descriptive Names** for workflow configurations
6. **Test Configurations** with dry-run mode

## Configuration Reference

### Complete Configuration Schema

```yaml
main:
  workflow:
    name: string                    # Workflow identifier
    version: string                 # Workflow version
    steps:
      - name: string               # Step name
        provider: string           # LLM provider
        model: string              # Model name
        temperature: float         # 0.0-1.0
        max_tokens: integer        # > 0
        timeout: integer           # > 0 (optional)
        system_prompt: string      # Custom prompt (optional)
  storage:
    output_dir: string             # Output directory
    create_dirs: boolean           # Auto-create dirs
    file_format: string            # json/yaml
    timestamp_format: string       # strftime format
  logging:
    level: string                  # DEBUG/INFO/WARNING/ERROR
    format: string                 # Log format string
    file: string                   # Log file path
    max_file_size: integer         # Max file size in bytes
    backup_count: integer          # Number of backup files
    console: boolean               # Enable console output
    json_format: boolean           # Use JSON format

providers:
  providers:
    [provider_name]:
      api_key: string              # API key or env var
      base_url: string             # API base URL
      timeout: integer             # Request timeout
      max_retries: integer         # Retry attempts
```

This configuration system provides flexibility for different use cases while maintaining consistency across deployments.