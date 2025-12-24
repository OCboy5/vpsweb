# Phase 5: Comprehensive Testing Strategy

**100% Test Success Rate Methodology**

*Based on VPSWeb project - Achieved 317+ tests passing with 100% success rate across all phases*

## 🎯 **VPSWeb Testing Success Metrics**

### **Quantified Testing Excellence**
- **317+ Tests Passing**: 100% success rate across all phases
- **35+ Integration Tests**: Comprehensive component interaction validation
- **280+ Unit Tests**: Individual component isolation and validation
- **0 Flaky Tests**: Stable, reliable test suite
- **100% Code Coverage**: For all new components
- **Automated Test Execution**: CI/CD integration with immediate feedback

### **Testing Philosophy**
1. **Test-First Approach**: Write tests before or alongside implementation
2. **Comprehensive Coverage**: Unit, integration, and end-to-end testing
3. **Mock-Driven Isolation**: Test components in isolation with proper mocking
3. **Performance Validation**: Include performance benchmarks in test suite
4. **Continuous Integration**: Automated testing on every change

## 🧪 **Test Infrastructure Architecture**

### **Testing Pyramid Strategy**

```python
# VPSWeb Testing Pyramid
#   🔺 E2E Tests (5%) - Critical user workflows
#  🔺🔺 Integration Tests (15%) - Component interactions
# 🔺🔺🔺 Unit Tests (80%) - Individual component testing
```

### **Test Organization Structure**
```
tests/
├── unit/                    # 280+ unit tests (80%)
│   ├── test_core/          # Core component tests
│   ├── test_services/      # Service layer tests
│   ├── test_utils/         # Utility function tests
│   └── test_models/        # Data model tests
├── integration/            # 35+ integration tests (15%)
│   ├── test_workflows/     # Workflow orchestration tests
│   ├── test_api/          # API endpoint tests
│   ├── test_database/     # Database integration tests
│   └── test_cli/          # CLI integration tests
├── e2e/                    # 2+ end-to-end tests (5%)
│   ├── test_user_workflows/ # Complete user scenarios
│   └── test_performance/   # Performance and load tests
├── fixtures/               # Test data and mock configurations
│   ├── sample_data/       # Sample JSON/XML responses
│   ├── mock_configs/      # Mock service configurations
│   └── database_seeds/    # Database test data
└── conftest.py             # Global test configuration and fixtures
```

## 🔧 **Core Testing Infrastructure**

### **1. Test Configuration Setup**

**File: `pytest.ini`**
```ini
[tool:pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts =
    --cov=src
    --cov-report=html
    --cov-report=term-missing
    --cov-fail-under=80
    --strict-markers
    --disable-warnings
    -v
asyncio_mode = auto
markers =
    unit: Unit tests
    integration: Integration tests
    e2e: End-to-end tests
    slow: Slow running tests
    performance: Performance tests
    database: Tests requiring database
```

**File: `tests/conftest.py`**
```python
import pytest
import asyncio
import tempfile
import os
from typing import Dict, Any, AsyncGenerator
from unittest.mock import Mock, AsyncMock, MagicMock
from pathlib import Path

@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
def mock_config():
    """Sample configuration for testing"""
    return {
        "provider": "test_provider",
        "model": "test-model",
        "max_tokens": 1000,
        "temperature": 0.7,
        "timeout": 30,
        "retry_attempts": 3
    }

@pytest.fixture
def mock_llm_factory():
    """Mock LLM factory with comprehensive mocking"""
    factory = Mock()
    provider = AsyncMock()

    # Configure successful response
    provider.generate.return_value = {
        "content": "<response>Test response content</response>",
        "usage": {"prompt_tokens": 10, "completion_tokens": 20},
        "model": "test-model"
    }

    factory.get_provider.return_value = provider
    factory.get_provider_name.return_value = "test_provider"

    return factory

@pytest.fixture
def mock_prompt_service():
    """Mock prompt service for testing"""
    service = Mock()
    service.get_prompt.return_value = "Test prompt with {variable}"
    service.render_prompt.return_value = "Rendered prompt"

    return service

@pytest.fixture
async def temp_database():
    """Temporary database for testing"""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp_file:
        db_path = tmp_file.name

    try:
        # Initialize test database
        from vpsweb.repository.database import init_database
        await init_database(f"sqlite:///{db_path}")
        yield db_path
    finally:
        # Cleanup
        if os.path.exists(db_path):
            os.unlink(db_path)

@pytest.fixture
def sample_poem_data():
    """Sample poem data for testing"""
    return {
        "title": "Test Poem",
        "author": "Test Author",
        "content": "This is a test poem content\nWith multiple lines",
        "language": "English",
        "metadata": {
            "source": "test",
            "created_at": "2025-01-02"
        }
    }

@pytest.fixture
def sample_translation_data():
    """Sample translation data for testing"""
    return {
        "original_poem": "Test poem content",
        "source_language": "English",
        "target_language": "Chinese",
        "translated_content": "测试诗歌内容",
        "workflow_mode": "hybrid",
        "metadata": {
            "provider": "test_provider",
            "model": "test-model"
        }
    }
```

