# 重构项目执行自动化机制

**创建日期**: 2025年11月2日
**目的**: 确保项目跟踪系统的有效执行，减少手动工作

---

## 🎯 执行策略：半自动化

结合我的自动化能力和您的日常参与，实现高效的项目跟踪。

---

## 🤖 我的自动化职责

### 1. **工作开始时的自动检查**
每次我重新开始工作时，会自动执行：

```python
# 自动执行的工作开始检查
def auto_start_work_check():
    # 1. 检查当前状态
    current_state = read_file("docs/claudecode/context/current_state.md")

    # 2. 检查下一步行动
    next_steps = read_file("docs/claudecode/context/next_steps.md")

    # 3. 检查当前分支状态
    branch_status = run_command("git branch --show-current")

    # 4. 更新今日工作日志（如果需要）
    today_log = f"docs/claudecode/progress/daily_updates/{datetime.now().strftime('%Y-%m-%d')}.md"

    # 5. 识别当前应该进行的任务
    return determine_current_tasks(current_state, next_steps)
```

### 2. **任务执行时的自动记录**
在我执行每个重要任务时，会自动：

```python
# 自动任务记录
def auto_log_task_progress(task_name, status, details):
    # 1. 更新当前状态
    update_current_state(task_name, status)

    # 2. 记录到今日日志
    append_to_daily_log(task_name, status, details)

    # 3. 更新下一步行动
    update_next_steps(task_name, status)

    # 4. 更新项目概览
    update_project_overview()
```

### 3. **工作结束时的自动总结**
每次工作结束时，会自动：

```python
# 自动工作总结
def auto_work_summary():
    # 1. 生成本日工作总结
    daily_summary = generate_daily_summary()

    # 2. 更新项目状态文件
    update_all_status_files()

    # 3. 明确下一步行动
    clarify_next_steps()

    # 4. 识别需要决策的问题
    identify_decisions_needed()
```

### 4. **定期自动健康检查**
每3-5个工作日，自动执行：

```python
# 自动健康检查
def auto_health_check():
    # 1. 使用MCP工具检查代码质量
    run_code_quality_checks()

    # 2. 检查分支一致性
    check_branch_consistency()

    # 3. 检查文档完整性
    check_documentation_integrity()

    # 4. 检查进度是否符合预期
    check_progress_alignment()

    # 5. 识别潜在风险
    identify_potential_risks()

def run_code_quality_checks():
    """使用MCP工具进行代码质量检查"""
    # 获取VS Code诊断信息
    diagnostics = get_diagnostics_code()

    # 分析诊断结果
    analyze_diagnostics(diagnostics)

    # 识别需要关注的问题
    identify_critical_issues(diagnostics)
```

---

## 👤 您的参与职责（轻量级）

### 1. **每日简短确认** (2分钟)
在每次与我开始工作时：

```bash
# 您只需要运行一个命令
./scripts/daily_handshake.sh
```

这个命令会：
- 显示昨日进度摘要
- 显示今日计划
- 询问是否有变更或特殊要求

### 2. **决策点响应** (按需)
当我需要决策时，会：
- 清晰描述问题和选项
- 提供推荐方案
- 等待您的确认

### 3. **里程碑回顾** (5分钟)
每个阶段完成时：
- 查看阶段总结报告
- 确认是否进入下一阶段
- 提供反馈和调整建议

---

## 🛠️ MCP工具集成的自动化工具

### 1. **智能代码导航和诊断**

