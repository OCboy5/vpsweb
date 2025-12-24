# API Integration Patterns

This document describes the common patterns used for API integrations in VPSWeb v0.7.0, including patterns for Background Briefing Reports (BBR), Server-Sent Events (SSE), and the WebUI API structure.

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

## Server-Sent Events (SSE) Patterns

### SSE Connection Pattern

```python
from fastapi.responses import StreamingResponse
import asyncio
import json

async def stream_task_updates(task_id: str):
    """Stream real-time task updates to client"""

    async def event_stream():
        while True:
            # Get current task state
            task = app.state.tasks.get(task_id)
            if not task:
                yield f"event: error\ndata: {json.dumps({'error': 'Task not found'})}\n\n"
                break

            # Send current status
            yield f"event: status\ndata: {json.dumps({'status': task.status, 'progress': task.progress})}\n\n"

            # Check if completed
            if task.status == "completed":
                yield f"event: completed\ndata: {json.dumps({'result': task.result})}\n\n"
                break
            elif task.status == "failed":
                yield f"event: error\ndata: {json.dumps({'error': task.error})}\n\n"
                break

            await asyncio.sleep(0.2)  # 200ms polling

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"  # Disable nginx buffering
        }
    )
```

### Client-Side SSE Pattern

```javascript
// EventSource connection with automatic reconnection
class TaskMonitor {
    constructor(taskId, onEvent, onError) {
        this.taskId = taskId;
        this.onEvent = onEvent;
        this.onError = onError;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        this.connect();
    }

    connect() {
        this.eventSource = new EventSource(`/api/v1/workflow/tasks/${this.taskId}/stream`);

        this.eventSource.addEventListener('connected', (event) => {
            this.reconnectAttempts = 0;  // Reset on successful connection
            this.onEvent('connected', JSON.parse(event.data));
        });

        this.eventSource.addEventListener('status', (event) => {
            this.onEvent('status', JSON.parse(event.data));
        });

        this.eventSource.addEventListener('step_change', (event) => {
            this.onEvent('step_change', JSON.parse(event.data));
        });

        this.eventSource.addEventListener('completed', (event) => {
            this.onEvent('completed', JSON.parse(event.data));
            this.eventSource.close();
        });

        this.eventSource.addEventListener('error', (event) => {
            this.eventSource.close();
            this.handleError();
        });
    }

    handleError() {
        if (this.reconnectAttempts < this.maxReconnectAttempts) {
            const delay = Math.pow(2, this.reconnectAttempts) * 1000;  // Exponential backoff
            setTimeout(() => {
                this.reconnectAttempts++;
                this.connect();
            }, delay);
        } else {
            this.onError('Max reconnection attempts reached');
        }
    }
}

// Usage
const monitor = new TaskMonitor(
    taskId,
    (eventType, data) => {
        updateProgressBar(data.progress);
        updateStatus(data.status);
    },
    (error) => {
        console.error('SSE Error:', error);
    }
);
```

### Event Broadcasting Pattern

```python
from typing import Set
import asyncio
from dataclasses import dataclass

@dataclass
class SSEConnection:
    queue: asyncio.Queue
    task_id: str

class SSEManager:
    def __init__(self):
        self.connections: Set[SSEConnection] = set()

    async def add_connection(self, task_id: str) -> asyncio.Queue:
        queue = asyncio.Queue()
        self.connections.add(SSEConnection(queue, task_id))
        return queue

    async def remove_connection(self, queue: asyncio.Queue):
        self.connections.discard(queue)

    async def broadcast_to_task(self, task_id: str, event_type: str, data: dict):
        """Broadcast event to all connections for a specific task"""
        message = f"event: {event_type}\ndata: {json.dumps(data)}\n\n"

        for conn in list(self.connections):
            if conn.task_id == task_id:
                try:
                    conn.queue.put_nowait(message)
                except asyncio.QueueFull:
                    # Remove dead connections
                    self.connections.discard(conn)
```

## Background Briefing Report (BBR) Patterns

### BBR Generation Pattern

```python
from vpsweb.services.bbr_generator import BBRGenerator
from vpsweb.models.bbr import BackgroundBriefingReport

async def generate_bbr(poem_id: str) -> BackgroundBriefingReport:
    """Generate a Background Briefing Report for a poem"""

    # Get poem from database
    poem = await poem_service.get_poem(poem_id)

    # Initialize BBR generator
    bbr_gen = BBRGenerator()

    try:
        # Generate BBR with contextual analysis
        bbr = await bbr_gen.generate_bbr(
            title=poem.title,
            author=poem.author,
            content=poem.original_text,
            language=poem.source_lang
        )

        # Save to database
        saved_bbr = await bbr_service.create_bbr(
            poem_id=poem_id,
            content=bbr.content,
            model_provider=bbr.model_provider,
            input_tokens=bbr.input_tokens,
            output_tokens=bbr.output_tokens
        )

        return saved_bbr

    except BBRGenerationError as e:
        logger.error(f"BBR generation failed for poem {poem_id}: {e}")
        raise
```