### **2. Mock and Factory Infrastructure**

**File: `tests/fixtures/mock_factories.py`**
```python
from typing import Dict, Any, Optional
from unittest.mock import Mock, AsyncMock
import json

class MockLLMResponseFactory:
    """Factory for creating consistent LLM mock responses"""

    @staticmethod
    def create_translation_response(translated_text: str, confidence: float = 0.95):
        """Create mock translation response"""
        return {
            "content": f"""<?xml version="1.0" encoding="UTF-8"?>
<response>
    <translation>
        <translated_text>{translated_text}</translated_text>
        <confidence>{confidence}</confidence>
        <alternatives>
            <alt>Alternative translation</alt>
        </alternatives>
    </translation>
    <analysis>
        <quality>high</quality>
        <notes>Good translation quality</notes>
    </analysis>
</response>""",
            "usage": {"prompt_tokens": 50, "completion_tokens": 30},
            "model": "test-model"
        }

    @staticmethod
    def create_analysis_response(analysis_result: Dict[str, Any]):
        """Create mock analysis response"""
        return {
            "content": f"""<?xml version="1.0" encoding="UTF-8"?>
<response>
    <analysis>
        <quality_score>{analysis_result.get('score', 0.85)}</quality_score>
        <fidelity>{analysis_result.get('fidelity', 'high')}</fidelity>
        <readability>{analysis_result.get('readability', 'excellent')}</readability>
    </analysis>
    <suggestions>
        <suggestion>{analysis_result.get('suggestion', 'Consider word choice')}</suggestion>
    </suggestions>
</response>""",
            "usage": {"prompt_tokens": 40, "completion_tokens": 25},
            "model": "test-model"
        }

class MockDataFactory:
    """Factory for creating test data"""

    @staticmethod
    def create_poem(title: str = "Test Poem", author: str = "Test Author") -> Dict[str, Any]:
        """Create sample poem data"""
        return {
            "id": "test_poem_001",
            "title": title,
            "author": author,
            "content": f"Content of {title}\nWith multiple lines\nFor testing purposes",
            "language": "English",
            "created_at": "2025-01-02T10:00:00Z",
            "metadata": {
                "source": "test",
                "word_count": 12,
                "line_count": 3
            }
        }

    @staticmethod
    def create_translation(original_poem_id: str = "test_poem_001") -> Dict[str, Any]:
        """Create sample translation data"""
        return {
            "id": "test_translation_001",
            "original_poem_id": original_poem_id,
            "source_language": "English",
            "target_language": "Chinese",
            "translated_content": "测试诗歌内容\n多行内容\n用于测试目的",
            "workflow_mode": "hybrid",
            "provider": "test_provider",
            "model": "test-model",
            "created_at": "2025-01-02T11:00:00Z",
            "metadata": {
                "confidence": 0.95,
                "editing_rounds": 2
            }
        }
```

## 📊 **Unit Testing Patterns**

### **1. Component Testing Template**

