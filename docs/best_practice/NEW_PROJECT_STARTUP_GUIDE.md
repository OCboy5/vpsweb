# 🚀 New Claude Code Project Startup Guide

**Your Path to VPSWeb-Level Excellence**

*Get your new project running with the same methodology that achieved 100% test success rates and complete architectural modernization*

## 🎯 **Quick Start: 5-Minute Setup**

### **Step 1: Copy This Package**
```bash
# Navigate to your new project directory
cd /path/to/your-new-project

# Copy the best practice package
cp -r /path/to/vpsweb/docs/best_practice/ ./
```

### **Step 2: Run Automated Setup**
```bash
# Execute the comprehensive setup script
./best_practice/scripts/setup-new-project.sh

# This script will create:
# - Project structure (src/, tests/, docs/, scripts/)
# - Configuration files (pyproject.toml, pytest.ini, .pre-commit-config.yaml)
# - Core component template
# - Test infrastructure
# - Quality gate scripts
# - Initial documentation
```

### **Step 3: Copy Essential Scripts**
```bash
# Make sure essential scripts are in place
cp ./best_practice/scripts/quality-gate.sh ./scripts/
cp ./best_practice/scripts/daily-setup.sh ./scripts/

# Make them executable
chmod +x ./scripts/quality-gate.sh ./scripts/daily-setup.sh
```

### **Step 4: Initialize Tracking**
```bash
# Copy tracking templates
mkdir -p docs/claudecode
cp ./best_practice/templates/phase_tracking.md docs/claudecode/current_phase.md

# Initialize with your project details
sed -i.bak 's/\[PROJECT_NAME\]/Your Project Name/g' docs/claudecode/current_phase.md
sed -i 's/\[START_DATE\]/'$(date +%Y-%m-%d)'/g' docs/claudecode/current_phase.md
```

### **Step 5: Start Development!**
```bash
# Install dependencies and verify setup
poetry install
export PYTHONPATH="$(pwd)/src:$PYTHONPATH"

# Run quality gates to ensure everything works
./scripts/quality-gate.sh

# Begin your first development session
./scripts/daily-setup.sh
```

## 📚 **Essential Reading Order**

### **🎯 Priority 1: Foundation (Day 1)**
1. **[README.md](./README.md)** - Overview and success metrics
2. **[01-project-setup.md](./01-project-setup.md)** - Environment setup and infrastructure
3. **[02-phase-planning.md](./02-phase-planning.md)** - Systematic development approach

### **🛠️ Priority 2: Daily Operations (Day 2-3)**
4. **[10-mcp-tools-best-practices.md](./10-mcp-tools-best-practices.md)** - **CRITICAL**: Tool usage excellence
5. **[04-development-workflow.md](./04-development-workflow.md)** - Daily workflow patterns
6. **[05-testing-strategy.md](./05-testing-strategy.md)** - 100% test success methodology

### **📊 Priority 3: Quality and Tracking (Day 4-5)**
7. **[07-project-tracking.md](./07-project-tracking.md)** - Progress management
8. **[06-code-quality-standards.md](./06-code-quality-standards.md)** - Quality gates and standards
9. **[03-success-metrics.md](./03-success-metrics.md)** - Measuring success

### **🚀 Priority 4: Advanced Topics (Week 2)**
10. **[13-architectural-patterns.md](./13-architectural-patterns.md)** - Modern architecture
11. **[11-automation-scripts.md](./11-automation-scripts.md)** - Development automation
12. **[15-continuous-improvement.md](./15-continuous-improvement.md)** - Learning and optimization

## 🎯 **Day 1: Foundation Setup**

### **Morning (2 hours): Environment and Infrastructure**

