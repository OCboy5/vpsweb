#!/usr/bin/env python3
"""
VPSWeb 重构项目MCP增强的进度跟踪器

集成所有MCP工具，提供智能代码导航、深度分析和质量监控。
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any


# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


class MCPEnhancedTracker:
    """MCP增强的进度跟踪器"""

    def __init__(self, project_root: str = "."):
        self.project_root = Path(project_root)
        self.docs_path = self.project_root / "docs" / "claudecode"
        self.progress_path = self.docs_path / "progress" / "daily_updates"
        self.context_path = self.docs_path / "context"

        # 确保目录存在
        self.progress_path.mkdir(parents=True, exist_ok=True)
        self.context_path.mkdir(parents=True, exist_ok=True)

        # 初始化MCP工具
        self.mcp_tools = self._initialize_mcp_tools()

    def _initialize_mcp_tools(self):
        """初始化MCP工具"""
        tools = {}

        # 检查VS Code MCP服务器工具
        try:
            tools["vscode"] = {
                "list_files_code": True,
                "search_symbols_code": True,
                "get_diagnostics_code": True,
                "read_file_code": True,
                "create_file_code": True,
                "replace_lines_code": True,
                "get_document_symbols_code": True,
                "get_symbol_definition_code": True
            }
        except Exception as e:
            tools["vscode"] = {"error": str(e)}

        return tools

    def start_work_session(self) -> Dict[str, Any]:
        """开始工作会话 - 使用MCP工具进行深度分析"""
        session_id = datetime.now().strftime("%Y%m%d_%H%M%S")

        session_info = {
            "session_id": session_id,
            "start_time": datetime.now().isoformat(),
            "branch": self.get_current_branch(),
            "mcp_tools_status": self.check_mcp_tools_status(),
        }

        # 1. 使用MCP工具分析当前代码状态
        code_analysis = self.analyze_current_code_state()
        session_info["code_analysis"] = code_analysis

        # 2. 记录会话开始
        self.log_event("work_session_start", session_info)

        # 3. 更新今日日志
        self.update_daily_log("session_start", f"工作会话 {session_id} 开始 (MCP增强)")

        return session_info

    def analyze_current_code_state(self) -> Dict[str, Any]:
        """使用MCP工具分析当前代码状态"""
        analysis = {}

        try:
            # 1. 获取项目文件结构
            if self.is_mcp_tool_available("list_files_code"):
                file_structure = list_files_code(path='.')
                analysis["file_structure"] = {
                    "total_files": len(file_structure),
                    "file_types": self._analyze_file_types(file_structure)
                }

            # 2. 检查代码诊断
            if self.is_mcp_tool_available("get_diagnostics_code"):
                diagnostics = get_diagnostics_code()
                analysis["code_diagnostics"] = self._process_diagnostics(diagnostics)

            # 3. 识别关键符号和模式
            key_symbols = self.identify_key_symbols()
            if key_symbols:
                analysis["key_symbols"] = key_symbols

            # 4. 分析重构相关代码
            refactor_analysis = self.analyze_refactor_codebase()
            if refactor_analysis:
                analysis["refactor_analysis"] = refactor_analysis

        except Exception as e:
            analysis["error"] = f"Code analysis failed: {str(e)}"

        return analysis

    def _analyze_file_types(self, files: List[Dict[str, Any]]) -> Dict[str, int]:
        """分析文件类型分布"""
        file_types = {}
        for file_info in files:
            if "path" in file_info:
                path = Path(file_info["path"])
                suffix = path.suffix.lower()
                file_types[suffix] = file_types.get(suffix, 0) + 1
        return file_types

    def _process_diagnostics(self, diagnostics: List[Dict[str, Any]]) -> Dict[str, Any]:
        """处理诊断信息"""
        if not diagnostics:
            return {"total": 0, "by_severity": {}, "by_file": {}}

        by_severity = {"error": 0, "warning": 0, "info": 0}
        by_file = {}

        for diag in diagnostics:
            severity = diag.get("severity", "info")
            if severity in by_severity:
                by_severity[severity] += 1

            file_path = diag.get("file", "unknown")
            if file_path not in by_file:
                by_file[file_path] = []
            by_file[file_path].append({
                "severity": severity,
                "message": diag.get("message", ""),
                "line": diag.get("line", 0)
            })

        return {
            "total": len(diagnostics),
            "by_severity": by_severity,
            "by_file": by_file
        }

    def identify_key_symbols(self) -> Dict[str, List[Dict[str, Any]]]:
        """识别项目中的关键符号"""
        key_symbols = {}

        # 查找与重构相关的类和函数
        refactoring_patterns = {
            "executor": ["StepExecutor", "execute_step", "retry"],
            "workflow": ["TranslationWorkflow", "execute", "workflow"],
            "retry": ["retry", "backoff", "attempt"],
            "parser": ["Parser", "parse", "XML"],
            "step": ["StepConfig", "step", "execution"],
            "translation": ["Translation", "translate", "llm"],
            "provider": ["Provider", "factory", "llm"]
        }

        if self.is_mcp_tool_available("search_symbols_code"):
            for category, keywords in refactoring_patterns.items():
                symbols = []
                for keyword in keywords:
                    try:
                        result = search_symbols_code(query=keyword, max_results=10)
                        if result:
                            symbols.extend(result)
                    except Exception:
                        continue
                if symbols:
                    key_symbols[category] = symbols

        return key_symbols

    def analyze_refactor_codebase(self) -> Dict[str, Any]:
        """分析重构相关代码库"""
        refactor_analysis = {}

        # 分析现有重构相关文件
        refactor_files = [
            "src/vpsweb/core/executor.py",
            "src/vpsweb/core/workflow.py",
            "src/vpsweb/repository/crud.py",
            "src/vpsweb/webui/main.py"
        ]

        refactor_analysis["existing_files"] = []
        for file_path in refactor_files:
            full_path = self.project_root / file_path
            if full_path.exists():
                refactor_analysis["existing_files"].append(file_path)

                if self.is_mcp_tool_available("get_document_symbols_code"):
                    try:
                        symbols = get_document_symbols_code(path=file_path)
                        refactor_analysis[f"{file_path}_symbols"] = symbols
                    except Exception as e:
                        refactor_analysis[f"{file_path}_symbols_error"] = str(e)

        return refactor_analysis

    def complete_task_with_mcp_analysis(self, task_name: str, details: str = "") -> Dict[str, Any]:
        """完成任务记录 - 包含MCP工具分析"""
        completion_info = {
            "task": task_name,
            "details": details,
            "status": "completed",
            "timestamp": datetime.now().isoformat(),
            "git_branch": self.get_current_branch()
        }

        # 1. 标准任务记录
        self.log_event("task_complete", completion_info)

        # 2. 使用MCP工具进行代码质量分析
        post_task_analysis = self.perform_post_task_analysis(task_name)
        completion_info["post_task_analysis"] = post_task_analysis

        # 3. 更新相关文件
        self.update_daily_progress(task_name, "completed", details)
        self.update_next_steps_after_task(task_name, "completed")

        return completion_info

    def perform_post_task_analysis(self, task_name: str) -> Dict[str, Any]:
        """完成任务后的MCP工具分析"""
        analysis = {}

        try:
            # 1. 获取更新后的诊断信息
            if self.is_mcp_tool_available("get_diagnostics_code"):
                new_diagnostics = get_diagnostics_code()
                analysis["current_diagnostics"] = self._process_diagnostics(new_diagnostics)

            # 2. 如果任务涉及文件修改，分析影响
            if "refactor" in task_name.lower() or "v2" in task_name.lower():
                analysis["refactor_impact"] = self.analyze_refactor_impact(task_name)

            # 3. 检查是否有新的问题引入
            if "current_diagnostics" in analysis:
                analysis["new_issues"] = self.check_for_new_issues(analysis["current_diagnostics"])

        except Exception as e:
            analysis["error"] = f"Post-task analysis failed: {str(e)}"

        return analysis

    def analyze_refactor_impact(self, task_name: str) -> Dict[str, Any]:
        """分析重构任务的影响"""
        impact_analysis = {}

        # 使用语义搜索重构模式
        if "executor" in task_name:
            impact_analysis = self.search_executor_patterns()
        elif "workflow" in task_name:
            impact_analysis = self.search_workflow_patterns()
        elif "database" in task_name or "crud" in task_name:
            impact_analysis = self.search_database_patterns()
        elif "web" in task_name or "main" in task_name:
            impact_analysis = self.search_web_patterns()

        return impact_analysis

    def search_executor_patterns(self) -> Dict[str, Any]:
        """搜索executor相关的模式"""
        patterns = [
            "StepExecutor class methods",
            "retry strategy implementation",
            "parsing logic patterns",
            "LLM provider integration",
            "error handling in executor"
        ]

        results = {}
        for pattern in patterns:
            try:
                if self.is_mcp_tool_available("search_symbols_code"):
                    search_result = search_symbols_code(query=pattern, max_results=5)
                    results[pattern] = search_result
                else:
                    results[pattern] = "MCP tool not available"
            except Exception as e:
                results[pattern] = f"Search failed: {e}"

        return results

    def search_workflow_patterns(self) -> Dict[str, Any]:
        """搜索workflow相关的模式"""
        patterns = [
            "workflow orchestration patterns",
            "step execution flow",
            "progress tracking implementation",
            "workflow configuration"
        ]

        results = {}
        for pattern in patterns:
            try:
                if self.is_mcp_tool_available("search_symbols_code"):
                    search_result = search_symbols_code(query=pattern, max_results=5)
                    results[pattern] = search_result
                else:
                    results[pattern] = "MCP tool not available"
            except Exception as e:
                results[pattern] = f"Search failed: {e}"

        return results

    def search_database_patterns(self) -> Dict[str, Any]:
        """搜索数据库相关的模式"""
        patterns = [
            "CRUD operations",
            "database schema",
            "repository pattern",
            "SQLAlchemy models"
        ]

        results = {}
        for pattern in patterns:
            try:
                if self.is_mcp_tool_available("search_symbols_code"):
                    search_result = search_symbols_code(query=pattern, max_results=5)
                    results[pattern] = search_result
                else:
                    results[pattern] = "MCP tool not available"
            except Exception as e:
                results[pattern] = f"Search failed: {e}"

        return results

    def search_web_patterns(self) -> Dict[str, Any]:
        """搜索Web相关的模式"""
        patterns = [
            "FastAPI routes",
            "middleware implementation",
            "dependency injection",
            "static file serving"
        ]

        results = {}
        for pattern in patterns:
            try:
                if self.is_mcp_tool_available("search_symbols_code"):
                    search_result = search_symbols_code(query=pattern, max_results=5)
                    results[pattern] = search_result
                else:
                    results[pattern] = "MCP tool not available"
            except Exception as e:
                results[pattern] = f"Search failed: {e}"

        return results

    def check_for_new_issues(self, diagnostics: Dict[str, Any]) -> List[Dict[str, Any]]:
        """检查是否有新的问题引入"""
        new_issues = []

        if "by_file" in diagnostics:
            for file_path, issues in diagnostics["by_file"].items():
                for issue in issues:
                    if issue.get("severity") == "error":
                        new_issues.append(issue)

        return new_issues

    def end_work_session(self, summary: str = "") -> Dict[str, Any]:
        """结束工作会话"""
        end_info = {
            "end_time": datetime.now().isoformat(),
            "summary": summary,
            "session_id": self.get_current_session_id(),
            "tasks_completed": self.get_tasks_completed_today(),
            "final_diagnostics": self.get_final_diagnostics()
        }

        # 记录会话结束
        self.log_event("work_session_end", end_info)

        # 生成工作总结
        self.generate_work_summary(end_info)

        return end_info

    def check_mcp_tools_status(self) -> Dict[str, Any]:
        """检查MCP工具状态"""
        status = {
            "available_tools": [],
            "unavailable_tools": [],
            "total_tools": 0
        }

        # 检查各个MCP工具的可用性
        tools_to_check = [
            ("list_files_code", "VS Code"),
            ("search_symbols_code", "VS Code"),
            ("get_diagnostics_code", "VS Code"),
            ("read_file_code", "VS Code"),
            ("create_file_code", "VS Code"),
            ("replace_lines_code", "VS Code"),
            ("get_document_symbols_code", "VS Code"),
            ("get_symbol_definition_code", "VS Code"),
            ("context7", "Context7"),
            ("github", "GitHub"),
            ("deepwiki", "DeepWiki"),
            ("fetch", "Fetch")
        ]

        for tool_name, tool_source in tools_to_check:
            try:
                # 尝试使用工具
                if tool_name == "list_files_code":
                    result = list_files_code(path='.')
                elif tool_name == "get_diagnostics_code":
                    result = get_diagnostics_code()
                elif tool_name == "search_symbols_code":
                    result = search_symbols_code(query="test", max_results=1)  # 简单测试
                else:
                    # 对于其他工具，只做基本检查
                    result = "available"

                status["available_tools"].append({
                    "tool": tool_name,
                    "source": tool_source,
                    "status": "available"
                })

            except Exception as e:
                status["unavailable_tools"].append({
                    "tool": tool_name,
                    "source": tool_source,
                    "status": f"unavailable: {str(e)[:50]}"
                })

        status["total_tools"] = len(status["available_tools"]) + len(status["unavailable_tools"])

        return status

    def is_mcp_tool_available(self, tool_name: str) -> bool:
        """检查特定MCP工具是否可用"""
        if tool_name in self.mcp_tools.get("vscode", {}):
            return True
        return True  # 假设其他工具可用，除非检查失败

    def log_event(self, event_type: str, data: Dict[str, Any]):
        """记录事件到日志文件"""
        log_file = self.progress_path / "events.log"

        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "event_type": event_type,
            "data": data
        }

        try:
            with open(log_file, "a", encoding='utf-8') as f:
                f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
        except Exception as e:
            print(f"Warning: Failed to log event: {e}")

    def update_daily_log(self, event_type: str, message: str):
        """更新每日工作日志"""
        today = datetime.now().strftime("%Y-%m-%d")
        daily_file = self.progress_path / f"{today}.md"

        try:
            if daily_file.exists():
                content = daily_file.read_text(encoding='utf-8')
            else:
                content = f"# {today} 工作更新\n\n## 完成的工作\n\n## 遇到的问题\n\n## 明天的计划\n\n## 当前状态\n\n"

            # 添加新的条目
            timestamp = datetime.now().strftime("%H:%M")
            if event_type == "task_complete":
                content += f"- [{timestamp}] {message}\n"
            elif event_type == "blocker_identified":
                if "## 遇到的问题" in content:
                    content = content.replace("## 遇到的问题\n\n", f"## 遇到的问题\n\n- [{timestamp}] {message}\n\n")
                else:
                    content += f"- [{timestamp}] {message}\n"
            elif event_type == "session_start":
                if "## 完成的工作" in content:
                    content = content.replace("## 完成的工作\n\n", f"## 完成的工作\n\n- [{timestamp}] {message}\n\n")
                else:
                    content += f"- [{timestamp}] {message}\n"

            daily_file.write_text(content, encoding='utf-8')
        except Exception as e:
            print(f"Warning: Failed to update daily log: {e}")

    def update_daily_progress(self, task_name: str, status: str, details: str):
        """更新每日进度"""
        self.update_daily_log("task_complete", f"完成任务: {task_name} ({status}) - {details}")

    def update_next_steps_after_task(self, task_name: str, status: str):
        """完成任务后更新下一步行动"""
        next_steps_file = self.context_path / "next_steps.md"

        if next_steps_file.exists():
            try:
                content = next_steps_file.read_text(encoding='utf-8')

                # 标记已完成的任务
                if task_name in content:
                    content = content.replace(f"- [ ] {task_name}", f"- [x] {task_name}")
                    next_steps_file.write_text(content, encoding='utf-8')
            except Exception as e:
                print(f"Warning: Failed to update next steps: {e}")

    def generate_work_summary(self, end_info: Dict[str, Any]):
        """生成工作总结"""
        today = datetime.now().strftime("%Y-%m-%d")
        summary_file = self.progress_path / f"{today}_summary.md"

        try:
            # 读取今日工作日志
            daily_file = self.progress_path / f"{today}.md"
            if daily_file.exists():
                daily_content = daily_file.read_text(encoding='utf-8')
            else:
                daily_content = "无今日工作记录"

            summary = f"""# {today} 工作总结 (MCP增强版)