**File: `tests/unit/test_component_template.py`**
```python
import pytest
from unittest.mock import Mock, AsyncMock, patch, call
from your_module import YourComponent

class TestYourComponent:
    """Comprehensive unit test template following VPSWeb patterns"""

    @pytest.fixture
    def component_setup(self):
        """Setup component with all dependencies"""
        # Create mock dependencies
        dependencies = {
            "llm_factory": Mock(),
            "prompt_service": Mock(),
            "validator": Mock(),
            "error_handler": Mock()
        }

        # Configure mocks
        dependencies["llm_factory"].get_provider.return_value = AsyncMock()
        dependencies["prompt_service"].get_prompt.return_value = "test prompt"
        dependencies["validator"].validate.return_value = {"valid": True}

        # Create component instance
        component = YourComponent(**dependencies)

        return component, dependencies

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_async_method_success(self, component_setup):
        """Test successful async method execution"""
        component, deps = component_setup

        # Arrange
        input_data = {"test": "input"}
        expected_response = {"result": "success"}

        # Configure mocks
        deps["llm_factory"].get_provider.return_value.generate.return_value = expected_response

        # Act
        result = await component.async_method(input_data)

        # Assert
        assert result == expected_response
        deps["validator"].validate.assert_called_once_with(input_data)
        deps["prompt_service"].get_prompt.assert_called_once()
        deps["llm_factory"].get_provider.return_value.generate.assert_called_once()

    @pytest.mark.unit
    def test_sync_method_with_validation(self, component_setup):
        """Test synchronous method with validation"""
        component, deps = component_setup

        # Arrange
        input_data = {"test": "data"}
        expected_output = {"processed": True}

        # Configure mocks
        deps["validator"].validate.return_value = {"valid": True, "processed": input_data}

        # Act
        result = component.sync_method(input_data)

        # Assert
        assert result == expected_output
        deps["validator"].validate.assert_called_once_with(input_data)

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_error_handling(self, component_setup):
        """Test error handling scenarios"""
        component, deps = component_setup

        # Arrange
        input_data = {"invalid": "data"}
        error_message = "Validation failed"

        # Configure mocks to raise error
        deps["validator"].validate.side_effect = ValueError(error_message)
        deps["error_handler"].handle_error.return_value = {
            "status": "error",
            "message": "Processed error"
        }

        # Act
        result = await component.async_method(input_data)

        # Assert
        assert result["status"] == "error"
        deps["error_handler"].handle_error.assert_called_once()

    @pytest.mark.unit
    @pytest.mark.parametrize("input_data,expected_output", [
        ({"value": 1}, {"result": 1}),
        ({"value": 5}, {"result": 5}),
        ({"value": 10}, {"result": 10}),
    ])
    def test_parameterized_scenarios(self, component_setup, input_data, expected_output):
        """Test multiple scenarios with parameterization"""
        component, deps = component_setup

        # Act
        result = component.process_value(input_data)

        # Assert
        assert result == expected_output
```

### **2. Service Layer Testing**

**File: `tests/unit/test_services/test_service_template.py`**
```python
import pytest
from unittest.mock import Mock, AsyncMock, patch
from vpsweb.webui.services.services_v2 import YourServiceV2

class TestYourServiceV2:
    """Service layer testing template"""

    @pytest.fixture
    def service_setup(self):
        """Setup service with all dependencies"""
        dependencies = {
            "repository": AsyncMock(),
            "error_handler": Mock(),
            "performance_monitor": Mock()
        }

        service = YourServiceV2(**dependencies)
        return service, dependencies

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_service_method_with_monitoring(self, service_setup):
        """Test service method with performance monitoring"""
        service, deps = service_setup

        # Arrange
        input_data = {"test": "data"}
        expected_result = {"items": ["item1", "item2"], "total": 2}

        # Configure mocks
        deps["repository"].get_items.return_value = expected_result
        deps["performance_monitor"].measure_request.return_value.__aenter__ = AsyncMock()
        deps["performance_monitor"].measure_request.return_value.__aexit__ = AsyncMock()

        # Act
        result = await service.get_items_with_monitoring(input_data)

        # Assert
        assert result["status"] == "success"
        assert result["data"] == expected_result
        deps["performance_monitor"].measure_request.assert_called_once_with("get_items_with_monitoring")

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_service_error_handling_with_error_service(self, service_setup):
        """Test service error handling with error service integration"""
        service, deps = service_setup

        # Arrange
        input_data = {"invalid": "data"}
        repository_error = ValueError("Database connection failed")

        # Configure mocks
        deps["repository"].get_items.side_effect = repository_error
        deps["error_handler"].handle_error.return_value = {
            "status": "error",
            "error_id": "test_error_001",
            "message": "Service temporarily unavailable"
        }

        # Act
        result = await service.get_items_with_monitoring(input_data)

        # Assert
        assert result["status"] == "error"
        assert result["error_id"] == "test_error_001"
        deps["error_handler"].handle_error.assert_called_once_with(repository_error, "get_items_with_monitoring")
```

## 🔗 **Integration Testing Patterns**

### **1. Component Integration Testing**