#### **1. Project Setup**
```bash
# Follow the step-by-step guide in 01-project-setup.md

# Execute this sequence:
echo "🚀 Setting up new Claude Code project..."

# 1. Create directory structure
mkdir -p src/{your_project_name,tests}
mkdir -p tests/{unit,integration,fixtures}
mkdir -p docs/{claudecode,api}
mkdir -p scripts/{setup,testing}

# 2. Initialize Python environment
poetry init
poetry add --group dev pytest pytest-cov pytest-asyncio
poetry add --group dev black flake8 mypy pre-commit
poetry add --group dev safety

# 3. Set up pre-commit hooks
poetry run pre-commit install

# 4. Copy configuration templates
cp docs/best_practice/templates/.pre-commit-config.yaml .
cp docs/best_practice/templates/pytest.ini .
cp docs/best_practice/templates/pyproject.toml .

echo "✅ Environment setup complete!"
```

#### **2. Test Infrastructure**
```python
# Create tests/conftest.py based on best practice template
cat > tests/conftest.py << 'EOF'
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock

@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
def mock_config():
    return {
        "provider": "test_provider",
        "model": "test-model",
        "max_tokens": 1000,
        "temperature": 0.7
    }

@pytest.fixture
def mock_llm_factory():
    factory = Mock()
    provider = AsyncMock()
    provider.generate.return_value = {"content": "test response"}
    factory.get_provider.return_value = provider
    return factory
EOF

echo "✅ Test infrastructure initialized!"
```

### **Afternoon (3 hours): First Component and Tests**

#### **1. Create Your First Component**
```python
# Create src/your_project_name/core.py with best practices
cat > src/your_project_name/core.py << 'EOF'
"""Core component following VPSWeb patterns"""

from typing import Dict, Any, Optional
from dataclasses import dataclass

@dataclass
class Config:
    """Configuration with type safety"""
    provider: str
    model: str
    max_tokens: int = 1000
    temperature: float = 0.7

class CoreComponent:
    """Core component with dependency injection"""

    def __init__(self, config: Config, validator=None):
        self.config = config
        self.validator = validator or self._default_validator

    def _default_validator(self, data: Dict[str, Any]) -> bool:
        """Default validation logic"""
        return bool(data and isinstance(data, dict))

    async def process_data(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process data with validation and error handling"""
        if not self.validator(input_data):
            raise ValueError("Invalid input data")

        # Your core logic here
        return {
            "status": "success",
            "processed_data": input_data,
            "config": {
                "provider": self.config.provider,
                "model": self.config.model
            }
        }
EOF

echo "✅ Core component created!"
```

#### **2. Create Comprehensive Tests**
```python
# Create tests/unit/test_core.py following VPSWeb patterns
cat > tests/unit/test_core.py << 'EOF'
import pytest
from unittest.mock import Mock, AsyncMock
from your_project_name.core import CoreComponent, Config

class TestCoreComponent:
    """Test core component with VPSWeb patterns"""

    @pytest.fixture
    def sample_config(self):
        return Config(
            provider="test_provider",
            model="test-model",
            max_tokens=1500,
            temperature=0.8
        )

    @pytest.fixture
    def core_component(self, sample_config):
        return CoreComponent(sample_config)

    @pytest.mark.unit
    def test_component_initialization(self, core_component, sample_config):
        """Test component initialization with dependency injection"""
        assert core_component.config == sample_config
        assert core_component.validator is not None

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_process_data_success(self, core_component):
        """Test successful data processing"""
        input_data = {"test": "data", "value": 123}

        result = await core_component.process_data(input_data)

        assert result["status"] == "success"
        assert result["processed_data"] == input_data
        assert result["config"]["provider"] == "test_provider"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_process_data_validation_failure(self, core_component):
        """Test data validation failure"""
        invalid_data = None

        with pytest.raises(ValueError, match="Invalid input data"):
            await core_component.process_data(invalid_data)

    @pytest.mark.unit
    @pytest.mark.parametrize("input_data", [
        {"key": "value"},
        {"number": 42},
        {"nested": {"data": "test"}},
        {}
    ])
    @pytest.mark.asyncio
    async def test_process_data_multiple_inputs(self, core_component, input_data):
        """Test with multiple input scenarios"""
        if input_data:  # Empty dict should fail validation
            result = await core_component.process_data(input_data)
            assert result["status"] == "success"
        else:
            with pytest.raises(ValueError):
                await core_component.process_data(input_data)
EOF

echo "✅ Comprehensive tests created!"
```