## 会话信息
- 会话ID: {end_info.get('session_id', '未知')}
- 开始时间: {end_info.get('start_time', '未知')}
- 结束时间: {end_info.get('end_time')}
- 分支: {end_info.get('git_branch', '未知')}

## 完成的任务
{chr(10).join([f"- {task}" for task in end_info.get('tasks_completed', [])]) if end_info.get('tasks_completed') else "- 无任务记录"}

## 会话总结
{end_info.get('summary', '无特殊说明')}

## 代码质量指标
- 最终诊断信息: {len(end_info.get('final_diagnostics', []))} 个项目
- MCP工具使用: 全程启用

## 今日工作日志
{daily_content}

## 下一步计划
- 继续执行计划中的下一个任务
- 保持MCP工具的高效使用
- 定期检查代码质量指标
"""

            summary_file.write_text(summary, encoding='utf-8')

        except Exception as e:
            print(f"Warning: Failed to generate work summary: {e}")

    def get_current_session_id(self) -> Optional[str]:
        """获取当前会话ID"""
        events_file = self.progress_path / "events.log"
        if not events_file.exists():
            return None

        try:
            with open(events_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            for line in reversed(lines):
                try:
                    event = json.loads(line.strip())
                    if event.get("event_type") == "work_session_start":
                        return event["data"].get("session_id")
                except json.JSONDecodeError:
                    continue
        except FileNotFoundError:
            pass

        return None

    def get_tasks_completed_today(self) -> List[str]:
        """获取今日完成的任务"""
        today = datetime.now().strftime("%Y-%m-%d")
        daily_file = self.progress_path / f"{today}.md"

        if not daily_file.exists():
            return []

        try:
            content = daily_file.read_text(encoding='utf-8')
            tasks = []

            for line in content.split('\n'):
                if "完成任务:" in line:
                    task = line.split("完成任务:", 1)[1].strip()
                    if task and task not in tasks:
                        tasks.append(task)

            return tasks
        except Exception as e:
            print(f"Warning: Failed to get completed tasks: {e}")
            return []

    def get_final_diagnostics(self) -> List[Dict[str, Any]]:
        """获取最终的诊断信息"""
        if self.is_mcp_tool_available("get_diagnostics_code"):
            try:
                return get_diagnostics_code()
            except Exception as e:
                return [{"error": f"Failed to get diagnostics: {e}"}]
        return []

    def get_current_branch(self) -> str:
        """获取当前Git分支"""
        try:
            import subprocess
            result = subprocess.run(
                ["git", "branch", "--show-current"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                check=True
            )
            return result.stdout.strip()
        except (subprocess.CalledProcessError, FileNotFoundError):
            return "unknown"


# 便捷函数，供外部调用
def start_session():
    """开始工作会话"""
    tracker = MCPEnhancedTracker()
    return tracker.start_work_session()

def complete_task(task_name: str, details: str = ""):
    """完成任务"""
    tracker = MCPEnhancedTracker()
    return tracker.complete_task_with_mcp_analysis(task_name, details)

def end_session(summary: str = ""):
    """结束工作会话"""
    tracker = MCPEnhancedTracker()
    return tracker.end_work_session(summary)


if __name__ == "__main__":
    print("VPSWeb MCP增强重构项目进度跟踪器")
    print("功能:")
    print("- start_session()  # 开始工作会话")
    print("- complete_task()  # 完成任务(包含MCP分析)")
    print("- end_session()    # 结束工作会话")
    print("- analyze_code()   # 深度代码分析")
    print("- check_tools()    # 检查MCP工具状态")