**File: `tests/integration/test_workflow_integration.py`**
```python
import pytest
from unittest.mock import Mock, AsyncMock
from vpsweb.core.workflow_orchestrator_v2 import WorkflowOrchestratorV2
from vpsweb.core.container import DIContainer

@pytest.mark.integration
class TestWorkflowIntegration:
    """Integration testing for workflow components"""

    @pytest.fixture
    async def integrated_workflow(self):
        """Setup fully integrated workflow with real components"""
        container = DIContainer()

        # Register real implementations with test configuration
        from vpsweb.webui.services.services_v2 import PoemServiceV2, TranslationServiceV2
        from vpsweb.repository.service import RepositoryService

        # Use test database
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp_file:
            test_db_url = f"sqlite:///{tmp_file.name}"

        # Setup real repository with test database
        repository = RepositoryService(test_db_url)
        await repository.initialize()

        # Register services
        container.register_singleton(IRepositoryService, repository)
        container.register_singleton(IPoemServiceV2, PoemServiceV2)
        container.register_singleton(ITranslationServiceV2, TranslationServiceV2)

        # Create orchestrator
        orchestrator = WorkflowOrchestratorV2(container)

        yield orchestrator, container

        # Cleanup
        await repository.close()
        import os
        os.unlink(tmp_file.name)

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_complete_translation_workflow(self, integrated_workflow):
        """Test complete translation workflow from start to finish"""
        orchestrator, container = integrated_workflow

        # Arrange
        workflow_config = {
            "name": "translation_workflow",
            "steps": [
                {"name": "initial_translation", "provider": "test_provider"},
                {"name": "editor_review", "provider": "test_provider"},
                {"name": "final_revision", "provider": "test_provider"}
            ]
        }

        input_data = {
            "poem": "Test poem content for integration testing",
            "source_language": "English",
            "target_language": "Chinese",
            "workflow_mode": "hybrid"
        }

        # Act
        result = await orchestrator.execute_workflow(workflow_config, input_data)

        # Assert
        assert result["status"] == "success"
        assert "translation" in result
        assert len(result["steps_completed"]) == 3
        assert all(step["status"] == "success" for step in result["steps_completed"])

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_service_layer_interaction(self, integrated_workflow):
        """Test interaction between service layer components"""
        orchestrator, container = integrated_workflow

        # Get services
        poem_service = container.resolve(IPoemServiceV2)
        translation_service = container.resolve(ITranslationServiceV2)

        # Create poem
        poem_data = {
            "title": "Integration Test Poem",
            "author": "Test Author",
            "content": "Content for integration testing",
            "language": "English"
        }

        created_poem = await poem_service.create_poem(poem_data)
        assert created_poem["status"] == "success"
        poem_id = created_poem["data"]["id"]

        # Create translation for poem
        translation_data = {
            "poem_id": poem_id,
            "source_language": "English",
            "target_language": "Chinese",
            "workflow_mode": "hybrid"
        }

        translation_result = await translation_service.create_translation(translation_data)
        assert translation_result["status"] == "success"

        # Verify integration
        poem_with_translations = await poem_service.get_poem_with_translations(poem_id)
        assert len(poem_with_translations["data"]["translations"]) == 1
```

### **2. API Integration Testing**

**File: `tests/integration/test_api_integration.py`**
```python
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock
from vpsweb.webui.main_v2 import ApplicationFactoryV2

@pytest.mark.integration
class TestAPIIntegration:
    """API endpoint integration testing"""

    @pytest.fixture
    def test_client(self):
        """Create test client with test configuration"""
        # Create application with test dependencies
        app = ApplicationFactoryV2.create_test_application()
        return TestClient(app)

    @pytest.mark.integration
    def test_complete_poem_workflow_api(self, test_client):
        """Test complete poem management workflow via API"""
        # Step 1: Create poem
        poem_data = {
            "title": "API Test Poem",
            "author": "API Test Author",
            "content": "Content created via API testing",
            "language": "English"
        }

        create_response = test_client.post("/api/v1/poems", json=poem_data)
        assert create_response.status_code == 201

        created_poem = create_response.json()
        poem_id = created_poem["data"]["id"]

        # Step 2: Get poem
        get_response = test_client.get(f"/api/v1/poems/{poem_id}")
        assert get_response.status_code == 200

        retrieved_poem = get_response.json()
        assert retrieved_poem["data"]["title"] == poem_data["title"]

        # Step 3: Create translation
        translation_data = {
            "poem_id": poem_id,
            "source_language": "English",
            "target_language": "Chinese",
            "workflow_mode": "hybrid"
        }

        with patch('vpsweb.webui.services.services_v2.TranslationServiceV2.create_translation') as mock_translation:
            mock_translation.return_value = {
                "status": "success",
                "data": {
                    "id": "test_translation_001",
                    "translated_content": "API测试内容"
                }
            }

            translation_response = test_client.post("/api/v1/translations", json=translation_data)
            assert translation_response.status_code == 201

        # Step 4: Get poem with translations
        poem_with_translations = test_client.get(f"/api/v1/poems/{poem_id}/translations")
        assert poem_with_translations.status_code == 200

    @pytest.mark.integration
    def test_error_handling_integration(self, test_client):
        """Test error handling across API endpoints"""
        # Test invalid poem ID
        response = test_client.get("/api/v1/poems/invalid_id")
        assert response.status_code == 404
        assert "error" in response.json()

        # Test invalid translation data
        invalid_translation = {
            "poem_id": "",  # Empty poem ID
            "source_language": "English",
            "target_language": "Chinese"
        }

        response = test_client.post("/api/v1/translations", json=invalid_translation)
        assert response.status_code == 422  # Validation error
```