### BBR API Endpoint Pattern

```python
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel

router = APIRouter(prefix="/api/v1/bbr", tags=["bbr"])

class BBRRequest(BaseModel):
    poem_id: str
    force_regenerate: bool = False

@router.post("/generate")
async def generate_bbr_endpoint(
    request: BBRRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Generate BBR for a poem"""

    # Check if BBR already exists
    existing_bbr = await bbr_service.get_latest_bbr(request.poem_id)

    if existing_bbr and not request.force_regenerate:
        return {"bbr_id": existing_bbr.id, "status": "exists"}

    # Start background generation
    background_tasks.add_task(generate_and_save_bbr, request.poem_id)

    return {"status": "generating", "poem_id": request.poem_id}

@router.get("/{poem_id}")
async def get_bbr(poem_id: str, db: Session = Depends(get_db)):
    """Get latest BBR for a poem"""

    bbr = await bbr_service.get_latest_bbr(poem_id)

    if not bbr:
        raise HTTPException(status_code=404, detail="BBR not found")

    return bbr

@router.get("/{bbr_id}/stream")
async def stream_bbr_generation(bbr_id: str):
    """Stream BBR generation progress (if implemented)"""

    async def bbr_stream():
        # Similar to task streaming but for BBR generation
        pass

    return StreamingResponse(bbr_stream(), media_type="text/event-stream")
```

### BBR Integration with Translation Pattern

```python
async def translate_with_bbr(
    poem_id: str,
    target_lang: str,
    workflow_mode: str
) -> Translation:
    """Translate poem using BBR for context"""

    # Get poem
    poem = await poem_service.get_poem(poem_id)

    # Get or generate BBR
    bbr = await bbr_service.get_latest_bbr(poem_id)
    if not bbr:
        bbr = await bbr_service.generate_bbr(poem_id)

    # Include BBR in translation prompt
    enhanced_prompt = build_translation_prompt(
        poem=poem,
        bbr_content=bbr.content,
        target_lang=target_lang
    )

    # Execute translation workflow
    translation = await workflow_service.execute_translation(
        prompt=enhanced_prompt,
        workflow_mode=workflow_mode
    )

    return translation

def build_translation_prompt(poem: Poem, bbr_content: str, target_lang: str) -> str:
    """Build translation prompt with BBR context"""

    return f"""
    Translate the following poem to {target_lang}.

    POEM:
    Title: {poem.title}
    Author: {poem.author}

    {poem.original_text}

    BACKGROUND CONTEXT:
    {bbr_content}

    Please provide a translation that respects the cultural and historical context provided above.
    """
```

## WebUI API Patterns

### Poem Management API Pattern

```python
from fastapi import APIRouter, Depends, Query
from typing import List, Optional

router = APIRouter(prefix="/api/v1/poems", tags=["poems"])

@router.get("/", response_model=List[PoemResponse])
async def list_poems(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    search: Optional[str] = Query(None),
    author: Optional[str] = Query(None),
    source_lang: Optional[str] = Query(None),
    is_selected: Optional[bool] = Query(None),
    db: Session = Depends(get_db)
):
    """List poems with filtering and pagination"""

    filters = {}
    if search:
        filters["search"] = search
    if author:
        filters["author"] = author
    if source_lang:
        filters["source_lang"] = source_lang
    if is_selected is not None:
        filters["is_selected"] = is_selected

    poems = await poem_service.get_poems(
        db=db,
        skip=skip,
        limit=limit,
        filters=filters
    )

    return poems

@router.post("/", response_model=PoemResponse)
async def create_poem(
    poem_data: PoemCreate,
    db: Session = Depends(get_db)
):
    """Create a new poem"""

    poem = await poem_service.create_poem(db=db, poem_data=poem_data)
    return poem

@router.get("/{poem_id}/translations", response_model=List[TranslationResponse])
async def get_poem_translations(
    poem_id: str,
    target_lang: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """Get all translations for a poem"""

    translations = await translation_service.get_translations_for_poem(
        db=db,
        poem_id=poem_id,
        target_lang=target_lang
    )

    return translations
```

### Statistics API Pattern

