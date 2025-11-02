#!/bin/bash
# 快速项目状态检查

echo "=== VPSWeb 重构项目状态 ==="
echo "更新时间: $(date)"
echo ""

# 当前分支
echo "🌿 当前分支:"
if git rev-parse --git-dir > /dev/null 2>&1; then
    git branch --show-current
else
    echo "不是git仓库"
fi
echo ""

# 最近更新
echo "📝 最近更新:"
TODAY_FILE="docs/claudecode/progress/daily_updates/$(date +%Y-%m-%d).md"
if [ -f "$TODAY_FILE" ]; then
    echo "今日已更新: $(wc -l < "$TODAY_FILE") 行"
else
    echo "今日未更新"
fi
echo ""

# 项目概览
OVERVIEW_FILE="docs/claudecode/status/project_overview.md"
if [ -f "$OVERVIEW_FILE" ]; then
    echo "📊 项目状态: 已更新"
    echo "最后修改: $(stat -c %y "$OVERVIEW_FILE" 2>/dev/null || stat -f %Sm "$OVERVIEW_FILE" 2>/dev/null)"
else
    echo "📊 项目状态: 未创建"
fi
echo ""

# 跟踪系统文件
echo "📁 跟踪系统文件:"
TRACKING_FILES=(
    "docs/claudecode/project_tracking_system.md"
    "docs/claudecode/context/current_state.md"
    "docs/claudecode/context/next_steps.md"
    "docs/claudecode/context/issues_and_blockers.md"
)

for file in "${TRACKING_FILES[@]}"; do
    if [ -f "$file" ]; then
        echo "  ✅ $file"
    else
        echo "  ❌ $file"
    fi
done
echo ""

# Python环境检查
echo "🐍 Python环境:"
if command -v poetry > /dev/null 2>&1; then
    echo "  ✅ Poetry 已安装"
    if poetry env info > /dev/null 2>&1; then
        echo "  ✅ Poetry 环境已配置"
    else
        echo "  ❌ Poetry 环境未配置"
    fi
else
    echo "  ❌ Poetry 未安装"
fi
echo ""

# 下一步行动
echo "📋 下一步:"
NEXT_STEPS_FILE="docs/claudecode/context/next_steps.md"
if [ -f "$NEXT_STEPS_FILE" ]; then
    echo "立即执行任务:"
    grep -E "^\s*-\s*\[.*\]" "$NEXT_STEPS_FILE" | head -3 | sed 's/^/  /'
else
    echo "未找到下一步计划文件"
fi
echo ""

echo "=== 状态检查完成 ==="