```python
# scripts/mcp_enhanced_tracker.py
import json
from datetime import datetime
from pathlib import Path

class MCPEnhancedTracker:
    def __init__(self):
        self.base_path = Path("docs/claudecode")

    def start_work_session(self):
        """开始工作会话 - 使用MCP工具进行深度分析"""
        session_id = datetime.now().strftime("%Y%m%d_%H%M%S")

        # 1. 使用MCP工具分析当前代码状态
        self.analyze_current_code_state()

        # 2. 记录会话开始
        self.log_event("work_session_start", {
            "session_id": session_id,
            "timestamp": datetime.now().isoformat(),
            "branch": self.get_current_branch(),
            "code_state": self.get_code_state(),
            "diagnostics": self.get_code_diagnostics()
        })

        return session_id

    def analyze_current_code_state(self):
        """使用MCP工具分析代码状态"""
        try:
            # 1. 获取项目文件结构
            file_structure = list_files_code(path='.')
            self.log_analysis("file_structure", file_structure)

            # 2. 检查代码诊断
            diagnostics = get_diagnostics_code()
            self.log_analysis("code_diagnostics", diagnostics)

            # 3. 识别关键符号和模式
            key_symbols = self.identify_key_symbols()
            self.log_analysis("key_symbols", key_symbols)

        except Exception as e:
            self.log_error("code_analysis_failed", str(e))

    def identify_key_symbols(self):
        """识别项目中的关键符号"""
        key_symbols = {}

        # 查找与重构相关的类和函数
        refactoring_patterns = [
            "executor", "workflow", "retry", "parser",
            "step", "translation", "llm", "provider"
        ]

        for pattern in refactoring_patterns:
            symbols = search_symbols_code(query=pattern, max_results=10)
            if symbols:
                key_symbols[pattern] = symbols

        return key_symbols

    def complete_task_with_mcp_analysis(self, task_name, details=""):
        """完成任务记录 - 包含MCP工具分析"""
        # 1. 标准任务记录
        self.complete_task(task_name, details)

        # 2. 使用MCP工具进行代码质量分析
        self.perform_post_task_analysis(task_name)

        # 3. 更新诊断信息
        self.update_code_diagnostics()

    def perform_post_task_analysis(self, task_name):
        """完成任务后的MCP工具分析"""
        try:
            # 获取更新后的诊断信息
            new_diagnostics = get_diagnostics_code()

            # 如果任务涉及文件修改，分析影响
            if "refactor" in task_name.lower():
                self.analyze_refactor_impact(task_name)

            # 检查是否有新的问题引入
            self.check_for_new_issues(new_diagnostics)

        except Exception as e:
            self.log_error("post_task_analysis_failed", str(e))

    def analyze_refactor_impact(self, task_name):
        """分析重构任务的影响"""
        # 使用context7进行语义搜索
        impact_analysis = self.search_refactor_patterns(task_name)
        self.log_analysis("refactor_impact", impact_analysis)

    def search_refactor_patterns(self, task_name):
        """使用context7搜索重构模式"""
        # 根据任务名称确定搜索策略
        if "executor" in task_name:
            return self.search_executor_patterns()
        elif "workflow" in task_name:
            return self.search_workflow_patterns()
        elif "database" in task_name or "crud" in task_name:
            return self.search_database_patterns()

        return {}

    def search_executor_patterns(self):
        """搜索executor相关的模式"""
        patterns = [
            "StepExecutor implementation patterns",
            "retry strategy usage",
            "parsing logic",
            "LLM provider integration"
        ]

        results = {}
        for pattern in patterns:
            try:
                # 使用context7进行语义搜索
                search_result = search_symbols_code(query=pattern, max_results=5)
                results[pattern] = search_result
            except Exception as e:
                results[pattern] = f"Search failed: {e}"

        return results

    def get_code_diagnostics(self):
        """获取代码诊断信息"""
        try:
            return get_diagnostics_code()
        except Exception as e:
            return {"error": f"Failed to get diagnostics: {e}"}

    def get_code_state(self):
        """获取当前代码状态"""
        try:
            # 获取文件结构
            files = list_files_code(path='.')

            # 获取关键符号
            key_symbols = self.identify_key_symbols()

            return {
                "file_count": len(files),
                "key_symbols": key_symbols,
                "last_analysis": datetime.now().isoformat()
            }
        except Exception as e:
            return {"error": f"Failed to get code state: {e}"}
```

### 2. **智能代码质量监控**

```python
# scripts/code_quality_monitor.py
class CodeQualityMonitor:
    def __init__(self):
        self.quality_metrics = {}
        self.baseline_metrics = None

    def establish_baseline(self):
        """建立代码质量基线"""
        self.baseline_metrics = self.collect_current_metrics()
        self.save_baseline()

    def collect_current_metrics(self):
        """收集当前代码质量指标"""
        metrics = {}

        try:
            # 1. 诊断信息
            metrics['diagnostics'] = get_diagnostics_code()

            # 2. 文件结构复杂度
            metrics['file_complexity'] = self.analyze_file_complexity()

            # 3. 代码重复度
            metrics['duplication'] = self.analyze_code_duplication()

            # 4. 导入依赖关系
            metrics['dependencies'] = self.analyze_dependencies()

            # 5. 测试覆盖率（如果可获取）
            metrics['test_coverage'] = self.get_test_coverage()

        except Exception as e:
            metrics['error'] = str(e)

        return metrics

    def monitor_quality_changes(self):
        """监控代码质量变化"""
        current_metrics = self.collect_current_metrics()

        if self.baseline_metrics:
            changes = self.compare_with_baseline(current_metrics)
            self.report_quality_changes(changes)

        return current_metrics

    def compare_with_baseline(self, current_metrics):
        """与基线比较"""
        changes = {}

        # 比较诊断信息变化
        if 'diagnostics' in current_metrics and 'diagnostics' in self.baseline_metrics:
            diag_changes = self.compare_diagnostics(
                current_metrics['diagnostics'],
                self.baseline_metrics['diagnostics']
            )
            changes['diagnostics'] = diag_changes

        return changes

    def compare_diagnostics(self, current, baseline):
        """比较诊断信息变化"""
        current_errors = {d['file']: d['message'] for d in current}
        baseline_errors = {d['file']: d['message'] for d in baseline}

        new_errors = set(current_errors.keys()) - set(baseline_errors.keys())
        fixed_errors = set(baseline_errors.keys()) - set(current_errors.keys())

        return {
            'new_errors': list(new_errors),
            'fixed_errors': list(fixed_errors),
            'total_current': len(current),
            'total_baseline': len(baseline)
        }
```