```python
@router.get("/dashboard", response_model=DashboardStats)
async def get_dashboard_stats(db: Session = Depends(get_db)):
    """Get dashboard statistics"""

    stats = await stats_service.get_dashboard_stats(db)

    return {
        "total_poets": stats.total_poets,
        "total_poems": stats.total_poems,
        "total_translations": stats.total_translations,
        "ai_translations": stats.ai_translations,
        "human_translations": stats.human_translations,
        "recent_activity": stats.recent_activity
    }

@router.get("/analytics", response_model=AnalyticsResponse)
async def get_analytics(
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    group_by: str = Query("day", regex="^(day|week|month)$"),
    db: Session = Depends(get_db)
):
    """Get analytics data"""

    analytics = await stats_service.get_analytics(
        db=db,
        date_from=date_from,
        date_to=date_to,
        group_by=group_by
    )

    return analytics
```
## Workflow API Patterns

### Translation Workflow Pattern

```python
from fastapi import APIRouter, BackgroundTasks, HTTPException

router = APIRouter(prefix="/api/v1/workflow", tags=["workflow"])

class TranslationRequest(BaseModel):
    poem_id: str
    target_lang: str
    workflow_mode: str = "hybrid"  # hybrid|manual|reasoning|non_reasoning

@router.post("/translate")
async def start_translation_workflow(
    request: TranslationRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Start automated translation workflow"""

    # Validate poem exists
    poem = await poem_service.get_poem(request.poem_id)
    if not poem:
        raise HTTPException(status_code=404, detail="Poem not found")

    # Create task record
    task = await workflow_service.create_translation_task(
        db=db,
        poem_id=request.poem_id,
        target_lang=request.target_lang,
        workflow_mode=request.workflow_mode
    )

    # Start background processing
    background_tasks.add_task(
        execute_translation_workflow,
        task.id,
        request.poem_id,
        request.target_lang,
        request.workflow_mode
    )

    return {
        "task_id": task.id,
        "status": "pending",
        "poem_id": request.poem_id,
        "target_lang": request.target_lang
    }

@router.get("/tasks/{task_id}/stream")
async def stream_task_progress(task_id: str):
    """Stream task progress via SSE"""
    return StreamingResponse(
        stream_task_updates(task_id),
        media_type="text/event-stream"
    )

@router.get("/tasks/{task_id}")
async def get_task_status(task_id: str, db: Session = Depends(get_db)):
    """Get current task status"""
    task = await workflow_service.get_task(db, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task

@router.delete("/tasks/{task_id}")
async def cancel_task(task_id: str, db: Session = Depends(get_db)):
    """Cancel running task"""
    success = await workflow_service.cancel_task(db, task_id)
    if not success:
        raise HTTPException(status_code=404, detail="Task not found or cannot be cancelled")
    return {"status": "cancelled"}
```

### Manual Workflow Pattern

```python
router = APIRouter(prefix="/api/v1/manual", tags=["manual_workflow"])

class ManualSessionCreate(BaseModel):
    poem_id: str
    target_lang: str

@router.post("/sessions")
async def create_manual_session(
    request: ManualSessionCreate,
    db: Session = Depends(get_db)
):
    """Create manual translation session"""

    session = await manual_workflow_service.create_session(
        db=db,
        poem_id=request.poem_id,
        target_lang=request.target_lang
    )

    return {
        "session_id": session.id,
        "poem_id": session.poem_id,
        "target_lang": session.target_lang,
        "status": "created"
    }

@router.post("/sessions/{session_id}/steps/{step_name}")
async def submit_manual_step(
    session_id: str,
    step_name: str,
    content: str,
    db: Session = Depends(get_db)
):
    """Submit content for manual workflow step"""

    result = await manual_workflow_service.submit_step(
        db=db,
        session_id=session_id,
        step_name=step_name,
        content=content
    )

    return result
```

## Security Patterns

### Enhanced API Key Management

```python
from typing import Optional
import os
from cryptography.fernet import Fernet

class SecureConfig:
    def __init__(self):
        self.encryption_key = os.getenv("FERNET_KEY", Fernet.generate_key())
        self.cipher = Fernet(self.encryption_key)

    def encrypt_api_key(self, api_key: str) -> str:
        """Encrypt API key for storage"""
        return self.cipher.encrypt(api_key.encode()).decode()

    def decrypt_api_key(self, encrypted_key: str) -> str:
        """Decrypt stored API key"""
        return self.cipher.decrypt(encrypted_key.encode()).decode()

    def get_provider_config(self, provider_name: str) -> dict:
        """Get provider configuration with decrypted API keys"""
        config = load_config_from_db(provider_name)

        if "encrypted_api_key" in config:
            config["api_key"] = self.decrypt_api_key(config["encrypted_api_key"])
            del config["encrypted_api_key"]

        return config
```

### Input Validation with Pydantic V2

