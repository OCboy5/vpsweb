# VPSWeb Testing Guide v0.3.2

**Complete Testing Guide for VPSWeb Central Repository & Web UI System**

This guide provides comprehensive testing procedures for the VPSWeb v0.3.2 central repository and web interface system.

---

## 📋 Table of Contents

1. [Setup & Configuration](#-setup--configuration)
2. [Web UI Testing](#-web-ui-testing)
3. [API Testing](#-api-testing)
4. [VPSWeb Workflow Integration](#-vpsweb-workflow-integration)
5. [Database & Performance Testing](#-database--performance-testing)
6. [Advanced Test Scenarios](#-advanced-test-scenarios)
7. [Troubleshooting](#-troubleshooting)

---

## 🔧 Setup & Configuration

### Prerequisites

- Python 3.8+ installed
- Poetry package manager
- Git
- SQLite3 (usually pre-installed)

### 1. Automated Setup

```bash
# Run the complete setup script
./scripts/setup.sh

# Or verify existing setup
./scripts/setup.sh --verify-only
```

### 2. Environment Configuration

Edit `.env.local` file and add your AI provider API keys:

```bash
# Required for translation workflow
TONGYI_API_KEY=your_tongyi_api_key_here
DEEPSEEK_API_KEY=your_deepseek_api_key_here

# Optional
OPENAI_API_KEY=your_openai_api_key_here

# Repository configuration
REPO_ROOT=./repository_root
REPO_DATABASE_URL=sqlite+aiosqlite:///./repository_root/repo.db
REPO_HOST=127.0.0.1
REPO_PORT=8000
REPO_DEBUG=false
DEV_MODE=true

# Logging
VERBOSE_LOGGING=true
LOG_FORMAT=text
```

### 3. Database Initialization

```bash
# Initialize database using dedicated script
./scripts/setup-database.sh init

# Verify database creation
./scripts/setup-database.sh status
```

### 4. Start Development Server

```bash
# Method 1: Use the start script (recommended)
./scripts/start.sh

# Method 2: Manual startup
export PYTHONPATH="$(pwd)/src:$PYTHONPATH"
poetry run uvicorn vpsweb.webui.main:app \
    --host 127.0.0.1 \
    --port 8000 \
    --reload \
    --log-level debug
```

### 5. Verify Setup

Visit these URLs to verify everything is working:

- **Main Web Interface**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health
- **Alternative API Docs**: http://localhost:8000/redoc

---

## 🌐 Web UI Testing

### Dashboard Testing

**URL**: http://localhost:8000

**Test Cases**:
- [ ] **Real-time Statistics Display**
  - Total poems count
  - Total translations count
  - Recent activity summary
  - Performance metrics

- [ ] **Recent Poems Display**
  - Poem list with metadata
  - Proper formatting of Chinese/English text
  - Clickable poem details
  - Pagination (if applicable)

- [ ] **Quick Action Buttons**
  - "Add New Poem" functionality
  - "View All Poems" navigation
  - "Statistics" dashboard link
  - Responsive design

- [ ] **Responsive Design**
  - Mobile view (width < 768px)
  - Tablet view (768px - 1024px)
  - Desktop view (> 1024px)
  - Touch interactions on mobile

### Poem Management Testing

**Navigation**: Dashboard → Poems → Manage Poems

**Test Cases**:
- [ ] **Create New Poem**
  ```bash
  # Test via Web UI
  1. Click "Add New Poem"
  2. Fill in: Poet Name (陶渊明), Poem Title (歸園田居), Language (Chinese), Poem Text
  3. Submit and verify creation
  4. Check poem appears in list
  ```

- [ ] **Edit Existing Poem**
  ```bash
  1. Click on any poem in the list
  2. Click "Edit" button
  3. Modify poem text or metadata
  4. Save changes and verify updates
  ```

- [ ] **Delete Poem**
  ```bash
  1. Select a poem from the list
  2. Click "Delete" button
  3. Confirm deletion in modal
  4. Verify poem is removed from database
  ```

- [ ] **Search and Filter**
  ```bash
  1. Test search by poet name
  2. Test search by poem title
  3. Test language filtering
  4. Test date range filtering
  ```

### Translation Interface Testing

**Navigation**: Dashboard → Translations

**Test Cases**:
- [ ] **Add Translation to Poem**
  ```bash
  1. Select an existing poem
  2. Click "Add Translation"
  3. Fill in translation language and text
  4. Set quality rating (1-10)
  5. Add human notes
  6. Save and verify translation appears
  ```

- [ ] **Edit Translation Quality**
  ```bash
  1. Click on existing translation
  2. Modify quality rating
  3. Update human notes
  4. Save changes and verify updates
  ```

- [ ] **Side-by-Side Comparison**
  ```bash
  1. Click on poem with multiple translations
  2. Verify comparison view shows original + translations
  3. Test filtering by quality rating
  4. Test sorting by date/quality
  ```

### Error Handling Testing

**Test Cases**:
- [ ] **404 Error Pages**
  - Visit non-existent URLs
  - Verify user-friendly error pages
  - Test navigation back to home

- [ ] **Validation Errors**
  - Submit empty forms
  - Enter invalid data formats
  - Verify validation messages appear

- [ ] **Timeout Errors**
  - Test with slow operations
  - Verify timeout handling works
  - Check error message clarity

---

## 🔌 API Testing

### Interactive API Testing

**URL**: http://localhost:8000/docs

**Procedure**:
1. Open Swagger UI in browser
2. Test each endpoint systematically
3. Verify request/response schemas
4. Test authentication (if implemented)

### Manual API Testing

#### Health and Statistics Endpoints

```bash
# Health check
curl -X GET http://localhost:8000/health

# Expected response: {"status": "healthy", "timestamp": "...", "version": "0.3.2"}

# Repository statistics
curl -X GET http://localhost:8000/api/statistics

# Expected response: JSON with total_poems, total_translations, etc.
```

#### Poem Management APIs

```bash
# List all poems
curl -X GET http://localhost:8000/api/poems

# Get specific poem (replace POEM_ID)
curl -X GET http://localhost:8000/api/poems/POEM_ID

# Create new poem
curl -X POST http://localhost:8000/api/poems \
  -H "Content-Type: application/json" \
  -d '{
    "poet_name": "陶渊明",
    "poem_title": "饮酒",
    "source_language": "chinese",
    "poem_text": "结庐在人境，而无车马喧。问君何能尔？心远地自偏。采菊东篱下，悠然见南山。山气日夕佳，飞鸟相与还。此中有真意，欲辨已忘言。"
  }'

# Update poem (replace POEM_ID)
curl -X PUT http://localhost:8000/api/poems/POEM_ID \
  -H "Content-Type: application/json" \
  -d '{
    "poet_name": "陶渊明",
    "poem_title": "饮酒·其五",
    "source_language": "chinese",
    "poem_text": "结庐在人境，而无车马喧。问君何能尔？心远地自偏。采菊东篱下，悠然见南山。"
  }'

# Delete poem (replace POEM_ID)
curl -X DELETE http://localhost:8000/api/poems/POEM_ID
```

#### Translation APIs

```bash
# Get translations for a poem (replace POEM_ID)
curl -X GET http://localhost:8000/api/poems/POEM_ID/translations

# Add translation to poem (replace POEM_ID)
curl -X POST http://localhost:8000/api/translations \
  -H "Content-Type: application/json" \
  -d '{
    "poem_id": "POEM_ID",
    "target_language": "english",
    "translation_text": "I built my cottage among the throngs of humanity, yet there is no noise of carriage and horse.",
    "quality_rating": 8,
    "human_notes": "Classic Taoist sentiment about finding peace in chaos"
  }'

# Update translation (replace TRANSLATION_ID)
curl -X PUT http://localhost:8000/api/translations/TRANSLATION_ID \
  -H "Content-Type: application/json" \
  -d '{
    "translation_text": "I built my cottage among the throngs of humanity, yet there is no noise of carriage or horse.",
    "quality_rating": 9,
    "human_notes": "Updated with better understanding of Taoist philosophy"
  }'
```

### Integration API Testing

#### Translation Workflow Integration

```bash
# Validate translation workflow (dry run)
curl -X POST http://localhost:8000/api/validate-translation \
  -H "Content-Type: application/json" \
  -d '{
    "poem_id": "POEM_ID",
    "source_lang": "chinese",
    "target_lang": "english",
    "workflow_mode": "hybrid"
  }'

# Execute full translation workflow
curl -X POST http://localhost:8000/api/translate \
  -H "Content-Type: application/json" \
  -d '{
    "poem_id": "POEM_ID",
    "source_lang": "chinese",
    "target_lang": "english",
    "workflow_mode": "hybrid"
  }'

# Expected response: JSON with workflow results, timing, and token usage
```

### API Error Testing

```bash
# Test 404 errors
curl -X GET http://localhost:8000/api/poems/nonexistent-id

# Test validation errors
curl -X POST http://localhost:8000/api/poems \
  -H "Content-Type: application/json" \
  -d '{"invalid": "data"}'

# Test timeout errors (long-running operations)
curl -X POST http://localhost:8000/api/translate \
  -H "Content-Type: application/json" \
  -d '{
    "poem_id": "POEM_ID",
    "source_lang": "chinese",
    "target_lang": "english",
    "workflow_mode": "reasoning"  # Slower mode for timeout testing
  }' \
  --max-time 30  # Force timeout
```

---

## 🔄 VPSWeb Workflow Integration

### Traditional CLI Workflow Testing

```bash
# Set environment
export PYTHONPATH="$(pwd)/src:$PYTHONPATH"

# Test basic CLI translation (creates files AND repository entries)
echo "静夜思 | 李白 | 床前明月光，疑是地上霜。举头望明月，低头思故乡。" | vpsweb translate -s chinese -t english -w hybrid

# Expected results:
# 1. JSON and Markdown files created in outputs/
# 2. Poem and translation entries created in repository
# 3. Workflow execution logged

# Verify CLI created repository entries
curl -X GET http://localhost:8000/api/poems | grep "静夜思"
curl -X GET http://localhost:8000/api/statistics
```

### WeChat Article Generation Integration

```bash
# Generate WeChat article from translation JSON
vpsweb generate-article -i outputs/json/李白_静夜思_chinese_english_hybrid_*.json

# Expected results:
# 1. WeChat article created in outputs/wechat_articles/
# 2. HTML template properly formatted
# 3. Translation data integrated from repository

# Test WeChat article publishing (if configured)
vpsweb publish-article -d outputs/wechat_articles/
```

### End-to-End Workflow Test

```bash
# Step 1: Create poem via Web UI
# 1. Visit http://localhost:8000
# 2. Click "Add New Poem"
# 3. Enter: "陶渊明 | 歸園田居 | 少无适俗韵，性本爱丘山..."
# 4. Save and note the poem ID

# Step 2: Add translation via Web UI
# 1. Navigate to the poem
# 2. Click "Add Translation"
# 3. Enter English translation
# 4. Set quality rating and add notes
# 5. Save

# Step 3: Run CLI translation on same poem
echo "歸園田居 | 陶渊明 | 少无适俗韵，性本爱丘山..." | vpsweb translate -s chinese -t english -w hybrid

# Step 4: Verify integration
# 1. Check repository has both manual and CLI translations
curl -X GET http://localhost:8000/api/poems/YOUR_POEM_ID/translations
# 2. Verify statistics updated
curl -X GET http://localhost:8000/api/statistics
# 3. Check dashboard shows new activity

# Step 5: Generate WeChat article
vpsweb generate-article -i outputs/json/陶渊明_歸園田居_chinese_english_hybrid_*.json
```

### Background Task Testing

```bash
# Start server and monitor logs
./scripts/start.sh &
SERVER_PID=$!

# In another terminal, monitor logs
tail -f logs/vpsweb.log

# Trigger background task via API
curl -X POST http://localhost:8000/api/translate \
  -H "Content-Type: application/json" \
  -d '{
    "poem_id": "TEST_POEM_ID",
    "source_lang": "chinese",
    "target_lang": "english",
    "workflow_mode": "hybrid"
  }'

# Observe background task execution in logs
# Verify task completion and result storage

# Cleanup
kill $SERVER_PID
```

---

## 📊 Database & Performance Testing

### Database Verification

```bash
# Check database structure
sqlite3 repository_root/repo.db ".schema"

# Verify data integrity
sqlite3 repository_root/repo.db "SELECT COUNT(*) FROM poems;"
sqlite3 repository_root/repo.db "SELECT COUNT(*) FROM translations;"
sqlite3 repository_root/repo.db "SELECT COUNT(*) FROM ai_logs;"
sqlite3 repository_root/repo.db "SELECT COUNT(*) FROM human_notes;"

# Test database performance (explain query plans)
sqlite3 repository_root/repo.db "EXPLAIN QUERY PLAN SELECT * FROM poems WHERE poet_name = '陶渊明';"
sqlite3 repository_root/repo.db "EXPLAIN QUERY PLAN SELECT * FROM translations WHERE target_language = 'english';"
```

### Performance Testing

```bash
# Run performance demo scripts
python scripts/demo_alembic_migrations.py --action status
python scripts/demo_rotating_logging.py --mode demo

# Test API response times
time curl -X GET http://localhost:8000/api/statistics
time curl -X GET http://localhost:8000/api/poems

# Load testing with concurrent requests
for i in {1..10}; do
  curl -X GET http://localhost:8000/api/statistics &
done
wait
```

### Database Migration Testing

```bash
# Test migration system
cd src/vpsweb/repository

# Check current migration version
poetry run alembic current

# Create test migration (for development)
poetry run alembic revision --autogenerate -m "test_migration"

# Upgrade to latest
poetry run alembic upgrade head

# Downgrade one version
poetry run alembic downgrade -1

# Upgrade again
poetry run alembic upgrade head

# Clean up test migration
# Edit migrations to remove test, then:
poetry run alembic upgrade head
```

### Logging System Testing

```bash
# Test rotating file logging
python scripts/demo_rotating_logging.py --mode test --count 1000

# Verify log rotation works
ls -la logs/
tail -f logs/vpsweb.log

# Test different log levels
# Edit .env.local to change LOG_LEVEL, then restart server
```

---

## 🎯 Advanced Test Scenarios

### Concurrency Testing

```bash
# Test concurrent API requests
for i in {1..20}; do
  curl -X GET http://localhost:8000/api/statistics &
done
wait

# Test concurrent poem creation
for i in {1..5}; do
  curl -X POST http://localhost:8000/api/poems \
    -H "Content-Type: application/json" \
    -d "{\"poet_name\": \"Test Poet $i\", \"poem_title\": \"Test Poem $i\", \"source_language\": \"english\", \"poem_text\": \"Test content $i\"}" &
done
wait

# Verify data integrity
curl -X GET http://localhost:8000/api/statistics
```

### Timeout and Error Recovery Testing

```bash
# Test workflow timeout protection
curl -X POST http://localhost:8000/api/translate \
  -H "Content-Type: application/json" \
  -d '{
    "poem_id": "EXISTING_POEM_ID",
    "source_lang": "chinese",
    "target_lang": "english",
    "workflow_mode": "reasoning"
  }' \
  --max-time 60  # Force client timeout

# Verify graceful error handling
curl -X GET http://localhost:8000/api/poems/invalid-poem-id

# Test database connection failure (simulate)
# Stop server, run requests, verify error handling
```

### Mobile Device Testing

```bash
# Use browser developer tools for mobile testing:
# 1. Open Chrome DevTools (F12)
# 2. Toggle device toolbar (Ctrl+Shift+M)
# 3. Test different device presets:
#    - iPhone 12 Pro (390x844)
#    - iPad (768x1024)
#    - Android (360x640)

# Test mobile-specific functionality:
# - Touch interactions
# - Responsive navigation
# - Mobile keyboard compatibility
# - Viewport scaling
```

### Configuration Testing

```bash
# Test different configuration scenarios:
# 1. Edit .env.local and change:
#    - REPO_DEBUG=true/false
#    - VERBOSE_LOGGING=true/false
#    - DEV_MODE=true/false
# 2. Restart server
# 3. Verify configuration changes take effect
# 4. Test appropriate behavior for each setting

# Test API key validation:
# 1. Remove API keys from .env.local
# 2. Restart server
# 3. Test translation workflow
# 4. Verify proper error handling for missing credentials
```

### Data Integrity Testing

```bash
# Test data consistency across operations:
# 1. Create poem via API
POEM_RESPONSE=$(curl -s -X POST http://localhost:8000/api/poems \
  -H "Content-Type: application/json" \
  -d '{"poet_name": "Test Poet", "poem_title": "Test Poem", "source_language": "english", "poem_text": "Test content"}')

POEM_ID=$(echo $POEM_RESPONSE | jq -r '.id')

# 2. Add translation
curl -X POST http://localhost:8000/api/translations \
  -H "Content-Type: application/json" \
  -d "{\"poem_id\": \"$POEM_ID\", \"target_language\": \"chinese\", \"translation_text\": \"测试内容\", \"quality_rating\": 8}"

# 3. Verify data consistency
curl -X GET http://localhost:8000/api/poems/$POEM_ID
curl -X GET http://localhost:8000/api/statistics

# 4. Test cascade delete
curl -X DELETE http://localhost:8000/api/poems/$POEM_ID

# 5. Verify translation also deleted
curl -X GET http://localhost:8000/api/translations | grep $POEM_ID  # Should return empty
```

---

## 🔧 Troubleshooting

### Common Issues and Solutions

#### Server Won't Start

```bash
# Check PYTHONPATH
echo $PYTHONPATH
# Should include: /path/to/vpsweb/src

# Check dependencies
poetry install

# Check for port conflicts
lsof -i :8000
# Kill conflicting processes:
pkill -f uvicorn

# Check database permissions
ls -la repository_root/
chmod 755 repository_root/
```

#### API Calls Fail

```bash
# Check API keys
cat .env.local | grep API_KEY

# Test AI provider connectivity
poetry run python -c "
from vpsweb.services.llm.factory import LLMFactory
try:
    factory = LLMFactory()
    provider = factory.get_provider('tongyi')
    print('✅ AI provider factory works')
except Exception as e:
    print(f'❌ AI provider error: {e}')
"

# Check server logs
tail -f logs/vpsweb.log
```

#### Database Issues

```bash
# Reset database completely
./scripts/reset.sh

# Manual database recreation
rm -f repository_root/repo.db
mkdir -p repository_root
cd src/vpsweb/repository
poetry run alembic upgrade head
cd -

# Check migration status
cd src/vpsweb/repository
poetry run alembic current
poetry run alembic history
cd -
```

#### Performance Issues

```bash
# Check database indexes
sqlite3 repository_root/repo.db ".indexes"

# Analyze slow queries
sqlite3 repository_root/repo.db "EXPLAIN QUERY PLAN SELECT * FROM poems WHERE poet_name = '陶渊明';"

# Monitor resource usage
top -p $(pgrep -f uvicorn)
```

#### Translation Workflow Issues

```bash
# Test translation workflow directly
export PYTHONPATH="$(pwd)/src:$PYTHONPATH"
poetry run python -c "
from vpsweb.core.workflow import TranslationWorkflow
from vpsweb.models.translation import TranslationInput
# Test basic workflow functionality
print('Testing workflow system...')
"

# Check prompt templates exist
ls -la config/prompts/

# Check configuration files
cat config/default.yaml | head -20
cat config/models.yaml | head -20
```

### Debug Mode

```bash
# Enable debug mode
# Edit .env.local: REPO_DEBUG=true
# Then restart server with verbose logging:
export PYTHONPATH="$(pwd)/src:$PYTHONPATH"
poetry run uvicorn vpsweb.webui.main:app \
    --host 127.0.0.1 \
    --port 8000 \
    --reload \
    --log-level debug
```

### Log Analysis

```bash
# Monitor real-time logs
tail -f logs/vpsweb.log

# Search for errors
grep -i error logs/vpsweb.log

# Analyze API requests
grep "POST\|GET\|PUT\|DELETE" logs/vpsweb.log

# Check workflow execution
grep -i workflow logs/vpsweb.log
```

### Test Automation Scripts

```bash
# Run comprehensive test suite
./scripts/test.sh

# Integration testing
./scripts/integration_test.sh

# Performance benchmarking
./scripts/performance_test.sh
```

---

## 📝 Testing Checklist

### Pre-Testing Checklist
- [ ] Environment configured with API keys
- [ ] Database initialized with migrations
- [ ] Development server starts successfully
- [ ] All API endpoints respond (health check)
- [ ] CLI tools functional

### Functional Testing Checklist
- [ ] Web UI loads and displays correctly
- [ ] Poem CRUD operations work
- [ ] Translation management works
- [ ] API endpoints function properly
- [ ] CLI workflow integration works
- [ ] WeChat article generation works

### Performance Testing Checklist
- [ ] Database queries execute efficiently
- [ ] API response times < 200ms
- [ ] Concurrent requests handled properly
- [ ] Memory usage remains stable
- [ ] Log rotation works correctly

### Error Handling Checklist
- [ ] 404 errors display user-friendly pages
- [ ] Validation errors show helpful messages
- [ ] Timeout protection works
- [ ] Database connection failures handled gracefully
- [ ] Missing API keys handled appropriately

### Integration Testing Checklist
- [ ] CLI ↔ Repository integration works
- [ ] Web UI ↔ Repository integration works
- [ ] Translation workflow ↔ Repository integration works
- [ ] WeChat generation ↔ Repository integration works
- [ ] End-to-end workflow functions correctly

---

## 🎯 Success Criteria

A successful testing session should demonstrate:

1. **Complete Functionality**: All features work as documented
2. **Integration Success**: All components work together seamlessly
3. **Performance Targets**: <200ms API response times, efficient database operations
4. **Error Handling**: Graceful handling of all error conditions
5. **User Experience**: Intuitive web interface and responsive design
6. **Data Integrity**: No data loss or corruption during operations
7. **Workflow Integration**: Seamless integration between CLI, Web UI, and Repository

**VPSWeb v0.3.2 is production-ready when all test criteria pass!** 🚀

---

*For additional support or questions, refer to the project documentation or create an issue in the repository.*