### 3. **增强的进度跟踪助手**

```python
# scripts/enhanced_progress_tracker.py
class EnhancedProgressTracker:
    def __init__(self):
        self.base_path = Path("docs/claudecode")
        self.mcp_tools = MCPTools()

    def start_work_session(self):
        """开始工作会话 - MCP增强版"""
        session_id = datetime.now().strftime("%Y%m%d_%H%M%S")

        # 1. MCP工具状态检查
        mcp_status = self.check_mcp_tools_status()

        # 2. 深度代码分析
        code_analysis = self.perform_deep_code_analysis()

        # 3. 记录会话开始
        self.log_event("work_session_start", {
            "session_id": session_id,
            "timestamp": datetime.now().isoformat(),
            "mcp_tools_status": mcp_status,
            "code_analysis": code_analysis,
            "branch": self.get_current_branch()
        })

        return session_id

    def check_mcp_tools_status(self):
        """检查MCP工具状态"""
        status = {}

        # 测试各个MCP工具的可用性
        tools_to_check = [
            "list_files_code", "search_symbols_code", "get_diagnostics_code",
            "context7", "github", "deepwiki", "fetch"
        ]

        for tool in tools_to_check:
            try:
                # 尝试使用工具
                if tool == "list_files_code":
                    result = list_files_code(path='.')
                elif tool == "get_diagnostics_code":
                    result = get_diagnostics_code()
                # ... 其他工具测试

                status[tool] = "available"
            except Exception as e:
                status[tool] = f"unavailable: {str(e)[:50]}"

        return status

    def perform_deep_code_analysis(self):
        """使用MCP工具进行深度代码分析"""
        analysis = {}

        try:
            # 1. 文件结构分析
            analysis['file_structure'] = list_files_code(path='.')

            # 2. 关键符号识别
            analysis['key_symbols'] = self.identify_critical_symbols()

            # 3. 依赖关系分析
            analysis['dependencies'] = self.analyze_dependencies()

            # 4. 代码质量指标
            analysis['quality_metrics'] = self.assess_code_quality()

        except Exception as e:
            analysis['error'] = str(e)

        return analysis

    def complete_task_with_comprehensive_analysis(self, task_name, details=""):
        """完成任务 - 包含全面分析"""
        # 1. 标准任务记录
        self.complete_task(task_name, details)

        # 2. 使用MCP工具进行全面分析
        comprehensive_analysis = self.perform_comprehensive_post_task_analysis(task_name)

        # 3. 生成分析报告
        self.generate_analysis_report(task_name, comprehensive_analysis)

    def perform_comprehensive_post_task_analysis(self, task_name):
        """执行全面的任务后分析"""
        analysis = {}

        # 1. 诊断信息变化
        analysis['diagnostics'] = self.analyze_diagnostics_changes()

        # 2. 文件变更影响
        analysis['file_impacts'] = self.analyze_file_impacts()

        # 3. 语义搜索验证
        analysis['semantic_verification'] = self.perform_semantic_verification(task_name)

        # 4. 依赖关系变化
        analysis['dependency_changes'] = self.analyze_dependency_changes()

        return analysis
```