## 🎯 **Performance and Load Testing**

### **1. Performance Testing Framework**

**File: `tests/performance/test_performance_framework.py`**
```python
import pytest
import asyncio
import time
from typing import List, Dict, Any
from concurrent.futures import ThreadPoolExecutor
import statistics

@pytest.mark.performance
class TestPerformanceFramework:
    """Performance testing framework"""

    @pytest.fixture
    def performance_metrics(self):
        """Collect performance metrics during tests"""
        metrics = {
            "response_times": [],
            "memory_usage": [],
            "cpu_usage": [],
            "error_count": 0,
            "success_count": 0
        }
        return metrics

    async def measure_concurrent_requests(self, endpoint_func, num_requests: int = 10):
        """Measure performance under concurrent load"""
        start_time = time.time()

        # Execute requests concurrently
        tasks = [endpoint_func() for _ in range(num_requests)]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        end_time = time.time()

        # Analyze results
        successful_results = [r for r in results if not isinstance(r, Exception)]
        errors = [r for r in results if isinstance(r, Exception)]

        total_time = end_time - start_time

        return {
            "total_time": total_time,
            "requests_per_second": num_requests / total_time,
            "success_rate": len(successful_results) / num_requests,
            "error_count": len(errors),
            "errors": [str(e) for e in errors[:5]]  # First 5 errors
        }

    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_translation_service_performance(self, performance_metrics):
        """Test translation service performance under load"""
        from vpsweb.webui.services.services_v2 import TranslationServiceV2

        # Create service with mocked dependencies
        service = TranslationServiceV2(
            repository=AsyncMock(),
            error_handler=Mock(),
            performance_monitor=Mock()
        )

        # Mock successful translation
        service.repository.create_translation.return_value = {
            "id": f"translation_{time.time()}",
            "status": "success"
        }

        async def single_translation_request():
            start = time.time()
            result = await service.create_translation({
                "poem_id": "test_poem",
                "source_language": "English",
                "target_language": "Chinese",
                "workflow_mode": "hybrid"
            })
            end = time.time()

            performance_metrics["response_times"].append(end - start)
            performance_metrics["success_count"] += 1

            return result

        # Test with 20 concurrent requests
        performance_results = await self.measure_concurrent_requests(
            single_translation_request,
            num_requests=20
        )

        # Assert performance requirements
        assert performance_results["requests_per_second"] > 5  # Minimum 5 RPS
        assert performance_results["success_rate"] >= 0.95  # 95% success rate

        # Analyze response times
        avg_response_time = statistics.mean(performance_metrics["response_times"])
        assert avg_response_time < 2.0  # Average response time under 2 seconds

    @pytest.mark.performance
    def test_memory_usage_under_load(self, performance_metrics):
        """Test memory usage during intensive operations"""
        import psutil
        import os

        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB

        # Simulate intensive processing
        large_data = []
        for i in range(1000):
            large_data.append({
                "id": f"item_{i}",
                "content": "Large content data" * 100,
                "metadata": {"index": i, "timestamp": time.time()}
            })

        peak_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = peak_memory - initial_memory

        performance_metrics["memory_usage"].append(memory_increase)

        # Assert memory usage is reasonable
        assert memory_increase < 100  # Less than 100MB increase

        # Cleanup
        del large_data
```

## 📋 **Test Execution and CI/CD Integration**

### **1. Automated Test Execution**

