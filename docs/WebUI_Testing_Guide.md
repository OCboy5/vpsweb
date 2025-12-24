# VPSWeb WebUI 测试指南

**重构后的WebUI系统完整测试流程**

## 🎯 **快速开始**

### **1. 启动重构后的服务器**
```bash
# 在项目根目录运行
./scripts/start_v2.sh
```

### **2. 访问Web界面**
- **主页**: http://127.0.0.1:8000
- **API文档**: http://127.0.0.1:8000/docs
- **健康检查**: http://127.0.0.1:8000/health
- **交互式API**: http://127.0.0.1:8000/redoc

## 🔧 **启动前准备**

### **环境检查**
```bash
# 1. 检查Poetry环境
poetry --version

# 2. 安装依赖
poetry install

# 3. 检查数据库
ls -la repository_root/repo.db

# 4. 设置Python路径
export PYTHONPATH="$(pwd)/src:$PYTHONPATH"
```

### **数据库初始化（如需要）**
```bash
# 如果数据库不存在，初始化它
./scripts/setup-database.sh init
```

## 🌐 **WebUI功能测试**

### **1. 主页访问测试**
**URL**: http://127.0.0.1:8000

**预期结果**:
- ✅ 页面正常加载
- ✅ 显示VPSWeb标题
- ✅ 显示导航菜单
- ✅ 显示统计信息或欢迎页面
- ✅ 响应式设计适配

**测试检查点**:
- [ ] 页面标题正确显示
- [ ] CSS样式正常加载
- [ ] JavaScript功能正常
- [ ] 没有404错误
- [ ] 链接可正常点击

### **2. API端点测试**

#### **2.1 诗歌管理API**
```bash
# 获取诗歌列表
curl http://127.0.0.1:8000/api/v1/poems

# 创建新诗歌
curl -X POST http://127.0.0.1:8000/api/v1/poems \
  -H "Content-Type: application/json" \
  -d '{
    "title": "测试诗歌",
    "author": "测试作者",
    "content": "这是测试诗歌内容",
    "language": "Chinese"
  }'

# 获取特定诗歌
curl http://127.0.0.1:8000/api/v1/poems/1
```

#### **2.2 翻译管理API**
```bash
# 获取翻译列表
curl http://127.0.0.1:8000/api/v1/translations

# 创建新翻译
curl -X POST http://127.0.0.1:8000/api/v1/translations \
  -H "Content-Type: application/json" \
  -d '{
    "poem_id": 1,
    "source_language": "Chinese",
    "target_language": "English",
    "workflow_mode": "hybrid"
  }'
```

#### **2.3 统计信息API**
```bash
# 获取统计信息
curl http://127.0.0.1:8000/api/v1/statistics
```

#### **2.4 诗人信息API**
```bash
# 获取诗人列表
curl http://127.0.0.1:8000/api/v1/poets

# 获取特定诗人信息
curl http://127.0.0.1:8000/api/v1/poets/1
```

### **3. 健康检查和监控**

#### **健康检查端点**
```bash
# 基本健康检查
curl http://127.0.0.1:8000/health

# 预期响应
{
  "status": "healthy",
  "version": "0.3.12",
  "services": {
    "database": "connected",
    "poem_service": "available",
    "translation_service": "available"
  }
}
```

#### **性能监控**
```bash
# 检查性能指标
curl http://127.0.0.1:8000/api/v1/performance
```

## 🔍 **功能测试清单**

### **诗歌管理功能**
- [ ] **查看诗歌列表**: 主页显示诗歌列表
- [ ] **诗歌搜索**: 按标题、作者、语言搜索
- [ ] **诗歌详情**: 点击诗歌查看详细信息
- [ ] **创建诗歌**: 通过表单创建新诗歌
- [ ] **编辑诗歌**: 修改现有诗歌信息
- [ ] **删除诗歌**: 删除诗歌（带确认）

### **翻译功能**
- [ ] **翻译列表**: 查看所有翻译
- [ ] **创建翻译**: 为诗歌创建翻译
- [ ] **翻译详情**: 查看翻译内容和元数据
- [ ] **工作流模式**: 支持不同的翻译工作流
- [ ] **翻译状态**: 跟踪翻译进度

### **统计分析功能**
- [ ] **仪表板**: 显示总体统计信息
- [ ] **诗歌统计**: 诗歌数量、语言分布
- [ ] **翻译统计**: 翻译成功率、工作流分布
- [ ] **用户活动**: 最近操作记录
- [ ] **图表展示**: 可视化统计数据

### **用户界面功能**
- [ ] **响应式设计**: 适配不同屏幕尺寸
- [ ] **导航菜单**: 清晰的导航结构
- [ ] **搜索功能**: 全站搜索
- [ ] **分页功能**: 大数据集分页显示
- [ ] **错误处理**: 友好的错误消息
- [ ] **加载状态**: 操作反馈

## 🧪 **集成测试**

