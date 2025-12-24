# Workflow Modes

VPSWeb supports different workflow modes to optimize for cost, quality, and reasoning capabilities.

## Overview

The workflow modes control which LLM models are used for each step of the 3-step Translator→Editor→Translator process:
1. **Initial Translation**: Raw translation attempt
2. **Editor Review**: Critical assessment and suggestions
3. **Translator Revision**: Final polished translation

## Available Modes

### Reasoning Mode
- **Models**: deepseek-reasoner or similar reasoning models
- **Characteristics**:
  - Prompts should not interfere with Chain-of-Thought
  - Higher token limits for reasoning traces
  - Temperature settings optimized for analytical work
- **Use Case**: Maximum quality translation where cost is secondary
- **Pros**: Highest quality, detailed reasoning
- **Cons**: Higher cost, slower processing

### Non-Reasoning Mode
- **Models**: qwen-plus or similar standard models
- **Characteristics**:
  - Direct, structured prompts for specific outputs
  - Optimized for efficiency and consistency
  - Lower temperature settings for reliability
- **Use Case**: Fast, cost-effective translations
- **Pros**: Fast, cost-effective, consistent
- **Cons**: Less detailed reasoning

### Hybrid Mode (Recommended)
- **Models**: Strategic combination of reasoning and non-reasoning models
- **Characteristics**:
  - Non-reasoning for initial translation (efficiency)
  - Reasoning for editor review (quality)
  - Non-reasoning for translator revision (consistency)
- **Use Case**: Optimal balance of quality and cost
- **Pros**: Best cost-quality ratio, leverages strengths of different models
- **Cons**: More complex configuration

## Configuration

Workflow modes are configured in `config/default.yaml`:

```yaml
workflow:
  mode: "hybrid"  # reasoning | non_reasoning | hybrid

  # Mode-specific settings
  reasoning:
    initial_translation_model: "deepseek-reasoner"
    editor_review_model: "deepseek-reasoner"
    translator_revision_model: "deepseek-reasoner"

  non_reasoning:
    initial_translation_model: "qwen-plus"
    editor_review_model: "qwen-plus"
    translator_revision_model: "qwen-plus"

  hybrid:
    initial_translation_model: "qwen-plus"
    editor_review_model: "deepseek-reasoner"
    translator_revision_model: "qwen-plus"
```

## Usage

```bash
# Use specific workflow mode
vpsweb translate -i poem.txt -s English -t Chinese -w hybrid
vpsweb translate -i poem.txt -s English -t Chinese -w reasoning
vpsweb translate -i poem.txt -s English -t Chinese -w non_reasoning
```

## Performance Comparison

| Mode | Quality | Cost | Speed | Best For |
|------|---------|------|-------|-----------|
| Reasoning | Highest | Highest | Slowest | Premium translations |
| Non-Reasoning | Good | Lowest | Fastest | Quick drafts |
| Hybrid | High | Medium | Medium | Daily use (recommended) |

## Custom Mode Creation

You can create custom workflow modes by:
1. Defining new mode configuration in `config/default.yaml`
2. Specifying which models to use for each workflow step
3. Setting appropriate parameters for each model
4. Testing the mode with sample translations

## Implementation Details

The workflow mode system is implemented in:
- `src/vpsweb/core/workflow.py` - Main workflow orchestration
- `src/vpsweb/models/config.py` - Configuration models
- `src/vpsweb/services/llm/` - LLM provider implementations

The system automatically selects the appropriate model and parameters for each workflow step based on the configured mode.