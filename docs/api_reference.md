# API Reference

VPSWeb provides both a Python API and CLI interface for poetry translation. This reference covers all available functions, classes, and data models.

## Python API

### Core Workflow

#### TranslationWorkflow

The main orchestrator for the three-step translation workflow.

```python
from vpsweb.core.workflow import TranslationWorkflow
from vpsweb.models.translation import TranslationInput
from vpsweb.utils.config_loader import load_config

# Load configuration
config = load_config()

# Create workflow instance
workflow = TranslationWorkflow(config.main.workflow)

# Prepare input data
input_data = TranslationInput(
    original_poem="The fog comes on little cat feet.",
    source_lang="English",
    target_lang="Chinese"
)

# Execute workflow
result = await workflow.execute(input_data)

# Access results
print(f"Initial: {result.initial_translation.initial_translation}")
print(f"Revised: {result.revised_translation.revised_translation}")
print(f"Editor suggestions: {result.editor_review.text}")
```

**Methods:**

- `async execute(input_data: TranslationInput) -> TranslationOutput`: Execute the complete translation workflow
- `validate_input(input_data: TranslationInput) -> bool`: Validate input data before execution
- `get_step_config(step_name: str) -> StepConfig`: Get configuration for a specific workflow step

### Data Models

#### TranslationInput

Input data for translation workflow.

```python
from vpsweb.models.translation import TranslationInput

input_data = TranslationInput(
    original_poem="Two roads diverged in a yellow wood,",
    source_lang="English",  # Supported: English, Chinese, Polish
    target_lang="Chinese",  # Supported: English, Chinese, Polish
    metadata={
        "author": "Robert Frost",
        "title": "The Road Not Taken",
        "year": 1916
    }
)
```

**Attributes:**

- `original_poem` (str): The poem text to translate
- `source_lang` (str): Source language (English/Chinese/Polish)
- `target_lang` (str): Target language (English/Chinese/Polish)
- `metadata` (Dict[str, Any]): Optional metadata about the poem

#### TranslationOutput

Complete workflow result containing all translation steps and metadata.

```python
result = await workflow.execute(input_data)

# Access individual components
print(f"Workflow ID: {result.workflow_id}")
print(f"Original: {result.original_poem}")
print(f"Initial translation: {result.initial_translation.initial_translation}")
print(f"Editor review: {result.editor_review.text}")
print(f"Revised translation: {result.revised_translation.revised_translation}")
print(f"Total tokens: {result.total_tokens}")
print(f"Duration: {result.duration_seconds}s")

# Get congregated output
output_dict = result.get_congregated_output()
```

**Attributes:**

- `workflow_id` (str): Unique identifier for this workflow execution
- `original_poem` (str): Original input poem
- `source_lang` (str): Source language
- `target_lang` (str): Target language
- `initial_translation` (InitialTranslation): First translation attempt
- `editor_review` (EditorReview): Professional editing feedback
- `revised_translation` (RevisedTranslation): Final improved translation
- `total_tokens` (int): Total tokens used across all steps
- `duration_seconds` (float): Total execution time
- `full_log` (Dict[str, Any]): Complete workflow execution log

**Methods:**

- `get_congregated_output() -> Dict[str, Any]`: Get all output data as a dictionary
- `save_to_file(file_path: str) -> None`: Save results to JSON file
- `load_from_file(file_path: str) -> TranslationOutput`: Load results from JSON file

#### InitialTranslation

First translation attempt with explanation.

```python
initial = result.initial_translation
print(f"Translation: {initial.initial_translation}")
print(f"Notes: {initial.initial_translation_notes}")
print(f"Tokens: {initial.tokens_used}")
print(f"Model: {initial.model_info}")
```

**Attributes:**

- `initial_translation` (str): The translated poem text
- `initial_translation_notes` (str): Explanation and translation notes
- `tokens_used` (int): Tokens consumed for this step
- `model_info` (Dict[str, Any]): Model and provider information
- `timestamp` (datetime): When this step was executed

#### EditorReview

Professional editing feedback and suggestions.

```python
review = result.editor_review
print(f"Review: {review.text}")
print(f"Summary: {review.summary}")
print(f"Tokens: {review.tokens_used}")
```