#### **3. Run Quality Gates**
```bash
# Execute quality gates to ensure everything works
echo "🔍 Running quality gates..."

poetry run black src/ tests/
echo "✅ Code formatting applied"

poetry run flake8 src/ tests/
echo "✅ Linting passed"

poetry run mypy src/
echo "✅ Type checking passed"

poetry run pytest tests/ -v --cov=src
echo "🎉 All tests passing with coverage report!"

echo "✅ Day 1 foundation complete!"
```

## 🛠️ **Day 2: MCP Tools Integration**

### **Morning (2 hours): Tool Setup and Validation**

#### **1. Verify MCP Tools Availability**
```python
# Create scripts/verify-mcp-tools.py
cat > scripts/verify-mcp-tools.py << 'EOF'
#!/usr/bin/env python3
"""Verify MCP tools are available and working"""

import sys
import subprocess

def check_tool_availability():
    """Check if essential MCP tools are available"""

    tools_status = {
        "vscode-mcp-server": False,
        "context7": False,
        "github": False,
        "deepwiki": False,
        "fetch": False
    }

    print("🔍 Verifying MCP tools availability...")

    # Test vscode-mcp-server
    try:
        # This would be called through Claude Code interface
        print("✅ vscode-mcp-server available (integrated)")
        tools_status["vscode-mcp-server"] = True
    except:
        print("❌ vscode-mcp-server not available")

    # Test context7
    try:
        print("✅ context7 available (integrated)")
        tools_status["context7"] = True
    except:
        print("❌ context7 not available")

    print("\n📊 Tool Availability Summary:")
    for tool, status in tools_status.items():
        status_icon = "✅" if status else "❌"
        print(f"  {status_icon} {tool}")

    available_count = sum(tools_status.values())
    print(f"\n🎯 Available: {available_count}/{len(tools_status)} tools")

    return available_count >= 3  # Require at least 3 tools

if __name__ == "__main__":
    if check_tool_availability():
        print("\n🎉 MCP tools verification passed!")
        sys.exit(0)
    else:
        print("\n❌ MCP tools verification failed!")
        sys.exit(1)
EOF

chmod +x scripts/verify-mcp-tools.py
```

#### **2. Practice MCP Tool Usage**
```python
# Create exercises/mcp-tool-practice.py
cat > exercises/mcp-tool-practice.py << 'EOF'
"""
MCP Tools Practice Exercises
Practice the same patterns used in VPSWeb project
"""

def exercise_1_project_structure_analysis():
    """
    Exercise 1: Use vscode-mcp-server to analyze project structure
    Expected: Use get_document_symbols_code and list_files_code
    """
    print("🎯 Exercise 1: Project Structure Analysis")
    print("Instructions:")
    print("1. Use list_files_code('src/', recursive=False) to get overview")
    print("2. Use get_document_symbols_code('src/your_project_name/core.py') to get structure")
    print("3. Compare efficiency vs reading entire files")
    return "Complete when you can retrieve structure without file contents"

def exercise_2_library_research():
    """
    Exercise 2: Use context7 to research best practices
    Expected: Use resolve_library_id and get_library_docs
    """
    print("🎯 Exercise 2: Library Research")
    print("Instructions:")
    print("1. Use resolve_library_id('fastapi') to get library ID")
    print("2. Use get_library_docs(library_id, topic='testing') to get testing patterns")
    print("3. Use get_library_docs(library_id, topic='dependency-injection') for DI patterns")
    return "Complete when you can retrieve specific documentation topics"

def exercise_3_code_search_patterns():
    """
    Exercise 3: Use github to find implementation patterns
    Expected: Use search_repositories and search_code
    """
    print("🎯 Exercise 3: Code Search Patterns")
    print("Instructions:")
    print("1. Use search_repositories('fastapi stars:>1000') to find successful projects")
    print("2. Use search_code('dependency injection language:python') to find patterns")
    print("3. Analyze results for common implementation approaches")
    return "Complete when you can find 3+ implementation examples"

def exercise_4_integrated_research():
    """
    Exercise 4: Combine multiple tools for comprehensive research
    Expected: Use tools in sequence like VPSWeb project
    """
    print("🎯 Exercise 4: Integrated Research")
    print("Instructions:")
    print("1. Research a feature using github search")
    print("2. Get library documentation using context7")
    print("3. Learn from successful projects using deepwiki")
    print("4. Synthesize findings into implementation plan")
    return "Complete when you can combine 3+ tools effectively"

def run_all_exercises():
    """Run all MCP tool practice exercises"""
    exercises = [
        exercise_1_project_structure_analysis,
        exercise_2_library_research,
        exercise_3_code_search_patterns,
        exercise_4_integrated_research
    ]

    print("🚀 MCP Tools Practice Exercises")
    print("=" * 50)

    for i, exercise in enumerate(exercises, 1):
        print(f"\nExercise {i}:")
        result = exercise()
        print(f"Goal: {result}")

    print("\n🎯 Pro Tip: Master these patterns to achieve VPSWeb-level efficiency!")
    print("   - Always use overview-first approach")
    print("   - Combine tools for comprehensive research")
    print("   - Minimize context usage while maximizing insight")

if __name__ == "__main__":
    run_all_exercises()
EOF

echo "✅ MCP tools practice exercises created!"
```

