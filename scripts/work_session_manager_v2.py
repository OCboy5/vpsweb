#!/usr/bin/env python3
"""
VPSWeb 重构项目工作会话管理器 (MCP增强版)

自动化工作会话的开始、进度跟踪和结束，集成所有MCP工具。
"""

import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional
import subprocess

# 导入MCP增强跟踪器
try:
    from .mcp_enhanced_tracker_v2 import MCPEnhancedTracker
    MCP_AVAILABLE = True
except ImportError:
    print("Warning: MCP Enhanced Tracker not available, falling back to basic tracker")
    MCP_AVAILABLE = False


class WorkSessionManager:
    def __init__(self, project_root: str = "."):
        self.project_root = Path(project_root)
        self.docs_path = self.project_root / "docs" / "claudecode"
        self.progress_path = self.docs_path / "progress" / "daily_updates"
        self.context_path = self.docs_path / "context"

        # 确保目录存在
        self.progress_path.mkdir(parents=True, exist_ok=True)
        self.context_path.mkdir(parents=True, exist_ok=True)

        # 初始化MCP增强跟踪器
        if MCP_AVAILABLE:
            self.mcp_tracker = MCPEnhancedTracker(project_root)
        else:
            self.mcp_tracker = None

    def start_work_session(self) -> Dict[str, any]:
        """开始工作会话 - MCP增强版"""
        session_id = datetime.now().strftime("%Y%m%d_%H%M%S")

        # 获取基础状态信息
        starting_state = self.get_current_state()
        git_branch = self.get_current_branch()
        uncommitted_changes = self.get_uncommitted_changes()

        session_info = {
            "session_id": session_id,
            "start_time": datetime.now().isoformat(),
            "starting_state": starting_state,
            "git_branch": git_branch,
            "uncommitted_changes": uncommitted_changes
        }

        # 如果MCP增强跟踪器可用，进行深度分析
        if self.mcp_tracker:
            try:
                # 使用MCP工具进行深度代码分析
                mcp_analysis = self.mcp_tracker.start_work_session()
                session_info["mcp_analysis"] = mcp_analysis

                # 记录MCP工具增强的会话开始
                enhanced_session_info = session_info.copy()
                enhanced_session_info["mcp_enhanced"] = True
                self.log_event("mcp_enhanced_session_start", enhanced_session_info)

                print(f"✅ MCP增强的工作会话 {session_id} 已启动")
                print(f"📊 代码质量分析: {len(mcp_analysis.get('diagnostics', []))} 个诊断项目")
                print(f"🔍 关键符号识别: {len(mcp_analysis.get('key_symbols', {}))} 个模式")

            except Exception as e:
                print(f"⚠️  MCP增强功能暂时不可用: {e}")
                # 记录到事件日志但继续正常流程
                self.log_event("mcp_enhancement_failed", {
                    "session_id": session_id,
                    "error": str(e),
                    "fallback_mode": True
                })

        # 记录标准会话开始
        self.log_event("work_session_start", session_info)

        # 更新今日日志
        self.update_daily_log("session_start", f"工作会话 {session_id} 开始")

        return session_info

    def complete_task(self, task_name: str, details: str = "", status: str = "completed") -> Dict[str, any]:
        """完成任务记录"""
        completion_info = {
            "task": task_name,
            "status": status,
            "details": details,
            "timestamp": datetime.now().isoformat(),
            "git_branch": self.get_current_branch()
        }

        # 记录任务完成
        self.log_event("task_complete", completion_info)

        # 更新相关文件
        self.update_daily_progress(task_name, status, details)
        self.update_next_steps_after_task(task_name, status)
        self.update_project_status()

        return completion_info

    def log_blocker(self, blocker: str, severity: str = "medium", suggested_action: str = "") -> Dict[str, any]:
        """记录阻塞问题"""
        blocker_info = {
            "blocker": blocker,
            "severity": severity,
            "suggested_action": suggested_action,
            "timestamp": datetime.now().isoformat(),
            "session_id": self.get_current_session_id()
        }

        # 记录阻塞
        self.log_event("blocker_identified", blocker_info)

        # 更新问题跟踪文件
        self.update_issues_file(blocker, severity)

        return blocker_info

    def end_work_session(self, summary: str = "") -> Dict[str, any]:
        """结束工作会话"""
        end_info = {
            "end_time": datetime.now().isoformat(),
            "summary": summary,
            "ending_state": self.get_current_state(),
            "session_id": self.get_current_session_id(),
            "tasks_completed": self.get_tasks_completed_today()
        }

        # 记录会话结束
        self.log_event("work_session_end", end_info)

        # 生成工作总结
        self.generate_work_summary(end_info)

        return end_info

    def get_current_state(self) -> Dict[str, any]:
        """获取当前项目状态"""
        state = {}

        # 从current_state.md读取
        current_state_file = self.context_path / "current_state.md"
        if current_state_file.exists():
            content = current_state_file.read_text(encoding='utf-8')

            # 解析当前阶段
            if "## 🎯 当前阶段" in content:
                state["current_phase"] = self.extract_section(content, "## 🎯 当前阶段")

            # 解析正在进行的任务
            if "## 📋 正在进行的任务" in content:
                state["current_tasks"] = self.extract_section(content, "## 📋 正在进行的任务")

        # 添加实时信息
        state["timestamp"] = datetime.now().isoformat()
        state["git_status"] = self.get_git_status()

        return state

    def update_daily_log(self, event_type: str, message: str):
        """更新每日工作日志"""
        today = datetime.now().strftime("%Y-%m-%d")
        daily_file = self.progress_path / f"{today}.md"

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

    def update_daily_progress(self, task_name: str, status: str, details: str):
        """更新每日进度"""
        self.update_daily_log("task_complete", f"完成任务: {task_name} ({status})")

    def log_event(self, event_type: str, data: Dict[str, any]):
        """记录事件到日志文件"""
        log_file = self.progress_path / "events.log"

        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "event_type": event_type,
            "data": data
        }

        with open(log_file, "a", encoding='utf-8') as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")

    def get_current_branch(self) -> str:
        """获取当前Git分支"""
        try:
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

    def get_git_status(self) -> Dict[str, any]:
        """获取Git状态"""
        status = {"clean": True, "branch": "unknown"}

        try:
            # 检查分支
            status["branch"] = self.get_current_branch()

            # 检查是否有未提交的更改
            result = subprocess.run(
                ["git", "diff", "--quiet"],
                cwd=self.project_root
            )
            if result.returncode != 0:
                status["clean"] = False

            result = subprocess.run(
                ["git", "diff", "--cached", "--quiet"],
                cwd=self.project_root
            )
            if result.returncode != 0:
                status["clean"] = False

        except (subprocess.CalledProcessError, FileNotFoundError):
            pass

        return status

    def get_uncommitted_changes(self) -> List[str]:
        """获取未提交的更改"""
        changes = []

        try:
            result = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                check=True
            )

            for line in result.stdout.strip().split('\n'):
                if line.strip():
                    changes.append(line.strip())

        except (subprocess.CalledProcessError, FileNotFoundError):
            pass

        return changes

    def extract_section(self, content: str, section_header: str) -> str:
        """从Markdown内容中提取特定部分"""
        lines = content.split('\n')
        section_lines = []
        in_section = False

        for line in lines:
            if line.strip() == section_header:
                in_section = True
                continue
            elif line.startswith("## ") and in_section:
                break
            elif in_section and line.strip():
                section_lines.append(line.strip())

        return '\n'.join(section_lines)

    def update_next_steps_after_task(self, task_name: str, status: str):
        """完成任务后更新下一步行动"""
        next_steps_file = self.context_path / "next_steps.md"

        if next_steps_file.exists():
            content = next_steps_file.read_text(encoding='utf-8')

            # 标记已完成的任务
            if task_name in content:
                content = content.replace(f"[ ] {task_name}", f"[x] {task_name}")
                next_steps_file.write_text(content, encoding='utf-8')

    def update_project_status(self):
        """更新项目状态文件"""
        # 更新project_overview.md中的进度
        overview_file = self.docs_path / "status" / "project_overview.md"
        if overview_file.exists():
            content = overview_file.read_text(encoding='utf-8')

            # 更新最后修改时间
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M")
            content = content.replace(
                "**最后更新**: ",
                f"**最后更新**: {current_time}"
            )

            overview_file.write_text(content, encoding='utf-8')

    def update_issues_file(self, blocker: str, severity: str):
        """更新问题跟踪文件"""
        issues_file = self.context_path / "issues_and_blockers.md"

        if issues_file.exists():
            content = issues_file.read_text(encoding='utf-8')
        else:
            content = "# 问题和阻塞跟踪\n\n## 🔴 阻塞问题\n\n## 🟡 技术问题\n\n## 📋 普通问题\n\n"

        # 添加新问题到阻塞部分
        new_issue = f"### 问题{len(self.get_existing_issues()) + 1}\n- **描述**: {blocker}\n- **状态**: 待解决\n- **解决方案**: 待确定\n- **预计解决时间**: 待定\n\n"

        if "## 🔴 阻塞问题" in content:
            content = content.replace("## 🔴 阻塞问题\n\n", f"## 🔴 阻塞问题\n\n{new_issue}")

        issues_file.write_text(content, encoding='utf-8')

    def get_existing_issues(self) -> List[str]:
        """获取现有问题列表"""
        issues_file = self.context_path / "issues_and_blockers.md"
        if not issues_file.exists():
            return []

        content = issues_file.read_text(encoding='utf-8')
        return [line.strip() for line in content.split('\n') if line.startswith("###")]

    def get_current_session_id(self) -> Optional[str]:
        """获取当前会话ID"""
        events_file = self.progress_path / "events.log"
        if not events_file.exists():
            return None

        # 读取最后一个work_session_start事件
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

        content = daily_file.read_text(encoding='utf-8')
        tasks = []

        for line in content.split('\n'):
            if "完成任务:" in line:
                task = line.split("完成任务:", 1)[1].strip()
                if task and task not in tasks:
                    tasks.append(task)

        return tasks

    def generate_work_summary(self, end_info: Dict[str, any]):
        """生成工作总结"""
        summary = f"""
# {datetime.now().strftime('%Y-%m-%d')} 工作总结

## 会话信息
- 会话ID: {end_info['session_id']}
- 开始时间: {end_info['start_time'] if 'start_time' in end_info else '未知'}
- 结束时间: {end_info['end_time']}
- 分支: {end_info.get('git_branch', '未知')}

## 完成的任务
{chr(10).join([f"- {task}" for task in end_info.get('tasks_completed', [])]) if end_info.get('tasks_completed') else "- 无任务记录"}

## 会话总结
{end_info.get('summary', '无特殊说明')}

## 下一步计划
- 继续执行计划中的下一个任务
- 保持项目跟踪系统的更新
- 定期检查项目健康状态
"""

        # 将总结添加到今日日志
        today = datetime.now().strftime("%Y-%m-%d")
        summary_file = self.progress_path / f"{today}_summary.md"
        summary_file.write_text(summary, encoding='utf-8')


# 便捷函数，供外部调用
def start_session():
    """开始工作会话"""
    manager = WorkSessionManager()
    return manager.start_work_session()

def complete_task(task_name: str, details: str = ""):
    """完成任务"""
    manager = WorkSessionManager()
    return manager.complete_task(task_name, details)

def end_session(summary: str = ""):
    """结束工作会话"""
    manager = WorkSessionManager()
    return manager.end_work_session(summary)

if __name__ == "__main__":
    # 示例用法
    print("VPSWeb 重构项目工作会话管理器")
    print("使用方法:")
    print("python scripts/work_session_manager.py start  # 开始会话")
    print("python scripts/work_session_manager.py complete <task_name>  # 完成任务")
    print("python scripts/work_session_manager.py end  # 结束会话")