**Attributes:**

- `text` (str): Detailed numbered suggestions for improvement
- `summary` (str): Overall assessment summary
- `tokens_used` (int): Tokens consumed for this step
- `model_info` (Dict[str, Any]): Model and provider information
- `timestamp` (datetime): When this step was executed

#### RevisedTranslation

Final translation incorporating editor feedback.

```python
revised = result.revised_translation
print(f"Final translation: {revised.revised_translation}")
print(f"Revision notes: {revised.revised_translation_notes}")
print(f"Tokens: {revised.tokens_used}")
```

**Attributes:**

- `revised_translation` (str): The improved final translation
- `revised_translation_notes` (str): Explanation of improvements made
- `tokens_used` (int): Tokens consumed for this step
- `model_info` (Dict[str, Any]): Model and provider information
- `timestamp` (datetime): When this step was executed

### Configuration Management

#### load_config()

Load and validate configuration from YAML files.

```python
from vpsweb.utils.config_loader import load_config

# Load default configuration
config = load_config()

# Load from specific file
config = load_config("config/custom.yaml")

# Load from directory
config = load_config("config/")

# Access configuration sections
workflow_config = config.main.workflow
provider_config = config.providers
logging_config = config.main.logging
```

**Parameters:**

- `config_path` (Optional[str]): Path to config file or directory. If None, uses default search paths.

**Returns:** `CompleteConfig` object with validated configuration.

### LLM Services

#### LLMFactory

Factory for creating LLM provider instances.

```python
from vpsweb.services.llm.factory import LLMFactory

# Create factory from configuration
factory = LLMFactory()

# Create provider instance
provider = factory.create_llm(
    provider="tongyi",
    model="qwen-max",
    api_key="your-api-key",
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
)

# Generate text
response = await provider.generate(
    messages=[{"role": "user", "content": "Translate this poem..."}],
    temperature=0.7,
    max_tokens=1000
)
```

**Methods:**

- `create_llm(provider: str, model: str, **kwargs) -> BaseLLMProvider`: Create LLM provider instance
- `get_available_providers() -> List[str]`: Get list of available provider names
- `validate_provider_config(provider: str, config: Dict[str, Any]) -> bool`: Validate provider configuration

#### BaseLLMProvider

Abstract base class for LLM providers.

```python
from vpsweb.services.llm.base import BaseLLMProvider

class CustomProvider(BaseLLMProvider):
    def __init__(self, api_key: str, base_url: str, **kwargs):
        self.api_key = api_key
        self.base_url = base_url
        super().__init__(**kwargs)

    async def generate(self, messages: List[Dict[str, str]], **kwargs):
        # Implementation for your provider
        response = await self._make_request(messages, **kwargs)
        return self._parse_response(response)

    def validate_config(self, config: Dict[str, Any]) -> bool:
        # Validate provider-specific configuration
        required = ['api_key', 'base_url']
        return all(key in config for key in required)
```

**Abstract Methods:**

- `async generate(messages: List[Dict[str, str]], **kwargs) -> Dict[str, Any]`: Generate text completion
- `validate_config(config: Dict[str, Any]) -> bool`: Validate provider configuration

### Utility Functions

#### Storage Utilities

```python
from vpsweb.utils.storage import save_translation_result, load_translation_result

# Save result to file
save_translation_result(result, "output/translation.json")

# Load result from file
loaded_result = load_translation_result("output/translation.json")
```

#### Logging Configuration

```python
from vpsweb.utils.logger import setup_logging

# Setup logging from configuration
setup_logging(config.main.logging)

# Or setup with custom settings
setup_logging(
    level="DEBUG",
    file="logs/app.log",
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
```

## CLI Interface

### Basic Translation

```bash
# Translate from file
vpsweb translate --input poem.txt --source English --target Chinese

# Translate from stdin
echo "The fog comes on little cat feet." | vpsweb translate --source English --target Chinese

# With custom output directory
vpsweb translate --input poem.txt --source English --target Chinese --output ./translations/
```

### Advanced Options