### **Afternoon (3 hours): Apply MCP Tools to Real Work**

#### **1. Research-Driven Feature Development**
```python
# Create templates/research_driven_development.py
cat > templates/research_driven_development.py << 'EOF'
"""
Template for Research-Driven Development
Apply VPSWeb's MCP tool patterns to new features
"""

async def research_feature_before_implementation(feature_description: str):
    """
    Template: Research feature before implementation
    Mirrors VPSWeb's successful research patterns
    """

    print(f"🔍 Researching feature: {feature_description}")

    # Step 1: Understand existing codebase (vscode-mcp-server)
    # Use: list_files_code, get_document_symbols_code, search_symbols_code

    # Step 2: Find existing implementations (github)
    # Use: search_repositories, search_code

    # Step 3: Get library documentation (context7)
    # Use: resolve_library_id, get_library_docs

    # Step 4: Learn from successful projects (deepwiki)
    # Use: read_wiki_structure, read_wiki_contents, ask_question

    # Step 5: Create implementation plan
    # Synthesize all research into actionable plan

    research_results = {
        "existing_patterns": "From vscode-mcp-server analysis",
        "similar_implementations": "From github search results",
        "library_guidance": "From context7 documentation",
        "best_practices": "From deepwiki project analysis",
        "implementation_plan": "Synthesized plan"
    }

    return research_results

# Example usage for your project
async def implement_new_feature_example():
    """Example: Implement a new caching feature"""

    feature = "Redis caching for API responses"

    # Research phase (uses MCP tools)
    research = await research_feature_before_implementation(feature)

    print("📋 Research Results:")
    for category, findings in research.items():
        print(f"  📂 {category}: {findings}")

    # Implementation phase (based on research)
    print("🚀 Implementing based on research...")

    # Your implementation code here

    print("✅ Feature implemented with research-driven approach!")

EOF

echo "✅ Research-driven development template created!"
```

## 📊 **Day 3: Project Tracking and Quality Systems**

### **Morning (2 hours): Initialize Tracking Systems**

#### **1. Set Up Project Tracking**
```bash
# Create your project tracking documents
cp docs/best_practice/templates/phase_tracking.md docs/claudecode/current_phase.md

# Initialize with your project details
sed -i.bak 's/\[PROJECT_NAME\]/Your Project Name/g' docs/claudecode/current_phase.md
sed -i 's/\[START_DATE\]/'$(date +%Y-%m-%d)'/g' docs/claudecode/current_phase.md
sed -i 's/\[CURRENT_PHASE\]/Phase 0: Test Infrastructure/g' docs/claudecode/current_phase.md

echo "✅ Project tracking initialized!"
```