### 4. **更新的每日握手脚本**
```bash
# scripts/daily_handshake.sh (MCP增强版)
#!/bin/bash

echo "=== VPSWeb 重构项目每日握手 (MCP增强版) ==="
echo "时间: $(date)"
echo ""

# 检查MCP工具状态
echo "🔧 MCP工具状态:"
python3 -c "
from scripts.mcp_enhanced_tracker import MCPEnhancedTracker
tracker = MCPEnhancedTracker()
status = tracker.check_mcp_tools_status()
for tool, status in status.items():
    echo '  ' \$tool': status
"
echo ""

# 显示昨日总结（原有逻辑）
# ... (保持原有的昨日回顾逻辑)

# 显示今日计划
echo "📋 今日计划 (MCP工具指导):"
# 使用MCP工具分析下一步计划
python3 -c "
import sys
sys.path.append('.')
from scripts.enhanced_progress_tracker import EnhancedProgressTracker

tracker = EnhancedProgressTracker()
current_state = tracker.get_current_state()
if current_state.get('key_symbols'):
    print('基于当前代码状态，建议重点关注:')
    for pattern, symbols in current_state['key_symbols'].items():
        if len(symbols) > 0:
            print(f'  - {pattern}: {len(symbols)} 个符号')
"
echo ""

# 显示当前状态（原有逻辑）
# ... (保持原有的状态显示逻辑)

# 代码质量健康检查
echo "🏥 代码质量健康检查:"
python3 -c "
from scripts.code_quality_monitor import CodeQualityMonitor

monitor = CodeQualityMonitor()
try:
    metrics = monitor.collect_current_metrics()
    if 'diagnostics' in metrics:
        diags = metrics['diagnostics']
        if isinstance(diags, list):
            print(f'  📊 诊断信息: {len(diags)} 个项目')
            error_count = len([d for d in diags if d.get('severity') == 'error'])
            warning_count = len([d for d in diags if d.get('severity') == 'warning'])
            if error_count == 0:
                print('  ✅ 无错误')
            else:
                print(f'  ❌ {error_count} 个错误')
            if warning_count == 0:
                print('  ✅ 无警告')
            else:
                print(f'  ⚠️  {warning_count} 个警告')
        else:
            print('  📊 诊断信息: 已获取')
    else:
        print('  📊 诊断信息: 获取中')
except Exception as e:
    print(f'  ❌ 质量检查失败: {e}')
"
echo ""

echo "=== MCP增强握手完成 ==="
echo "🚀 现在可以开始高质量的工作！"

---

## 📅 日常执行时间表

### 每日自动执行

| 时间 | 我的自动行动 | 您的参与 |
|------|-------------|----------|
| **工作开始** | 自动检查状态，恢复上下文 | 运行 `./scripts/daily_handshake.sh` |
| **工作期间** | 自动记录任务进度 | 无需操作 |
| **遇到问题时** | 自动记录问题，识别需要决策的点 | 响应决策请求 |
| **工作结束** | 自动生成工作总结，更新所有文件 | 无需操作 |
| **下午3点** | 自动提醒更新进度 | 确认提醒（如需要） |

### 每周自动执行

| 时间 | 我的自动行动 | 您的参与 |
|------|-------------|----------|
| **周五下午** | 生成周度报告，更新里程碑状态 | 查看周报，提供反馈 |
| **周一上午** | 检查周度计划对齐，识别本周重点 | 确认本周重点 |

### 每里程碑自动执行

| 时间 | 我的自动行动 | 您的参与 |
|------|-------------|----------|
| **阶段完成** | 生成完成报告，更新所有状态文件 | 确认完成，决定下一步 |
| **遇到重大阻塞** | 自动升级问题，提供解决方案选项 | 做出决策 |

---

## 🎯 预期效果

### 对您的便利
- **最小时间投入**: 每天只需2分钟的握手确认
- **最大透明度**: 随时了解项目状态
- **及时决策**: 只在真正需要时参与
- **轻松回顾**: 完整的历史记录便于回顾

### 对项目的好处
- **持续跟踪**: 不会遗漏任何进展和问题
- **及时预警**: 提前发现潜在风险
- **质量保证**: 自动检查确保文档和状态的一致性
- **高效协作**: 减少沟通成本，专注实际工作

---

## 🚀 立即开始

### 1. 创建握手脚本
```bash
# 创建每日握手脚本（已包含在设计中）
```

### 2. 配置自动提醒
```python
# 在我的工具中集成提醒系统
```

### 3. 测试自动化流程
```bash
# 测试第一次的自动执行
./scripts/daily_handshake.sh
```

---

## 📞 您的使用建议

1. **信任自动化**: 相信我的自动记录和更新
2. **关注重点**: 在需要决策时及时响应
3. **定期回顾**: 每周查看自动生成的报告
4. **反馈优化**: 告诉我哪些地方可以改进

通过这个半自动化系统，我们既能保持项目的完整跟踪，又能最大化您的工作效率。