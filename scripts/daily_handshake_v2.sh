#!/bin/bash
# VPSWeb 重构项目每日握手脚本

echo "=== VPSWeb 重构项目每日握手 ==="
echo "时间: $(date)"
echo ""

# 检查是否在正确的目录
if [ ! -f "pyproject.toml" ]; then
    echo "❌ 错误: 请在项目根目录执行此脚本"
    echo "当前目录: $(pwd)"
    exit 1
fi

# 显示昨日总结
echo "📝 昨日工作回顾:"
YESTERDAY=$(date -d "yesterday" +%Y-%m-%d 2>/dev/null || date -v-1d +%Y-%m-%d 2>/dev/null)
YESTERDAY_FILE="docs/claudecode/progress/daily_updates/$YESTERDAY.md"

if [ -f "$YESTERDAY_FILE" ]; then
    echo "文件: $YESTERDAY_FILE"
    if grep -q "## 完成的工作" "$YESTERDAY_FILE"; then
        echo "完成的主要工作:"
        grep -A 10 "## 完成的工作" "$YESTERDAY_FILE" | grep -E "^\s*- " | head -5 | sed 's/^/  /'
    else
        echo "  无具体工作记录"
    fi
else
    echo "  无昨日记录"
fi
echo ""

# 显示今日计划
echo "📋 今日计划:"
NEXT_STEPS_FILE="docs/claudecode/context/next_steps.md"
if [ -f "$NEXT_STEPS_FILE" ]; then
    if grep -q "## 🚀 立即执行" "$NEXT_STEPS_FILE"; then
        grep -A 10 "## 🚀 立即执行" "$NEXT_STEPS_FILE" | grep -E "^\s*\[\s*\]" | head -5 | sed 's/^/  /'
    else
        echo "  查看文档获取详细计划"
    fi
else
    echo "  无今日计划记录"
fi
echo ""

# 显示当前状态
echo "🎯 当前项目状态:"
CURRENT_STATE_FILE="docs/claudecode/context/current_state.md"
if [ -f "$CURRENT_STATE_FILE" ]; then
    if grep -q "## 🎯 当前阶段" "$CURRENT_STATE_FILE"; then
        grep -A 5 "## 🎯 当前阶段" "$CURRENT_STATE_FILE" | sed 's/^/  /'
    fi

    if grep -q "## 📋 正在进行的任务" "$CURRENT_STATE_FILE"; then
        echo ""
        grep -A 3 "## 📋 正在进行的任务" "$CURRENT_STATE_FILE" | sed 's/^/  /'
    fi
else
    echo "  无状态记录"
fi
echo ""

# 显示当前分支
echo "🌿 Git状态:"
if git rev-parse --git-dir > /dev/null 2>&1; then
    CURRENT_BRANCH=$(git branch --show-current 2>/dev/null || echo "未知")
    echo "  当前分支: $CURRENT_BRANCH"

    # 检查是否有未提交的更改
    if ! git diff --quiet 2>/dev/null || ! git diff --cached --quiet 2>/dev/null; then
        echo "  ⚠️  有未提交的更改"
    else
        echo "  ✅ 工作目录干净"
    fi
else
    echo "  不是Git仓库"
fi
echo ""

# 检查待处理的问题
echo "🚨 需要注意:"
ISSUES_FILE="docs/claudecode/context/issues_and_blockers.md"
if [ -f "$ISSUES_FILE" ]; then
    if grep -q "## 🔴 阻塞问题" "$ISSUES_FILE"; then
        BLOCKERS=$(grep -c "^\s*### 问题" "$ISSUES_FILE" 2>/dev/null || echo "0")
        if [ "$BLOCKERS" -gt 0 ]; then
            echo "  有 $BLOCKERS 个阻塞问题需要处理"
        fi
    fi

    if grep -q "## 🟡 技术问题 (需要决策)" "$ISSUES_FILE"; then
        DECISIONS=$(grep -c "需要决策\|需要确认" "$ISSUES_FILE" 2>/dev/null || echo "0")
        if [ "$DECISIONS" -gt 0 ]; then
            echo "  有 $DECISIONS 个事项需要您的决策"
        fi
    fi
else
    echo "  无特殊问题记录"
fi
echo ""

# 显示健康检查结果
echo "🏥 项目健康:"
OVERVIEW_FILE="docs/claudecode/status/project_overview.md"
if [ -f "$OVERVIEW_FILE" ]; then
    echo "  ✅ 项目状态文件已更新"

    # 检查最后更新时间
    if command -v stat >/dev/null 2>&1; then
        if stat -c %Y "$OVERVIEW_FILE" >/dev/null 2>&1; then
            # Linux
            MOD_TIME=$(stat -c %Y "$OVERVIEW_FILE" 2>/dev/null)
        else
            # macOS
            MOD_TIME=$(stat -f %m "$OVERVIEW_FILE" 2>/dev/null)
        fi

        if [ -n "$MOD_TIME" ]; then
            DAYS_SINCE=$(( ($(date +%s) - MOD_TIME) / 86400 ))
            if [ "$DAYS_SINCE" -eq 0 ]; then
                echo "  ✅ 状态文件是今天更新的"
            elif [ "$DAYS_SINCE" -le 2 ]; then
                echo "  ⚠️  状态文件是 $DAYS_SINCE 天前更新的"
            else
                echo "  ❌ 状态文件是 $DAYS_SINCE 天前更新的，需要更新"
            fi
        fi
    fi
else
    echo "  ❌ 项目状态文件不存在"
fi

# 检查今日日志
TODAY_FILE="docs/claudecode/progress/daily_updates/$(date +%Y-%m-%d).md"
if [ -f "$TODAY_FILE" ]; then
    echo "  ✅ 今日日志已创建"
else
    echo "  ℹ️  今日日志尚未创建"
fi
echo ""

# Python环境检查
echo "🐍 开发环境:"
if command -v poetry >/dev/null 2>&1; then
    echo "  ✅ Poetry 已安装"
    if poetry env info >/dev/null 2>&1; then
        echo "  ✅ Poetry 环境已配置"
        PYTHON_VERSION=$(poetry run python --version 2>/dev/null)
        if [ -n "$PYTHON_VERSION" ]; then
            echo "  Python: $PYTHON_VERSION"
        fi
    else
        echo "  ❌ Poetry 环境未配置，请运行: poetry install"
    fi
else
    echo "  ❌ Poetry 未安装"
fi
echo ""

# 提供今日日志模板（如果不存在）
if [ ! -f "$TODAY_FILE" ]; then
    echo "💡 建议创建今日工作日志，模板如下:"
    echo "echo '# $(date +%Y-%m-%d) 工作更新'"
    echo "echo ''"
    echo "echo '## 完成的工作'"
    echo "echo '- '"
    echo "echo ''"
    echo "echo '## 遇到的问题'"
    echo "echo '- '"
    echo "echo ''"
    echo "echo '## 明天的计划'"
    echo "echo '- '"
    echo "echo ''"
    echo "echo '## 当前状态'"
    echo "echo '- 分支: \$(git branch --show-current)'"
    echo "echo '- 进度: '"
    echo ""
    echo "# 或者我可以帮您自动创建，请告诉我"
fi

echo ""
echo "=== 每日握手完成 ==="
echo "🚀 现在可以开始工作了！如果需要我帮助执行任何任务，请告诉我。"