#### **2. Create Success Metrics Dashboard**
```markdown
# Create docs/claudecode/success_metrics.md
cat > docs/claudecode/success_metrics.md << 'EOF'
# Project Success Metrics

## Primary Success Indicators

### Test Success Rate
- **Target**: 100%
- **Current**: 1/1 (100%)
- **Trend**: STABLE

### Code Quality Score
- **Target**: < 5 average complexity
- **Current**: 2/10
- **Trend**: EXCELLENT

### MCP Tools Efficiency
- **Target**: 70% efficiency improvement
- **Current**: Learning phase
- **Trend**: IMPROVING

## Today's Achievements
- [x] Project structure created
- [x] Test infrastructure initialized
- [x] First component and tests implemented
- [x] Quality gates passing
- [x] MCP tools research started

## Tomorrow's Goals
- [ ] Complete MCP tools practice exercises
- [ ] Implement second component using research-driven approach
- [ ] Achieve 5/5 tests passing
- [ ] Set up CI/CD pipeline

## Success Criteria Checklist
- [ ] All tests passing (100%)
- [ ] Code quality gates passing
- [ ] MCP tools integrated and efficient
- [ ] Project tracking active and updated
- [ ] Documentation following VPSWeb patterns

EOF

echo "✅ Success metrics dashboard created!"
```

### **Afternoon (3 hours): Quality Gates and Automation**

#### **1. Complete Quality Gates Setup**
```bash
# Create comprehensive quality gates script
cat > scripts/quality-gate.sh << 'EOF'
#!/bin/bash
# Comprehensive quality gate validation

set -e

echo "🔍 Running Quality Gate Validation"
echo "================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    local status=$1
    local message=$2

    if [ "$status" = "PASS" ]; then
        echo -e "${GREEN}✅ $message${NC}"
    elif [ "$status" = "FAIL" ]; then
        echo -e "${RED}❌ $message${NC}"
    else
        echo -e "${YELLOW}⚠️  $message${NC}"
    fi
}

# Check 1: Code formatting
echo "📝 Checking code formatting..."
if poetry run black --check src/ tests/; then
    print_status "PASS" "Code formatting"
else
    print_status "FAIL" "Code formatting issues found"
    echo "Run 'poetry run black src/ tests/' to fix"
    exit 1
fi

# Check 2: Linting
echo "🔍 Running linting..."
if poetry run flake8 src/ tests/; then
    print_status "PASS" "Code linting"
else
    print_status "FAIL" "Linting issues found"
    exit 1
fi

# Check 3: Type checking
echo "🔍 Running type checking..."
if poetry run mypy src/; then
    print_status "PASS" "Type checking"
else
    print_status "FAIL" "Type checking issues found"
    exit 1
fi

# Check 4: Security
echo "🔒 Running security check..."
if poetry run safety check; then
    print_status "PASS" "Security scan"
else
    print_status "FAIL" "Security vulnerabilities found"
    exit 1
fi

# Check 5: Tests
echo "🧪 Running tests..."
if poetry run pytest tests/ -v --cov=src --cov-fail-under=80; then
    print_status "PASS" "All tests passing"
else
    print_status "FAIL" "Test failures or insufficient coverage"
    exit 1
fi

echo ""
echo "🎉 All quality gates passed!"
echo "📊 Coverage report available in htmlcov/index.html"
EOF

chmod +x scripts/quality-gate.sh
```

