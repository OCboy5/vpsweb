# API Integration Patterns

This document describes the common patterns used for API integrations in VPSWeb.

## Provider Factory Pattern

VPSWeb uses a factory pattern for LLM provider abstraction:

```python
# Standard provider instantiation
from vpsweb.services.llm.factory import LLMFactory

provider = LLMFactory.create_provider(
    provider_type="tongyi",
    config=provider_config
)

# Standard workflow execution
response = await provider.generate(
    messages=messages,
    temperature=0.7,
    max_tokens=4096
)
```

## Adding New Providers

1. **Create Provider Class**:
```python
from vpsweb.services.llm.base import BaseLLMProvider

class NewProvider(BaseLLMProvider):
    async def generate(self, messages: List[Dict], **kwargs) -> str:
        # Implementation here
        pass

    def get_provider_name(self) -> str:
        return "new_provider"
```

2. **Update Factory**:
```python
# In factory.py
def create_provider(provider_type: str, config: dict) -> BaseLLMProvider:
    if provider_type == "new_provider":
        return NewProvider(config)
    # ... existing providers
```

3. **Add Configuration**:
```yaml
# In models.yaml
new_provider:
  api_key: "${NEW_PROVIDER_API_KEY}"
  base_url: "https://api.newprovider.com"
  model: "new-model"
```

## Error Handling Patterns

### Custom Exceptions
```python
class ProviderError(Exception):
    """Base exception for provider errors"""
    pass

class RateLimitError(ProviderError):
    """Rate limit exceeded"""
    pass

class AuthenticationError(ProviderError):
    """Authentication failed"""
    pass
```

### Graceful Degradation
```python
try:
    response = await primary_provider.generate(messages)
except ProviderError:
    # Fallback to backup provider
    response = await backup_provider.generate(messages)
```

### Retry Logic
```python
import asyncio
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
async def generate_with_retry(provider, messages):
    return await provider.generate(messages)
```

## Configuration Patterns

### Environment Variables
```python
import os
from typing import Optional

def get_env_var(key: str, default: Optional[str] = None) -> str:
    value = os.getenv(key)
    if value is None:
        if default is not None:
            return default
        raise ValueError(f"Environment variable {key} is required")
    return value
```

### Configuration Validation
```python
from pydantic import BaseModel, validator

class ProviderConfig(BaseModel):
    api_key: str
    base_url: str
    model: str

    @validator('api_key')
    def api_key_not_empty(cls, v):
        if not v:
            raise ValueError('API key cannot be empty')
        return v
```

## Logging Patterns

### Structured Logging
```python
import logging

logger = logging.getLogger(__name__)

async def generate_with_logging(provider, messages):
    logger.info("Generating response", extra={
        'provider': provider.get_provider_name(),
        'message_count': len(messages),
        'model': provider.config.model
    })

    try:
        response = await provider.generate(messages)
        logger.info("Response generated successfully", extra={
            'response_length': len(response),
            'provider': provider.get_provider_name()
        })
        return response
    except Exception as e:
        logger.error("Generation failed", extra={
            'error': str(e),
            'provider': provider.get_provider_name()
        })
        raise
```

## Async Patterns

### Concurrent Processing
```python
async def process_multiple_translations(texts: List[str]) -> List[str]:
    tasks = [translate_single(text) for text in texts]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    return results
```

### Resource Management
```python
import aiohttp

async def with_http_session():
    async with aiohttp.ClientSession() as session:
        # Use session for multiple requests
        pass
```

## Testing Patterns

### Mock Providers
```python
class MockLLMProvider(BaseLLMProvider):
    def __init__(self, config: dict):
        self.responses = config.get('responses', {})

    async def generate(self, messages: List[Dict], **kwargs) -> str:
        # Return predefined response based on input
        return self.responses.get(str(messages), "Mock response")
```

### Integration Tests
```python
import pytest
from vpsweb.services.llm.factory import LLMFactory

@pytest.mark.asyncio
async def test_provider_factory():
    config = {"api_key": "test_key", "model": "test_model"}
    provider = LLMFactory.create_provider("mock", config)

    response = await provider.generate([{"role": "user", "content": "test"}])
    assert response == "Mock response"
```

## Security Patterns

### API Key Management
```python
def load_secure_config():
    # Load from environment or secure storage
    return {
        'api_key': os.getenv('PROVIDER_API_KEY'),
        # Never hardcode secrets
    }
```

### Input Validation
```python
def validate_messages(messages: List[Dict]) -> None:
    for message in messages:
        if not isinstance(message, dict):
            raise ValueError("Message must be a dictionary")
        if 'role' not in message or 'content' not in message:
            raise ValueError("Message must have 'role' and 'content'")
```

These patterns ensure consistent, reliable, and maintainable API integrations across the VPSWeb codebase.