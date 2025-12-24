PSD: Vox Poetica Studio Web (vpsweb)

1. 项目概述

项目名称: Vox Poetica Studio Web (vpsweb)
项目目标: 将Dify工作流转换为可配置的Python项目，实现多语言诗歌的专业翻译流程
核心流程: Translator → Editor → Translator (初译→编辑意见→终稿)

2. 系统架构设计

text
vpsweb/
├── config/                 # 配置文件
├── src/                   # 源代码
│   ├── core/             # 核心模块
│   ├── models/           # 数据模型
│   ├── workflows/        # 工作流实现
│   ├── clients/          # LLM客户端
│   └── utils/            # 工具函数
├── tests/                # 测试代码
├── docs/                 # 文档
└── examples/             # 使用示例
3. 核心模块设计

3.1 配置管理系统

python
# 配置文件结构
config/
├── models.yaml           # 模型配置
├── prompts/              # 提示词模板
│   ├── initial_translation.yaml
│   ├── editor_review.yaml
│   └── translator_revision.yaml
├── workflows/            # 工作流配置
│   └── poetry_translation.yaml
└── app.yaml             # 应用配置
3.2 数据模型

python
# 核心数据类
class TranslationRequest:
    original_poem: str
    source_lang: str  
    target_lang: str

class TranslationStep:
    input: Dict
    output: Dict
    metadata: Dict

class WorkflowResult:
    steps: List[TranslationStep]
    final_output: Dict
3.3 工作流引擎

python
class PoetryTranslationWorkflow:
    def __init__(self, config: WorkflowConfig):
        self.config = config
        self.steps = [
            InitialTranslationStep(),
            EditorReviewStep(), 
            TranslatorRevisionStep(),
            ResultAggregationStep()
        ]
    
    async def execute(self, request: TranslationRequest) -> WorkflowResult
4. 技术规格

4.1 依赖技术栈

Python 3.9+
Pydantic: 数据验证和配置管理
aiohttp: 异步HTTP客户端
PyYAML: 配置文件解析
pytest: 测试框架
FastAPI (预留): 未来Web UI
4.2 LLM客户端集成

python
class LLMClient:
    async def generate(self, prompt: str, model_config: ModelConfig) -> str

class MultiProviderClient:
    def __init__(self):
        self.clients = {
            'tongyi': TongyiClient(),
            'deepseek': DeepseekClient()
        }
5. 工作流转换策略

5.1 Dify DSL到Python的映射

Dify组件	Python实现
Start节点	TranslationRequest类
LLM节点	对应的Step类 + LLMClient
Code节点	专门的解析函数
Template-transform节点	结果聚合器
End节点	WorkflowResult类
5.2 提示词模板管理

yaml
# prompts/initial_translation.yaml
system_prompt: |
  You are a renowned poet and professional {source_lang}-to-{target_lang} poetry translator...
  
user_prompt: |
  Your task is to provide a high-quality translation of a poem from {source_lang} to {target_lang}...
  
output_format:
  type: xml
  structure:
    initial_translation: str
    initial_translation_notes: str
6. 配置化设计

6.1 模型配置

yaml
# config/models.yaml
tongyi:
  qwen-max-latest:
    provider: "tongyi"
    api_key: ${TONGYI_API_KEY}
    parameters:
      temperature: 0.7
      max_tokens: 4000

deepseek:
  deepseek-reasoner:
    provider: "deepseek" 
    api_key: ${DEEPSEEK_API_KEY}
    parameters:
      max_tokens: 8192
6.2 工作流配置

yaml
# workflows/poetry_translation.yaml
steps:
  initial_translation:
    model: "tongyi/qwen-max-latest"
    prompt: "initial_translation"
    output_parser: "xml"
    
  editor_review:
    model: "deepseek/deepseek-reasoner" 
    prompt: "editor_review"
    
  translator_revision:
    model: "tongyi/qwen-max-0919"
    prompt: "translator_revision"
    parameters:
      temperature: 0.2
      max_tokens: 8001
7. 输出结构化设计

python
@dataclass
class StepOutput:
    content: Dict[str, Any]
    metadata: Dict[str, Any]
    errors: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        return asdict(self)
8. 扩展性考虑

8.1 插件式架构

可插拔的LLM提供商
可配置的工作流步骤
模块化的输出解析器
8.2 Web UI预留接口

python
# 为未来FastAPI应用预留的接口
class WebService:
    async def translate_poem(request: TranslationRequest) -> JSONResponse
    async def get_workflow_status(workflow_id: str) -> JSONResponse
9. 开发计划

Phase 1: 基础框架和配置系统
Phase 2: LLM客户端集成
Phase 3: 工作流步骤实现
Phase 4: 输出解析和结果聚合
Phase 5: 测试和文档
Phase 6: Web UI集成（可选）

10. 质量保证

单元测试覆盖核心功能
集成测试验证工作流
配置文件验证
错误处理和日志记录