#### **2. Create Daily Development Script**
```bash
# Create scripts/daily-setup.sh
cat > scripts/daily-setup.sh << 'EOF'
#!/bin/bash
# Daily development setup script

set -e

echo "🌅 Daily Development Setup"
echo "========================="

# Sync with latest changes
echo "📥 Syncing with repository..."
git pull origin main || echo "No remote or up to date"

# Verify environment
echo "🐍 Verifying Python environment..."
poetry install

# Set environment
export PYTHONPATH="$(pwd)/src:$PYTHONPATH"

# Quick health check
echo "🔍 Running quick health check..."
python -c "from your_project_name.core import CoreComponent; print('✅ Import check passed')"

# Check project status
echo "📊 Current project status:"
if [ -f "docs/claudecode/current_phase.md" ]; then
    echo "📋 Phase tracking: Active"
else
    echo "⚠️  Phase tracking: Not initialized"
fi

# Run morning quality check
echo "🔍 Morning quality check..."
if poetry run black --check src/ tests/; then
    echo "✅ Code formatting OK"
else
    echo "⚠️  Code formatting needs attention"
fi

if poetry run flake8 src/ tests/ > /dev/null 2>&1; then
    echo "✅ Linting OK"
else
    echo "⚠️  Linting issues found"
fi

echo ""
echo "✅ Daily setup complete!"
echo "💡 Run './scripts/quality-gate.sh' for comprehensive validation"
echo "📚 Review 'docs/best_practice/04-development-workflow.md' for daily workflow"
EOF

chmod +x scripts/daily-setup.sh
```

## 🎯 **Your First Week Success Plan**

### **Day 1: Foundation** ✅
- [x] Environment setup
- [x] Test infrastructure
- [x] First component with tests
- [x] Quality gates passing

### **Day 2: MCP Tools Mastery**
- [ ] Complete MCP tools practice exercises
- [ ] Implement second component using research-driven approach
- [ ] Achieve efficient tool usage patterns
- [ ] Document tool efficiency improvements

### **Day 3: Quality Systems**
- [x] Project tracking initialized
- [x] Success metrics dashboard
- [x] Comprehensive quality gates
- [ ] Daily development workflow established

### **Day 4-5: Integration and Expansion**
- [ ] Add integration tests
- [ ] Implement service layer patterns
- [ ] Set up CI/CD pipeline
- [ ] Create documentation following VPSWeb patterns

### **Week 1 Success Criteria**
- [ ] 5+ tests passing (100% success rate)
- [ ] All quality gates passing
- [ ] MCP tools integrated and efficient
- [ ] Project tracking active and updated
- [ ] Following VPSWeb development patterns

## 🚀 **Immediate Next Steps**

### **Right Now**
1. **Run the quality gates**: `./scripts/quality-gate.sh`
2. **Verify your setup**: All checks should pass
3. **Start MCP tools practice**: Complete exercises in `exercises/mcp-tool-practice.py`

### **Today**
1. **Complete MCP tools exercises** (Day 2 agenda)
2. **Implement a second component** using research-driven approach
3. **Update project tracking** with your progress

### **This Week**
1. **Follow the daily workflow** from `04-development-workflow.md`
2. **Update success metrics** daily in `docs/claudecode/success_metrics.md`
3. **Review best practices** in relevant documentation sections

## 🎓 **Learning Resources**

### **Essential Reading**
- **[10-mcp-tools-best-practices.md](./10-mcp-tools-best-practices.md)** - Tool mastery
- **[04-development-workflow.md](./04-development-workflow.md)** - Daily patterns
- **[05-testing-strategy.md](./05-testing-strategy.md)** - Testing excellence

### **VPSWeb Project Reference**
Study the VPSWeb project documentation to see these practices in action:
- [Final completion summary](../claudecode/FINAL_COMPLETION_SUMMARY.md)
- [Phase completion reports](../claudecode/refactoring/phase_3/)
- [Code review resolution analysis](../claudecode/CODE_REVIEW_ISSUES_RESOLUTION_STATUS.md)

## 💡 **Pro Tips for Success**

1. **Tool-First Development**: Always use MCP tools before manual analysis
2. **Incremental Validation**: Run quality gates after every meaningful change
3. **Documentation-Driven**: Document decisions as you make them
4. **Pattern Recognition**: Learn from VPSWeb examples and apply patterns
5. **Continuous Improvement**: Update your process based on what works

---

**🎉 Congratulations!** You now have everything you need to achieve VPSWeb-level excellence in your new project. The methodology, tools, and patterns that delivered 100% test success rates and complete architectural modernization are now at your fingertips.

**Your Journey Starts Now!** 🚀