```python
from pydantic import BaseModel, validator, Field
import bleach

class PoemCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)
    author: str = Field(..., min_length=1, max_length=200)
    source_lang: str = Field(..., regex="^[a-z]{2}(-[A-Z]{2})?$")
    original_text: str = Field(..., min_length=1, max_length=50000)

    @validator('title', 'author')
    def sanitize_html_fields(cls, v):
        """Sanitize HTML from text fields"""
        return bleach.clean(v, tags=[], strip=True)

    @validator('original_text')
    def preserve_poem_formatting(cls, v):
        """Clean HTML but preserve poem formatting"""
        # Allow basic formatting but remove scripts and dangerous content
        allowed_tags = ['p', 'br', 'stanza', 'line']
        return bleach.clean(v, tags=allowed_tags, strip=True)

    class Config:
        validate_assignment = True
```

### Rate Limiting Pattern

```python
from fastapi import Request, HTTPException
from collections import defaultdict
import time
from typing import Dict

class RateLimiter:
    def __init__(self, requests_per_minute: int = 60):
        self.requests_per_minute = requests_per_minute
        self.requests: Dict[str, list] = defaultdict(list)

    def is_allowed(self, client_id: str) -> bool:
        """Check if client is allowed to make request"""
        now = time.time()
        minute_ago = now - 60

        # Remove old requests
        self.requests[client_id] = [
            req_time for req_time in self.requests[client_id]
            if req_time > minute_ago
        ]

        # Check if under limit
        if len(self.requests[client_id]) >= self.requests_per_minute:
            return False

        # Add current request
        self.requests[client_id].append(now)
        return True

# Usage middleware
rate_limiter = RateLimiter(requests_per_minute=100)

@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    client_id = request.client.host

    if not rate_limiter.is_allowed(client_id):
        raise HTTPException(
            status_code=429,
            detail="Too many requests",
            headers={"Retry-After": "60"}
        )

    response = await call_next(request)
    return response
```

## Testing Patterns

### API Endpoint Testing with SSE

```python
import pytest
import json
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

@pytest.mark.asyncio
async def test_translation_workflow_with_sse(client: TestClient, db: Session, sample_poem):
    """Test complete translation workflow with SSE streaming"""

    # Start translation
    request_data = {
        "poem_id": sample_poem.id,
        "target_lang": "zh-CN",
        "workflow_mode": "hybrid"
    }

    response = client.post("/api/v1/workflow/translate", json=request_data)
    assert response.status_code == 200

    task_data = response.json()
    task_id = task_data["task_id"]

    # Test SSE streaming
    with client.stream("GET", f"/api/v1/workflow/tasks/{task_id}/stream") as response:
        assert response.status_code == 200
        assert "text/event-stream" in response.headers["content-type"]

        events = []
        for line in response.iter_lines():
            if line:
                if line.startswith(b"data:"):
                    event_data = json.loads(line[5:].decode())
                    events.append(event_data)

        # Verify received events
        assert len(events) > 0
        assert any(e.get("event") == "connected" for e in events)
        assert any(e.get("event") == "completed" for e in events)

    # Verify final result
    response = client.get(f"/api/v1/workflow/tasks/{task_id}")
    assert response.status_code == 200
    final_task = response.json()
    assert final_task["status"] == "completed"
```

### BBR Generation Testing

```python
from unittest.mock import AsyncMock, patch

@pytest.mark.asyncio
async def test_bbr_generation_with_mock():
    """Test BBR generation with mocked LLM provider"""

    mock_provider = AsyncMock()
    mock_provider.generate.return_value = """
    # Background Briefing Report

    ## Cultural Context
    This poem was written during the Tang Dynasty (618-907 CE)...

    ## Linguistic Analysis
    The poem uses classical Chinese poetic forms with regulated meter...

    ## Translation Considerations
    Key challenges include translating cultural references and maintaining...
    """

    with patch('vpsweb.services.llm.factory.LLMFactory.create_provider') as mock_factory:
        mock_factory.return_value = mock_provider

        bbr_gen = BBRGenerator()
        bbr = await bbr_gen.generate_bbr(
            title="静夜思",
            author="李白",
            content="床前明月光，疑是地上霜...",
            language="zh-CN"
        )

        assert "Tang Dynasty" in bbr.content
        assert "静夜思" in bbr.content
        mock_provider.generate.assert_called_once()

        # Verify token tracking
        assert bbr.input_tokens > 0
        assert bbr.output_tokens > 0
        assert bbr.total_tokens > 0
```

These patterns ensure consistent, reliable, and maintainable API integrations across the VPSWeb codebase, with comprehensive support for modern features like SSE streaming, BBR generation, and secure API practices.