```bash
# Custom configuration
vpsweb translate --input poem.txt --source English --target Chinese --config custom.yaml

# Verbose logging
vpsweb translate --input poem.txt --source English --target Chinese --verbose

# Dry run (validate without execution)
vpsweb translate --input poem.txt --source English --target Chinese --dry-run

# All options combined
vpsweb translate \
  --input poem.txt \
  --source English \
  --target Chinese \
  --config custom.yaml \
  --output ./translations/ \
  --verbose \
  --dry-run
```

### CLI Commands

#### translate

Execute the translation workflow.

**Options:**

- `-i, --input FILE`: Input poem file (or read from stdin)
- `-s, --source TEXT`: Source language (required)
- `-t, --target TEXT`: Target language (required)
- `-c, --config DIRECTORY`: Custom configuration directory
- `-o, --output DIRECTORY`: Custom output directory
- `--verbose`: Enable verbose logging
- `--dry-run`: Validate configuration without execution
- `--help`: Show help message

#### version

Show version information.

```bash
vpsweb --version
```

#### help

Show help for commands.

```bash
vpsweb --help
vpsweb translate --help
```

## Error Handling

### Common Exceptions

```python
from vpsweb.core.exceptions import (
    TranslationError,
    ConfigurationError,
    ProviderError,
    ValidationError
)

try:
    result = await workflow.execute(input_data)
except ConfigurationError as e:
    print(f"Configuration error: {e}")
except ProviderError as e:
    print(f"LLM provider error: {e}")
except ValidationError as e:
    print(f"Input validation error: {e}")
except TranslationError as e:
    print(f"Translation workflow error: {e}")
```

### Custom Error Classes

- `TranslationError`: Base class for all translation-related errors
- `ConfigurationError`: Configuration validation or loading errors
- `ProviderError`: LLM provider communication errors
- `ValidationError`: Input data validation errors
- `ParserError`: XML parsing errors from LLM responses

## Examples

### Complete Workflow Example

```python
import asyncio
from vpsweb.core.workflow import TranslationWorkflow
from vpsweb.models.translation import TranslationInput
from vpsweb.utils.config_loader import load_config

async def main():
    # Load configuration
    config = load_config()

    # Create workflow
    workflow = TranslationWorkflow(config.main.workflow)

    # Prepare input
    input_data = TranslationInput(
        original_poem="""Two roads diverged in a yellow wood,
And sorry I could not travel both
And be one traveler, long I stood
And looked down one as far as I could""",
        source_lang="English",
        target_lang="Chinese",
        metadata={
            "author": "Robert Frost",
            "title": "The Road Not Taken",
            "stanza": "first"
        }
    )

    # Execute workflow
    result = await workflow.execute(input_data)

    # Print results
    print("=== TRANSLATION COMPLETE ===")
    print(f"Workflow ID: {result.workflow_id}")
    print(f"Duration: {result.duration_seconds:.2f}s")
    print(f"Total tokens: {result.total_tokens}")
    print()
    print("=== INITIAL TRANSLATION ===")
    print(result.initial_translation.initial_translation)
    print()
    print("=== EDITOR SUGGESTIONS ===")
    print(result.editor_review.text)
    print()
    print("=== REVISED TRANSLATION ===")
    print(result.revised_translation.revised_translation)

    # Save results
    result.save_to_file("translation_result.json")

if __name__ == "__main__":
    asyncio.run(main())
```

### Custom Provider Example

```python
from vpsweb.services.llm.base import BaseLLMProvider

class MyCustomProvider(BaseLLMProvider):
    def __init__(self, api_key: str, base_url: str, **kwargs):
        self.api_key = api_key
        self.base_url = base_url
        super().__init__(**kwargs)

    async def generate(self, messages: List[Dict[str, str]], **kwargs):
        # Implement your provider logic here
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "messages": messages,
            "model": kwargs.get("model", "default"),
            "temperature": kwargs.get("temperature", 0.7),
            "max_tokens": kwargs.get("max_tokens", 1000)
        }

        # Make API request
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    return data
                else:
                    raise ProviderError(f"API request failed: {response.status}")

    def validate_config(self, config: Dict[str, Any]) -> bool:
        required = ['api_key', 'base_url']
        return all(key in config for key in required)
```

This API reference provides comprehensive documentation for using VPSWeb programmatically through both Python and CLI interfaces.