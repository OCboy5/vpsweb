# Testing Strategy

This document outlines the testing approach for VPSWeb.

## Current Testing Approach

### Manual Testing
- **End-to-end workflow verification**: Testing complete translation workflows
- **Error handling validation**: Verifying proper error responses
- **Configuration testing**: Testing various configuration scenarios
- **CLI interface testing**: Validating command-line interface functionality

### Testing Commands
```bash
# Run all tests
python -m pytest tests/ -v

# Run specific test file
python -m pytest tests/test_workflow.py -v

# Run with coverage
python -m pytest tests/ --cov=vpsweb --cov-report=html

# Run linting (part of quality checks)
python -m flake8 src/ --max-line-length=88

# Type checking
python -m mypy src/ --ignore-missing-imports
```

## Automated Testing Framework

### Structure
The testing framework is designed around:
- **Pytest-based**: Using pytest for test execution and discovery
- **Asyncio support**: Testing asynchronous code properly
- **Mock providers**: Isolating tests from external API dependencies
- **Integration tests**: Testing complete workflows

### Test Organization
```
tests/
├── unit/                    # Unit tests for individual components
│   ├── test_workflow.py     # Workflow logic tests
│   ├── test_models.py       # Data model tests
│   └── test_providers.py    # LLM provider tests
├── integration/             # Integration tests
│   ├── test_end_to_end.py   # Complete workflow tests
│   └── test_cli.py          # CLI interface tests
└── fixtures/                # Test data and configurations
    ├── sample_poems.txt
    └── test_configs.yaml
```

### Mock Provider Implementation
```python
class MockLLMProvider(BaseLLMProvider):
    def __init__(self, config: dict):
        self.responses = config.get('responses', {})
        self.call_count = 0

    async def generate(self, messages: List[Dict], **kwargs) -> str:
        self.call_count += 1
        # Return predefined responses based on input patterns
        return self._get_mock_response(messages)

    def _get_mock_response(self, messages: List[Dict]) -> str:
        # Logic to return appropriate mock response
        pass
```

### Test Configuration
```yaml
# tests/fixtures/test_config.yaml
test_providers:
  mock:
    responses:
      "initial_translation": "Mock translation result"
      "editor_review": "<editorreview>Mock suggestions</editorreview>"
      "translator_revision": "Mock final translation"
```

## Testing Best Practices

### Test Isolation
- Use mocks for external dependencies
- Each test should be independent
- Clean up resources after each test

### Async Testing
```python
import pytest
from vpsweb.core.workflow import TranslationWorkflow

@pytest.mark.asyncio
async def test_workflow_translation():
    workflow = TranslationWorkflow(test_config)
    input_data = TranslationInput(
        original_poem="Test poem",
        source_lang="English",
        target_lang="Chinese"
    )

    result = await workflow.execute(input_data)
    assert result.revised_translation.revised_translation is not None
```

### Configuration Testing
```python
def test_config_validation():
    # Test valid configuration
    valid_config = {"api_key": "test", "model": "test-model"}
    config = ProviderConfig(**valid_config)
    assert config.api_key == "test"

    # Test invalid configuration
    with pytest.raises(ValueError):
        invalid_config = {"api_key": "", "model": "test-model"}
        ProviderConfig(**invalid_config)
```

### Error Scenario Testing
```python
@pytest.mark.asyncio
async def test_provider_error_handling():
    provider = FailingMockProvider()  # Always raises exceptions
    workflow = TranslationWorkflow(test_config)

    with pytest.raises(ProviderError):
        await workflow.execute(input_data)
```

## Continuous Integration

### Pre-commit Validation
Required quality checks before releases:
```bash
# Code formatting (must pass)
python -m black --check src/ tests/

# Testing (must pass)
python -m pytest tests/

# Import verification (must pass)
python -c "from src.vpsweb.models.config import ModelProviderConfig"
```

### Quality Gates
- All tests must pass
- Code must be properly formatted
- Type checking must succeed
- Critical imports must work

## Future Testing Enhancements

### Planned Improvements
1. **Expanded Test Coverage**: Increase coverage from current baseline to >90%
2. **Performance Testing**: Add benchmarks for translation speed and quality
3. **Load Testing**: Test system behavior under high load
4. **Property-Based Testing**: Use hypothesis for more thorough testing

### Test Data Management
1. **Fixture Management**: Better organization of test data
2. **Test Scenarios**: Standardized test translation scenarios
3. **Regression Tests**: Automated regression detection

### Integration Testing
1. **Real Provider Testing**: Optional tests with real providers
2. **End-to-End Scenarios**: Complex real-world translation scenarios
3. **Configuration Testing**: Test with various configuration combinations

## Debugging Tests

### Running Tests in Debug Mode
```bash
# Run with verbose output
python -m pytest tests/ -v -s

# Stop on first failure
python -m pytest tests/ -x

# Run specific test with debugging
python -m pytest tests/test_workflow.py::test_specific_case -v -s
```

### Common Test Issues
1. **Async/Sync Mixing**: Ensure async tests use proper async/await
2. **Mock Configuration**: Verify mock providers are properly configured
3. **Resource Cleanup**: Ensure proper cleanup in test teardown
4. **Environment Variables**: Set required environment variables for tests

## Testing Resources

- [Pytest Documentation](https://docs.pytest.org/)
- [Async Testing with Pytest](https://pytest-asyncio.readthedocs.io/)
- [Mock Testing Patterns](https://docs.python.org/3/library/unittest.mock.html)

For specific testing questions or issues, refer to the test files in the `tests/` directory for examples and patterns.