### **1. 端到端工作流测试**
```bash
# 完整的诗歌创建和翻译流程
# 1. 创建诗歌
POEM_RESPONSE=$(curl -s -X POST http://127.0.0.1:8000/api/v1/poems \
  -H "Content-Type: application/json" \
  -d '{
    "title": "集成测试诗歌",
    "author": "测试作者",
    "content": "这是集成测试诗歌内容\n包含多行文本",
    "language": "Chinese"
  }')

# 提取诗歌ID
POEM_ID=$(echo $POEM_RESPONSE | jq -r '.data.id')

# 2. 创建翻译
curl -s -X POST http://127.0.0.1:8000/api/v1/translations \
  -H "Content-Type: application/json" \
  -d "{
    \"poem_id\": $POEM_ID,
    \"source_language\": \"Chinese\",
    \"target_language\": \"English\",
    \"workflow_mode\": \"hybrid\"
  }"

# 3. 验证结果
curl -s http://127.0.0.1:8000/api/v1/poems/$POEM_ID
```

### **2. 性能测试**
```bash
# 并发请求测试
for i in {1..10}; do
  curl -s http://127.0.0.1:8000/api/v1/poems &
done
wait

# 大数据量测试
curl -s "http://127.0.0.1:8000/api/v1/poems?limit=100&offset=0"
```

### **3. 错误处理测试**
```bash
# 测试无效诗歌ID
curl http://127.0.0.1:8000/api/v1/poems/99999

# 测试无效数据
curl -X POST http://127.0.0.1:8000/api/v1/poems \
  -H "Content-Type: application/json" \
  -d '{"invalid": "data"}'

# 测试缺失必需字段
curl -X POST http://127.0.0.1:8000/api/v1/poems \
  -H "Content-Type: application/json" \
  -d '{"title": ""}'
```

## 🔧 **调试和故障排除**

### **常见问题**

#### **1. 启动失败**
```bash
# 检查端口占用
lsof -i :8000

# 检查Python路径
echo $PYTHONPATH

# 检查依赖
poetry show

# 测试导入
poetry run python -c "from vpsweb.webui.main_v2 import create_app; print('OK')"
```

#### **2. 数据库连接问题**
```bash
# 检查数据库文件
ls -la repository_root/repo.db

# 测试数据库连接
poetry run python -c "
from vpsweb.repository.database import get_db
print('Database connection test')
"

# 重新初始化数据库
./scripts/setup-database.sh reset
```

#### **3. 服务层错误**
```bash
# 检查服务注册
poetry run python -c "
from vpsweb.core.container import DIContainer
from vpsweb.webui.main_v2 import ApplicationFactoryV2
app = ApplicationFactoryV2.create_application()
print('Services initialized successfully')
"
```

### **日志调试**
```bash
# 查看服务器日志
# 启动时的日志会显示在终端

# 启用详细日志
export VPSWEB_DEBUG=true
./scripts/start_v2.sh

# 检查应用日志
tail -f repository_root/logs/app.log
```

## 📊 **测试报告模板**

### **功能测试结果**
```
VPSWeb WebUI 测试报告
====================

测试日期: [日期]
测试环境: [环境描述]
服务器地址: http://127.0.0.1:8000

功能测试结果:
✅ 诗歌管理: 通过/失败
✅ 翻译功能: 通过/失败
✅ 统计分析: 通过/失败
✅ 用户界面: 通过/失败
✅ API端点: 通过/失败

性能测试结果:
- 响应时间: [时间]
- 并发处理: [结果]
- 内存使用: [使用量]

发现问题:
1. [问题描述]
2. [问题描述]

建议改进:
1. [改进建议]
2. [改进建议]
```

## 🚀 **自动化测试脚本**

### **基本功能测试脚本**
```bash
#!/bin/bash
# basic_functionality_test.sh

echo "🧪 VPSWeb WebUI 基本功能测试"
echo "============================="

BASE_URL="http://127.0.0.1:8000"

# 测试服务器是否运行
echo "1. 测试服务器连接..."
if curl -s "$BASE_URL/health" > /dev/null; then
    echo "✅ 服务器运行正常"
else
    echo "❌ 服务器未运行"
    exit 1
fi

# 测试API端点
echo "2. 测试API端点..."
endpoints=(
    "/api/v1/poems"
    "/api/v1/translations"
    "/api/v1/statistics"
    "/api/v1/poets"
)

for endpoint in "${endpoints[@]}"; do
    if curl -s "$BASE_URL$endpoint" > /dev/null; then
        echo "✅ $endpoint - 正常"
    else
        echo "❌ $endpoint - 失败"
    fi
done

echo "✅ 基本功能测试完成"
```

## 🎯 **成功标准**

### **启动成功标志**
- [ ] 服务器启动无错误
- [ ] 健康检查返回200状态
- [ ] 数据库连接正常
- [ ] 所有服务初始化成功

### **功能测试成功标志**
- [ ] 所有API端点响应正常
- [ ] Web界面正常显示
- [ ] 数据CRUD操作正常
- [ ] 错误处理工作正常

### **性能测试成功标志**
- [ ] 响应时间 < 2秒
- [ ] 支持10个并发请求
- [ ] 内存使用稳定
- [ ] 无内存泄漏

---

**🎉 完成此指南中的所有测试后，您将全面验证重构后的VPSWeb WebUI系统功能！**