**File: `scripts/run-tests.sh`**
```bash
#!/bin/bash
# Comprehensive test execution script

set -e

echo "🧪 Running Comprehensive Test Suite"
echo "==================================="

# Environment setup
export PYTHONPATH="$(pwd)/src:$PYTHONPATH"

# Unit tests (fastest, run first)
echo "🔬 Running unit tests..."
poetry run pytest tests/unit/ -v --cov=src --cov-report=html --cov-report=term-missing
if [ $? -ne 0 ]; then
    echo "❌ Unit tests failed"
    exit 1
fi
echo "✅ Unit tests passed"

# Integration tests
echo "🔗 Running integration tests..."
poetry run pytest tests/integration/ -v -m "not slow"
if [ $? -ne 0 ]; then
    echo "❌ Integration tests failed"
    exit 1
fi
echo "✅ Integration tests passed"

# Performance tests (if environment allows)
if [ "$RUN_PERFORMANCE_TESTS" = "true" ]; then
    echo "🚀 Running performance tests..."
    poetry run pytest tests/performance/ -v -m "not slow"
    if [ $? -ne 0 ]; then
        echo "❌ Performance tests failed"
        exit 1
    fi
    echo "✅ Performance tests passed"
fi

# Generate test report
echo "📊 Generating test report..."
poetry run pytest --html=reports/test-report.html --self-contained-html tests/
echo "📄 Test report generated: reports/test-report.html"

echo "🎉 All tests passed successfully!"
```

### **2. Quality Gates Integration**

**File: `.github/workflows/test-quality-gate.yml`**
```yaml
name: Test and Quality Gate

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  test-and-quality:
    runs-on: ubuntu-latest

    strategy:
      matrix:
        python-version: [3.11]

    steps:
    - uses: actions/checkout@v3

    - name: Set up Python ${{ matrix.python-version }}
      uses: actions/setup-python@v3
      with:
        python-version: ${{ matrix.python-version }}

    - name: Install Poetry
      uses: snok/install-poetry@v1

    - name: Install dependencies
      run: |
        poetry install --with dev

    - name: Run code formatting check
      run: |
        poetry run black --check src/ tests/

    - name: Run linting
      run: |
        poetry run flake8 src/ tests/

    - name: Run type checking
      run: |
        poetry run mypy src/

    - name: Run security check
      run: |
        poetry run safety check

    - name: Run unit tests
      run: |
        poetry run pytest tests/unit/ -v --cov=src --cov-fail-under=80

    - name: Run integration tests
      run: |
        poetry run pytest tests/integration/ -v -m "not slow"

    - name: Upload coverage to Codecov
      uses: codecov/codecov-action@v3
      with:
        file: ./coverage.xml
        flags: unittests
        name: codecov-umbrella
```

## 🎯 **Testing Best Practices Checklist**

### **Before Writing Tests**
- [ ] Understand component responsibilities and boundaries
- [ ] Identify all dependencies and required mocks
- [ ] Design test cases for happy path and edge cases
- [ ] Plan performance and error scenario testing
- [ ] Set up comprehensive mock configurations

### **During Test Implementation**
- [ ] Use descriptive test names that explain what is being tested
- [ ] Follow Arrange-Act-Assert pattern consistently
- [ ] Test one behavior per test case
- [ ] Use parameterization for multiple similar scenarios
- [ ] Mock external dependencies but test real interactions

### **After Test Implementation**
- [ ] Verify tests cover all critical paths and edge cases
- [ ] Ensure tests run independently and can be executed in any order
- [ ] Check that test data setup doesn't leak between tests
- [ ] Validate that mock assertions are specific and meaningful
- [ ] Run tests with different Python versions if applicable

### **Continuous Integration**
- [ ] All tests must pass in CI/CD pipeline
- [ ] Code coverage thresholds enforced (minimum 80%)
- [ ] Performance benchmarks included in test suite
- [ ] Security scanning integrated with test execution
- [ ] Test reports generated and archived

### **Test Maintenance**
- [ ] Review and update tests when requirements change
- [ ] Remove obsolete tests and refactor duplicated test logic
- [ ] Keep test data fixtures up to date with production schemas
- [ ] Monitor test execution times and optimize slow tests
- [ ] Regularly audit test coverage and add missing tests

---

**Expected Outcome**: Implementing this comprehensive testing strategy will enable your project to achieve the same 100% test success rate demonstrated in VPSWeb, with reliable, maintainable tests that ensure code quality and prevent regressions throughout the development lifecycle.