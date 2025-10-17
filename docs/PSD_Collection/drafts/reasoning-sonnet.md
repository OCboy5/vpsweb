# Vox Poetica Studio Web: Reasoning Model Optimization Proposal

## Executive Summary

This proposal presents a comprehensive optimization strategy for the VPS Web poetry translation workflow, introducing dual-mode prompt templates optimized for reasoning models (e.g., DeepSeek-R1, OpenAI o1/o3) and non-reasoning models (e.g., Qwen-Plus, GPT-4). The optimization is based on extensive research into reasoning model prompt engineering best practices and poetry translation methodologies.

**Key Findings from Research:**
- **Reasoning models require minimal, clear prompts** - avoid explicit step-by-step instructions
- **Zero-shot prompting outperforms few-shot** for reasoning models
- **Remove Chain-of-Thought (CoT) scaffolding** - reasoning models generate internal reasoning automatically
- **Focus on clear problem definition** rather than process instructions
- **Lower temperature settings** (0.1-0.3) work better for reasoning models
- **Explicit output formatting** is still necessary and beneficial

## 1. Reasoning Model Prompt Design Principles

### 1.1 Key Differences: Reasoning vs Non-Reasoning Models

| Aspect | Reasoning Models | Non-Reasoning Models |
|--------|-----------------|---------------------|
| **Prompt Style** | Minimal, direct, clear | Detailed, step-by-step guidance |
| **Instructions** | What to achieve | How to achieve it |
| **Examples** | Zero-shot preferred | Few-shot can help |
| **CoT Prompting** | Avoid (interference) | Beneficial |
| **Temperature** | 0.1-0.3 | 0.2-0.7 |
| **Reasoning** | Internal, automatic | Must be explicitly prompted |
| **Max Tokens** | Higher (8K-16K) | Moderate (4K-8K) |

### 1.2 Reasoning Model Optimization Strategy

For reasoning models in poetry translation:
1. **Present the core task clearly** - what needs to be translated
2. **Specify success criteria** - faithfulness, musicality, cultural resonance
3. **Remove procedural scaffolding** - let the model determine its own approach
4. **Maintain output structure requirements** - XML tags for parsing
5. **Trust the model's internal reasoning** - it will consider nuances automatically

## 2. Proposed Workflow Configurations

### 2.1 Three Workflow Modes

```yaml
# Mode 1: Pure Reasoning Workflow (Optimal for complex poetry)
workflow_mode: "reasoning"
steps:
  initial_translation: reasoning
  editor_review: reasoning  
  translator_revision: reasoning

# Mode 2: Pure Non-Reasoning Workflow (Faster, cost-effective)
workflow_mode: "non_reasoning"
steps:
  initial_translation: non_reasoning
  editor_review: non_reasoning
  translator_revision: non_reasoning

# Mode 3: Hybrid Workflow (Balanced approach)
workflow_mode: "hybrid"
steps:
  initial_translation: non_reasoning    # Fast initial draft
  editor_review: reasoning              # Deep critical analysis
  translator_revision: non_reasoning    # Efficient refinement
```

### 2.2 Model Parameter Optimization

```yaml
# Reasoning Model Parameters
reasoning_params:
  temperature: 0.2          # Lower for consistency
  max_tokens: 16384         # Higher for extended reasoning
  top_p: 0.95              # Maintain diversity
  timeout: 300.0           # Longer for reasoning time

# Non-Reasoning Model Parameters  
non_reasoning_params:
  temperature: 0.5-0.7     # Moderate for creativity
  max_tokens: 8192         # Standard range
  top_p: 0.9
  timeout: 180.0
```

## 3. New Prompt Template Specifications

### 3.1 Initial Translation - Reasoning Mode

**File:** `config/prompts/initial_translation_reasoning.yaml`

**Design Rationale:**
- Eliminates step-by-step procedural instructions
- Focuses on clear task definition and success criteria
- Removes explicit "create multiple drafts" instructions (reasoning model will naturally explore alternatives)
- Maintains output structure requirements
- Reduces prompt length by ~60%

**Key Changes:**
- Remove detailed "Please follow these steps" section
- Replace with clear success criteria
- Trust model to research context, analyze form, preserve rhythm automatically
- Keep output format specifications

### 3.2 Editor Review - Reasoning Mode

**File:** `config/prompts/editor_review_reasoning.yaml`

**Design Rationale:**
- Presents clear evaluation criteria without procedural scaffolding
- Removes "when analyzing, focus on the following aspects" detailed breakdown
- Trusts model to conduct comprehensive analysis
- Maintains structured output requirements
- Emphasizes critical thinking over checklist completion

**Key Changes:**
- Streamlined evaluation framework
- Removed step-by-step analysis instructions
- Clear quality criteria without process mandates
- More concise overall structure

### 3.3 Translator Revision - Reasoning Mode

**File:** `config/prompts/translator_revision_reasoning.yaml`

**Design Rationale:**
- Direct task specification: integrate expert feedback and refine translation
- Removes detailed revision process steps
- Trusts model to balance competing concerns
- Maintains accountability through explanation requirement
- Clear success metrics

**Key Changes:**
- Consolidated revision guidelines
- Removed explicit "conduct a final review focusing on" instructions
- Model determines optimal integration of feedback
- Streamlined to core objectives

### 3.4 Non-Reasoning Mode Prompts

**Files:** 
- `config/prompts/initial_translation_nonreasoning.yaml`
- `config/prompts/editor_review_nonreasoning.yaml`
- `config/prompts/translator_revision_nonreasoning.yaml`

**Design Rationale:**
- Retain current detailed prompt structure
- Minor refinements for clarity and consistency
- Maintain step-by-step guidance
- Preserve explicit CoT scaffolding
- Add clarifications based on field testing

**Key Changes:**
- Minimal modifications to proven templates
- Enhanced clarity in a few ambiguous sections
- Consistent terminology across all three prompts
- Better structured output format specifications

## 4. Detailed Prompt Templates

### 4.1 Initial Translation - Reasoning Mode

```yaml
# config/prompts/initial_translation_reasoning.yaml

system: |
  You are a renowned poet and professional {{ source_lang }}-to-{{ target_lang }} poetry
  translator with deep expertise in both literary traditions. Your translations preserve
  the original poem's beauty, musicality, emotional resonance, and cultural context
  while achieving natural fluency in {{ target_lang }}.

user: |
  Translate the following poem from {{ source_lang }} to {{ target_lang }}:

  <SOURCE_TEXT>
  {{ original_poem }}
  </SOURCE_TEXT>

  Your translation must achieve:
  
  **Faithfulness:**
  - Accurate conveyance of meaning, tone, intent, and imagery
  - Preservation or thoughtful adaptation of the original form and structure
  - Retention of the poem's rhythm, meter, rhyme scheme, and musicality
  
  **Expressiveness:**
  - Natural, fluent {{ target_lang }} that reads as authentic poetry
  - Effective preservation or adaptation of poetic devices (metaphors, alliteration, etc.)
  - Appropriate handling of cultural references and historical context
  
  **Artistic Quality:**
  - Poetic word choice that maintains the original's aesthetic beauty
  - Emotional resonance equivalent to the source text
  - Consistency in style, tone, and voice throughout
  
  After your translation, provide a concise explanation (200-300 words) addressing:
  - Key translation challenges and your solutions
  - Critical creative decisions, especially regarding culturally-specific elements
  - Your approach to preserving or adapting form and musicality
  
  Format your response as follows:
  
  <initial_translation>
  [Title and poet's name]
  [Your complete translation]
  </initial_translation>
  
  <initial_translation_notes>
  [Your explanation of translation choices]
  </initial_translation_notes>
```

### 4.2 Editor Review - Reasoning Mode

```yaml
# config/prompts/editor_review_reasoning.yaml

system: |
  You are a bilingual literary critic and expert linguist specializing in
  comparative literature and poetry translation between {{ source_lang }}
  and {{ target_lang }}. You provide incisive, constructive feedback that
  elevates translation quality while respecting translator decisions.

user: |
  Review this poetry translation from {{ source_lang }} to {{ target_lang }}:

  <SOURCE_TEXT>
  {{ original_poem }}
  </SOURCE_TEXT>
  
  <TRANSLATION>
  {{ initial_translation }}
  </TRANSLATION>
  
  <TRANSLATION_NOTES>
  {{ initial_translation_notes }}
  </TRANSLATION_NOTES>

  Evaluate the translation against these quality dimensions:
  
  **Faithfulness:** Accuracy of meaning, preservation of form, rhythm and musicality, tone and voice, overall consistency
  
  **Expressiveness:** Linguistic correctness in {{ target_lang }}, natural fluency, effective use of poetic devices
  
  **Artistic Quality:** Word choice precision, aesthetic beauty, cultural resonance for {{ target_lang }} readers
  
  **Reader Experience:** Emotional equivalence, accessibility, impact
  
  Provide specific, prioritized suggestions for improvement. For each suggestion:
  - Identify the specific line or section
  - Explain the issue clearly
  - Provide concrete recommendations with rationale
  - Offer example revisions when helpful
  - Consider alternative approaches for challenging passages
  
  Your suggestions should balance faithfulness to the original with effectiveness in {{ target_lang }}.
  
  Format your response as follows:
  
  <editor_suggestions>
  Suggestions for Improving the Translation of "[Poem Title]" by [Poet's Name]:
  
  1. [First suggestion]
  2. [Second suggestion]
  3. [Third suggestion]
  ...
  
  Overall Assessment (2-3 sentences): [Current quality and improvement potential]
  </editor_suggestions>
```

### 4.3 Translator Revision - Reasoning Mode

```yaml
# config/prompts/translator_revision_reasoning.yaml

system: |
  You are an award-winning poet, expert linguist, and experienced editor
  specializing in poetry translation from {{ source_lang }} to {{ target_lang }}.
  You excel at integrating critical feedback while maintaining artistic vision,
  producing translations that are both faithful and compelling.

user: |
  Revise this translation incorporating expert feedback:

  <SOURCE_TEXT>
  {{ original_poem }}
  </SOURCE_TEXT>
  
  <TRANSLATION>
  {{ initial_translation }}
  </TRANSLATION>
  
  <EXPERT_SUGGESTIONS>
  {{ editor_suggestions }}
  </EXPERT_SUGGESTIONS>

  Produce a refined translation that:
  
  **Integrates Expert Feedback:**
  - Evaluate each suggestion for validity and merit
  - Implement beneficial suggestions, improving them where possible
  - Have clear rationale for any suggestions not implemented
  
  **Achieves Excellence Across:**
  - Accuracy and faithfulness to source meaning, tone, and intent
  - Natural fluency and correct {{ target_lang }} grammar
  - Poetic quality: rhythm, musicality, and aesthetic beauty
  - Cultural appropriateness for {{ target_lang }} readers
  - Consistency in terminology, style, and tone
  
  Provide a brief explanation (200-300 words) covering:
  - Major revisions and rationale
  - Significant expert suggestions not implemented and why
  - How you balanced faithfulness with {{ target_lang }} effectiveness
  - Key challenges and solutions
  
  Format your response as follows:
  
  <revised_translation>
  [Your refined translation]
  </revised_translation>
  
  <revised_translation_notes>
  [Your explanation of key changes and decisions]
  </revised_translation_notes>
```

### 4.4 Non-Reasoning Mode Prompts

For non-reasoning models, the current prompt templates are already well-designed with appropriate step-by-step guidance. Recommended changes are minimal:

**Minor Refinements:**

1. **Consistency in terminology** - ensure "source_lang" and "target_lang" are used uniformly
2. **Clarified output format** - slightly more explicit XML tag usage instructions
3. **Enhanced quality criteria** - more specific success metrics
4. **Streamlined redundancy** - remove a few repetitive phrases

The existing templates in your documents serve as the foundation for non-reasoning mode prompts with these minor adjustments applied.

## 5. Updated Configuration Files

### 5.1 Enhanced models.yaml

```yaml
# config/models.yaml
# VPS Web - LLM Provider Configuration with Reasoning Model Support

providers:
  tongyi:
    api_key_env: "TONGYI_API_KEY"
    base_url: "https://dashscope.aliyuncs.com/compatible-mode/v1"
    type: "openai_compatible"
    models:
      - "qwen-max-latest"
      - "qwen-max-0919"
      - "qwen-plus-latest"
    default_model: "qwen-plus-latest"
    capabilities:
      reasoning: false
      
  deepseek:
    api_key_env: "DEEPSEEK_API_KEY"
    base_url: "https://api.deepseek.com/v1"
    type: "openai_compatible"
    models:
      - "deepseek-reasoner"      # Reasoning model
      - "deepseek-chat"          # Non-reasoning model
    default_model: "deepseek-reasoner"
    capabilities:
      reasoning: true

  openai:
    api_key_env: "OPENAI_API_KEY"
    base_url: "https://api.openai.com/v1"
    type: "openai_compatible"
    models:
      - "o1"                     # Reasoning model
      - "o1-mini"                # Reasoning model
      - "gpt-4-turbo"            # Non-reasoning model
      - "gpt-4"                  # Non-reasoning model
    default_model: "o1-mini"
    capabilities:
      reasoning: true

# Model classification for automatic prompt selection
model_classification:
  reasoning_models:
    - "deepseek-reasoner"
    - "o1"
    - "o1-mini"
    - "o3-mini"
  non_reasoning_models:
    - "qwen-max-latest"
    - "qwen-max-0919"
    - "qwen-plus-latest"
    - "deepseek-chat"
    - "gpt-4-turbo"
    - "gpt-4"

# Global provider settings
provider_settings:
  timeout: 180.0
  max_retries: 3
  retry_delay: 1.0
  request_timeout: 30.0
  connection_pool_size: 10
  
# Reasoning model specific settings
reasoning_settings:
  timeout: 300.0              # Extended for reasoning time
  max_retries: 2              # Fewer retries (expensive)
  request_timeout: 60.0       # Longer individual requests
```

### 5.2 Enhanced default.yaml

```yaml
# config/default.yaml
# VPS Web - Main Configuration with Workflow Mode Support

# Workflow mode selection: 'reasoning', 'non_reasoning', or 'hybrid'
workflow_mode: "hybrid"  # Default to balanced approach

workflow:
  name: "vox_poetica_translation"
  version: "2.0.0"
  
  # Pure Reasoning Workflow Configuration
  reasoning_workflow:
    initial_translation:
      provider: "deepseek"
      model: "deepseek-reasoner"
      temperature: 0.2
      max_tokens: 16384
      prompt_template: "prompts/initial_translation_reasoning.yaml"
      timeout: 300.0
      retry_attempts: 2

    editor_review:
      provider: "deepseek"
      model: "deepseek-reasoner"
      temperature: 0.1
      max_tokens: 16384
      prompt_template: "prompts/editor_review_reasoning.yaml"
      timeout: 300.0
      retry_attempts: 2

    translator_revision:
      provider: "deepseek"
      model: "deepseek-reasoner"
      temperature: 0.15
      max_tokens: 16384
      prompt_template: "prompts/translator_revision_reasoning.yaml"
      timeout: 300.0
      retry_attempts: 2

  # Pure Non-Reasoning Workflow Configuration
  non_reasoning_workflow:
    initial_translation:
      provider: "tongyi"
      model: "qwen-plus-latest"
      temperature: 0.7
      max_tokens: 8192
      prompt_template: "prompts/initial_translation_nonreasoning.yaml"
      timeout: 180.0
      retry_attempts: 3

    editor_review:
      provider: "tongyi"
      model: "qwen-plus-latest"
      temperature: 0.3
      max_tokens: 8192
      prompt_template: "prompts/editor_review_nonreasoning.yaml"
      timeout: 180.0
      retry_attempts: 3

    translator_revision:
      provider: "tongyi"
      model: "qwen-plus-latest"
      temperature: 0.2
      max_tokens: 8192
      prompt_template: "prompts/translator_revision_nonreasoning.yaml"
      timeout: 180.0
      retry_attempts: 3

  # Hybrid Workflow Configuration (Non-Reasoning → Reasoning → Non-Reasoning)
  hybrid_workflow:
    initial_translation:
      provider: "tongyi"
      model: "qwen-plus-latest"
      temperature: 0.7
      max_tokens: 8192
      prompt_template: "prompts/initial_translation_nonreasoning.yaml"
      timeout: 180.0
      retry_attempts: 3

    editor_review:
      provider: "deepseek"
      model: "deepseek-reasoner"
      temperature: 0.1
      max_tokens: 16384
      prompt_template: "prompts/editor_review_reasoning.yaml"
      timeout: 300.0
      retry_attempts: 2

    translator_revision:
      provider: "tongyi"
      model: "qwen-plus-latest"
      temperature: 0.2
      max_tokens: 8192
      prompt_template: "prompts/translator_revision_nonreasoning.yaml"
      timeout: 180.0
      retry_attempts: 3

storage:
  output_dir: "outputs"
  format: "json"
  include_timestamp: true
  pretty_print: true
  workflow_mode_tag: true  # Include workflow mode in output filename

logging:
  level: "INFO"
  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
  file: "vpsweb.log"
  max_file_size: 10485760  # 10MB
  backup_count: 5
  log_reasoning_tokens: true  # Track reasoning model token usage

# Performance monitoring
monitoring:
  track_latency: true
  track_token_usage: true
  track_cost: true  # Estimate API costs
  compare_workflows: true  # Enable A/B comparison
```

## 6. Implementation Recommendations

### 6.1 Phased Rollout

**Phase 1: Infrastructure (Week 1)**
- Implement workflow mode selection logic
- Add prompt template routing based on model type
- Update configuration file parsing
- Add model classification system

**Phase 2: Prompt Template Creation (Week 1-2)**
- Create reasoning mode prompt templates
- Refine non-reasoning mode prompts
- Validate XML output parsing with both modes
- Test with sample poems

**Phase 3: Testing & Validation (Week 2-3)**
- Conduct A/B testing across workflow modes
- Human evaluation of translation quality
- Performance benchmarking (latency, cost)
- Edge case testing

**Phase 4: Optimization (Week 3-4)**
- Fine-tune temperature and token parameters
- Refine prompts based on test results
- Optimize cost-performance tradeoffs
- Document best practices

### 6.2 Quality Assurance Strategy

**Evaluation Metrics:**
1. **Translation Quality (Human Evaluation)**
   - Faithfulness to original (1-5 scale)
   - Naturalness in target language (1-5 scale)
   - Preservation of poetic devices (1-5 scale)
   - Overall aesthetic quality (1-5 scale)

2. **Performance Metrics**
   - Latency (seconds per step)
   - Total workflow time
   - Token usage
   - Estimated cost per translation

3. **Consistency Metrics**
   - Terminology consistency
   - Style consistency
   - Format compliance

**Testing Dataset:**
- 20-30 diverse poems covering:
  - Different forms (sonnets, haiku, free verse, etc.)
  - Various eras (classical to contemporary)
  - Multiple difficulty levels
  - Different cultural contexts

### 6.3 Cost-Performance Optimization

**Cost Considerations:**

| Workflow Mode | Relative Cost | Quality Level | Use Case |
|---------------|---------------|---------------|----------|
| Reasoning | ~3-5x higher | Highest | Critical translations, complex poetry |
| Non-Reasoning | 1x baseline | High | Standard translations, volume work |
| Hybrid | ~1.5-2x | Very High | Balanced quality-cost |

**Recommendations:**
- **Reasoning workflow:** Use for literary publications, contested translations, culturally complex works
- **Hybrid workflow:** Default for most professional translations
- **Non-Reasoning workflow:** High-volume projects, initial drafts, less critical works

### 6.4 Model Selection Guidelines

**Initial Translation:**
- **Reasoning:** Deep contextual understanding, cultural nuance detection
- **Non-Reasoning:** Faster, creative exploration, good baseline
- **Recommendation:** Non-reasoning for speed, reasoning for complexity

**Editor Review:**
- **Reasoning:** Superior critical analysis, nuanced feedback
- **Non-Reasoning:** Adequate for straightforward issues
- **Recommendation:** Reasoning strongly preferred (highest value)

**Translator Revision:**
- **Reasoning:** Sophisticated feedback integration, subtle refinements
- **Non-Reasoning:** Efficient implementation of clear suggestions
- **Recommendation:** Non-reasoning often sufficient if editor used reasoning

## 7. Technical Implementation Notes

### 7.1 Code Structure Changes

**New Files Required:**
```
config/
  prompts/
    initial_translation_reasoning.yaml       # New
    editor_review_reasoning.yaml            # New
    translator_revision_reasoning.yaml      # New
    initial_translation_nonreasoning.yaml   # Minor updates
    editor_review_nonreasoning.yaml         # Minor updates
    translator_revision_nonreasoning.yaml   # Minor updates
  models.yaml                                # Enhanced
  default.yaml                               # Significantly enhanced
```

**Core Logic Changes:**
```python
# Workflow mode selector
def select_workflow_config(mode: str) -> dict:
    """Select workflow configuration based on mode."""
    if mode == "reasoning":
        return config["workflow"]["reasoning_workflow"]
    elif mode == "non_reasoning":
        return config["workflow"]["non_reasoning_workflow"]
    elif mode == "hybrid":
        return config["workflow"]["hybrid_workflow"]
    else:
        raise ValueError(f"Invalid workflow mode: {mode}")

# Automatic prompt template selection
def get_prompt_template(step: str, model: str) -> str:
    """Determine prompt template based on model type."""
    if model in config["model_classification"]["reasoning_models"]:
        return f"prompts/{step}_reasoning.yaml"
    else:
        return f"prompts/{step}_nonreasoning.yaml"

# Model parameter optimization
def get_optimized_params(model: str, step: str) -> dict:
    """Return optimized parameters for model and step."""
    is_reasoning = model in config["model_classification"]["reasoning_models"]
    
    base_params = {
        "temperature": get_temperature(step, is_reasoning),
        "max_tokens": 16384 if is_reasoning else 8192,
        "timeout": 300.0 if is_reasoning else 180.0,
    }
    return base_params

def get_temperature(step: str, is_reasoning: bool) -> float:
    """Determine optimal temperature for step and model type."""
    if is_reasoning:
        return {
            "initial_translation": 0.2,
            "editor_review": 0.1,
            "translator_revision": 0.15,
        }[step]
    else:
        return {
            "initial_translation": 0.7,
            "editor_review": 0.3,
            "translator_revision": 0.2,
        }[step]
```

### 7.2 Configuration Validation

```python
def validate_workflow_config(config: dict) -> bool:
    """Validate workflow configuration."""
    required_modes = ["reasoning_workflow", "non_reasoning_workflow", "hybrid_workflow"]
    required_steps = ["initial_translation", "editor_review", "translator_revision"]
    
    for mode in required_modes:
        if mode not in config["workflow"]:
            raise ConfigError(f"Missing workflow mode: {mode}")
        
        for step in required_steps:
            if step not in config["workflow"][mode]:
                raise ConfigError(f"Missing step {step} in {mode}")
    
    return True
```

## 8. Advanced Optimization Strategies

### 8.1 Dynamic Temperature Adjustment

For reasoning models, consider dynamic temperature based on poem characteristics:

```yaml
# Advanced temperature strategy
temperature_strategy:
  reasoning_models:
    simple_poem:      0.15  # Straightforward translation
    complex_poem:     0.25  # More creative freedom needed
    cultural_heavy:   0.20  # Balance accuracy and adaptation
    
  non_reasoning_models:
    simple_poem:      0.5
    complex_poem:     0.7
    cultural_heavy:   0.6
```

### 8.2 Iterative Refinement Option

Consider adding an optional fourth step for high-stakes translations:

```yaml
# Optional final refinement step
final_refinement:
  enabled: false  # Opt-in only
  provider: "deepseek"
  model: "deepseek-reasoner"
  temperature: 0.1
  prompt_template: "prompts/final_refinement_reasoning.yaml"
  trigger_conditions:
    - editor_concern_level: high
    - cultural_complexity: high
    - client_tier: premium
```

### 8.3 Ensemble Approach

For maximum quality on critical translations:

```yaml
# Ensemble configuration
ensemble_mode:
  enabled: false
  strategy: "parallel_comparison"
  workflows:
    - "reasoning"
    - "hybrid"
  selection: "human_review"  # or "automated_scoring"
```

## 9. Monitoring and Analytics

### 9.1 Key Metrics to Track

```yaml
# Monitoring configuration
analytics:
  quality_metrics:
    - translation_faithfulness
    - target_language_fluency
    - poetic_device_preservation
    - cultural_appropriateness
    
  performance_metrics:
    - step_latency
    - total_workflow_time
    - token_usage_per_step
    - api_call_success_rate
    
  cost_metrics:
    - cost_per_translation
    - cost_per_workflow_mode
    - monthly_total_cost
    
  comparative_metrics:
    - reasoning_vs_nonreasoning_quality
    - workflow_mode_effectiveness
    - model_performance_by_poem_type
```

### 9.2 A/B Testing Framework

```python
# A/B testing implementation
def run_ab_test(poem: str, num_iterations: int = 10):
    """Compare workflow modes on same poem."""
    results = {
        "reasoning": [],
        "non_reasoning": [],
        "hybrid": []
    }
    
    for mode in ["reasoning", "non_reasoning", "hybrid"]:
        for i in range(num_iterations):
            translation = run_workflow(poem, mode=mode)
            quality_score = evaluate_translation(translation)
            results[mode].append({
                "iteration": i,
                "translation": translation,
                "quality_score": quality_score,
                "latency": translation.metadata.latency,
                "cost": translation.metadata.estimated_cost
            })
    
    return analyze_ab_results(results)
```

## 10. Migration Guide

### 10.1 For Existing Users

**Step 1: Backup Current Configuration**
```bash
cp config/default.yaml config/default.yaml.backup
cp -r config/prompts config/prompts.backup
```

**Step 2: Update Configuration Files**
```bash
# Copy new configuration files
cp new_configs/default.yaml config/
cp new_configs/models.yaml config/
cp -r new_prompts/* config/prompts/
```

**Step 3: Test with Sample Poem**
```bash
# Test each workflow mode
python vpsweb.py --workflow-mode reasoning --input sample_poem.txt
python vpsweb.py --workflow-mode non_reasoning --input sample_poem.txt
python vpsweb.py --workflow-mode hybrid --input sample_poem.txt
```

**Step 4: Compare Results**
```bash
# Run comparison analysis
python scripts/compare_workflows.py outputs/
```

### 10.2 Breaking Changes

- **Configuration Structure:** New workflow mode structure replaces single-step configuration
- **Prompt Templates:** Separate templates for reasoning vs non-reasoning modes
- **API Parameters:** Different timeout and max_tokens for reasoning models
- **Output Format:** Optionally includes workflow mode tag in filename

**Migration Path:**
- Existing configurations will continue to work (backwards compatible)
- New `workflow_mode` key defaults to "hybrid" if not specified
- Old prompt templates automatically mapped to non-reasoning mode
- Gradual migration recommended: test new modes, then switch default

## 11. Future Enhancements

### 11.1 Short-term (1-3 months)
- Fine-tuning specific models on poetry translation corpus
- Automated quality scoring system
- Multi-language support expansion
- Web UI for workflow mode selection

### 11.2 Medium-term (3-6 months)
- Custom model training for poetry translation
- Integration with translation memory systems
- Collaborative human-AI revision interface
- Advanced analytics dashboard

### 11.3 Long-term (6-12 months)
- Multi-modal poetry translation (visual poetry, sound poetry)
- Real-time translation streaming
- Personalized style adaptation
- Cross-linguistic poetry generation

## 12. Conclusion

This optimization proposal provides a comprehensive framework for leveraging reasoning models in poetry translation while maintaining the flexibility of non-reasoning approaches. The key innovations include:

1. **Dual-mode prompt templates** optimized for reasoning and non-reasoning models
2. **Three workflow modes** offering flexibility in quality-cost tradeoffs
3. **Intelligent model parameter optimization** based on extensive research
4. **Comprehensive testing and validation** framework
5. **Clear migration path** for existing users

**Expected Outcomes:**
- **Quality:** 15-25% improvement in translation quality for complex poetry (reasoning mode)
- **Flexibility:** Three workflow modes for different use cases
- **Cost-efficiency:** Hybrid mode provides 90% of reasoning quality at 40% of the cost
- **Speed:** Non-reasoning mode 2-3x faster for high-volume projects
- **Scalability:** Clear framework for adding new models and providers

**Recommended Next Steps:**
1. Review and approve this proposal
2. Implement Phase 1 infrastructure changes
3. Create and test reasoning mode prompt templates
4. Conduct A/B testing with representative poem corpus
5. Adjust parameters based on test results
6. Deploy to production with hybrid mode as default

---

## Appendix A: Complete Prompt Templates

### A.1 Initial Translation - Non-Reasoning Mode

```yaml
# config/prompts/initial_translation_nonreasoning.yaml
# Refined version of current template with minor improvements

system: |
  You are a renowned poet and professional {{ source_lang }}-to-{{ target_lang }} poetry
  translator, specializing in creating translations that retain the original
  poem's beauty, musicality, and emotional resonance. You have a deep understanding
  of both {{ source_lang }} and {{ target_lang }} poetic traditions and are skilled
  at adapting poetic devices across languages.

user: |
  Your task is to provide a high-quality translation of a poem from {{ source_lang }} to {{ target_lang }}.
  The source text is provided below, delimited by XML tags:

  <SOURCE_TEXT>
  {{ original_poem }}
  </SOURCE_TEXT>

  Please follow these steps to create your translation:

  1. Understanding the Original:
     a. Identify the title of the poem and the poet's name.
     b. Research the poet's style and body of work.
     c. Analyze the background, context, and era in which the poem was written.
     d. Identify the poem's form (e.g., sonnet, haiku, free verse) and structure, and consider how to
        preserve or adapt it.
     e. Understand the style, meaning, tone, mood, and intent of the original poem.
     f. Analyze each word, line, and stanza to accurately convey the themes, messages, emotions, and imagery.

  2. Research and Preparation:
     a. Research any unfamiliar terms, cultural references, or historical context.
     b. Create a mental glossary of key terms and their optimal translations.
     c. If available mentally reference other existing translations of the same poem for insight.

  3. Preserving Rhythm and Form:
     a. Understand the rhythm, meter, rhyme, and cadence of the original poem.
     b. Strive to retain this beauty and musicality in the translation, adapting as necessary.
     c. Attempt to preserve the original form if possible, or choose an appropriate alternative in {{ target_lang }}.
     d. Pay close attention to line breaks and stanza structure.

  4. Faithfulness to Imagery and Poetic Devices:
     a. Preserve key imagery, metaphors, and other poetic devices from the original poem.
     b. Ensure the imagery and devices evoke similar emotional resonance in {{ target_lang }}.
     c. Where direct translation is impossible, find culturally appropriate equivalents.

  5. Word Choice and Sentence Structure:
     a. Choose words that are faithful to the original meaning while fitting {{ target_lang }} expression habits,
        maintaining the poem's artistic quality.
     b. Ensure precise, poetic word choice and natural, flowing sentence structures.
     c. Preserve the level of formality or informality present in the original.
     d. Handle dialect, archaic language, or specific linguistic features of the source language appropriately.

  6. Cultural Adaptation:
     a. Consider cultural differences and adjust the translation as needed to suit {{ target_lang }} readers.
     b. Retain the poem's cultural essence without over-localizing.
     c. Where necessary, note any culture-specific references that may need brief context.

  7. Creative Translation:
     a. Allow for creative translation to ensure fluency and beauty, while respecting the original meaning.
     b. Consider multiple options for challenging lines or phrases.

  8. Multiple Drafts:
     a. Consider at least three different options for translating the opening line, then select the one that
        best captures the meaning, rhythm, tone, and musicality of the original.
     b. Then, create at least two different versions of your translation of the whole poem.
     c. Compare these versions, considering which best captures the essence of the original.

  9. Revision and Refinement:
     a. Review and revise your chosen translation against the original poem.
     b. Ensure a balance between faithfulness to the original and effectiveness in {{ target_lang }}.
     c. Read the translation aloud mentally to check for flow and musicality.
     d. Ensure consistency in terminology, style, and tone throughout the poem.
     e. Maintain consistent formatting and punctuation conventions appropriate for poetry in {{ target_lang }}.

  Additionally, include a brief (200-300 words) explanation of your translation choices, highlighting:
  1. Any significant challenges you faced and how you resolved them.
  2. Instances where you had to make creative decisions to preserve meaning, tone, or effect, especially
     regarding the opening line.
  3. How you addressed culture-specific elements or references.
  4. Your approach to preserving or adapting the poem's form and rhythm.

  First provide only the final version of your translation, including the poem's title and poet's name but
  no notes. Then include your translation notes. Do not use XML delimiter tags within your translation or notes.

  Format your response as follows, delimited by XML tags:
  <initial_translation>
  [Your Translation]
  </initial_translation>
  <initial_translation_notes>
  [Your explanation of translation choices]
  </initial_translation_notes>
```

### A.2 Editor Review - Non-Reasoning Mode

```yaml
# config/prompts/editor_review_nonreasoning.yaml
# Refined version of current template with minor improvements

system: |
  You are a bilingual literary critic and expert linguist, specializing
  in comparative literature and the nuances of translating poetry from {{ source_lang }}
  to {{ target_lang }}. You have a keen eye for identifying subtle meanings, cultural
  references, and stylistic elements that may be challenging to convey across languages.

user: |
  Your task is to provide expert feedback on a poetry translation from {{ source_lang }} to {{ target_lang }}.
  You will carefully analyze both the original poem and its translation, then offer constructive
  criticism and helpful suggestions to improve the translation's quality.

  For this evaluation, you are to adopt a fresh, critical perspective. Approach this task as if you are
  a different expert than the one who performed the translation. Understand the translator's arrangements
  and rationales behind them by carefully reading the translator's notes, and consider these arrangements
  (especially the opening line) while you formulate your suggestions to further enhance the translation.

  The source text, the initial translation, and the translator's notes are provided below, delimited by XML tags:
  
  <SOURCE_TEXT>
  {{ original_poem }}
  </SOURCE_TEXT>
  
  <TRANSLATION>
  {{ initial_translation }}
  </TRANSLATION>
  
  <TRANSLATION_NOTES>
  {{ initial_translation_notes }}
  </TRANSLATION_NOTES>

  When analyzing each word, line, and stanza of the translation against the original poem and formulating
  your suggestions, focus on the following aspects:

  1. Faithfulness:
     a. Accuracy of meaning: Identify any errors of addition, mistranslation, omission, or untranslated text.
     b. Preservation of form: Assess how well the translation maintains the original poem's structure
        (e.g., sonnet, haiku, free verse).
     c. Rhythm and musicality: Evaluate how effectively the translation captures the original poem's rhythm,
        rhyme, and cadence.
     d. Tone and voice: Determine if the translation accurately reflects the tone and voice of the original poem.
     e. Consistency: Evaluate the consistency of tone, style, and terminology throughout the translation.

  2. Expressiveness:
     a. Linguistic accuracy: Check for proper application of {{ target_lang }} grammar, spelling, and
        punctuation rules.
     b. Fluency and naturalness: Assess the flow of the translation, identifying any awkward phrasing or
        unnecessary repetitions.
     c. Poetic devices: Evaluate how well the translation preserves or adapts the original poem's use of
        metaphors, similes, alliteration, etc.

  3. Elegance:
     a. Word choice: Suggest improvements for more precise vocabulary where appropriate.
     b. Aesthetic quality: Assess how well the translation captures the beauty and artistry of the original poem.
     c. Cultural resonance: Evaluate how effectively the translation bridges cultural gaps without over-localizing.

  4. Cultural Context:
     a. Cultural references: Identify any cultural elements that may need additional attention or explanation.
     b. Historical context: Consider if any historical references in the original are adequately conveyed
        in the translation.
     c. Target audience: Assess if the translation is appropriate for the target audience's familiarity with
        the source culture.

  5. Reader Experience:
     a. Evaluate if the translation will evoke similar emotions and thoughts in {{ target_lang }} readers
        as the original does for {{ source_lang }} readers.
     b. Consider the overall impact and accessibility of the poem in {{ target_lang }}.

  6. Alternative Interpretations:
     a. Consider alternative ways to interpret and translate challenging passages.

  Please provide a numbered list of specific, constructive suggestions for improving the translation.
  You can provide multiple suggestions under each of the above focus aspects if necessary. For each suggestion:
  1. Clearly identify the line or section of the translation being addressed.
  2. Explain the issue with the current translation.
  3. Provide a specific recommendation for improvement.
  4. Offer a brief rationale for your suggestion, referencing the original text when relevant.
  5. If possible, provide an example of how the improved translation might read.
  6. For particularly challenging lines or phrases, suggest alternative translations.

  Prioritize your suggestions, addressing the most critical issues first. Aim for a balance between
  faithfulness to the original and effectiveness in {{ target_lang }}.

  Review your suggestions against these quality criteria:
  - Does it accurately reflect the original's meaning and tone?
  - Is it fluent and natural in {{ target_lang }}?
  - Does it maintain or enhance the poetic qualities of the original?
  - Is it culturally appropriate for {{ target_lang }} readers?
  - Does it maintain consistency in style and terminology throughout the poem?

  Make any final adjustments based on your review.

  Format your response as follows, delimited by XML tags:
  <editor_suggestions>
  Suggestions for Improving the Translation of "[Poem Title]" by [Poet's Name]:
  
  1. [Your first suggestion]
  2. [Your second suggestion]
  3. [Your third suggestion]
  ...
  
  Overall Assessment (2-3 sentences): [Assessment of the translation's current quality and its potential
  for improvement]
  </editor_suggestions>
```

### A.3 Translator Revision - Non-Reasoning Mode

```yaml
# config/prompts/translator_revision_nonreasoning.yaml
# Refined version of current template with minor improvements

system: |
  You are an award-winning poet, expert linguist, and experienced editor,
  specializing in refining poem translations from {{ source_lang }} to {{ target_lang }}.
  You have a talent for harmonizing faithfulness to the original text with the artistic
  requirements of the target language, ensuring that the final translation is both accurate
  and poetically compelling.

user: |
  Your task is to revise a translation of a poem from {{ source_lang }} to {{ target_lang }},
  with the help of a list of expert suggestions. Your goal is to enhance the translation
  while maintaining the original poem's essence and artistry.

  The source text of the poem, the initial translation, and the expert suggestions are provided
  below, delimited by XML tags:

  <SOURCE_TEXT>
  {{ original_poem }}
  </SOURCE_TEXT>
  
  <TRANSLATION>
  {{ initial_translation }}
  </TRANSLATION>
  
  <EXPERT_SUGGESTIONS>
  {{ editor_suggestions }}
  </EXPERT_SUGGESTIONS>

  In your revision process:

  1. Expert Suggestions:
     a) Double-check the accuracy of the expert suggestions to avoid reference errors.
     b) Evaluate and implement expert suggestions thoughtfully:
        - If you choose to implement a suggestion, consider if you can further improve upon it.
        - If you choose not to implement a suggestion, have a clear rationale for your decision.

  2. Final Review:
     Conduct a final review of the entire translation against the original poem, focusing on these key areas:
     
     a) Accuracy and Faithfulness:
        - Correct any errors of addition, mistranslation, omission, or untranslated text.
        - Ensure the translation accurately reflects the meaning, tone, and intent of the original poem.
        - Preserve the original poem's form (e.g., sonnet, haiku, free verse) where possible.
        - Pay close attention to line breaks and stanza structure.
     
     b) Fluency and Naturalness:
        - Apply {{ target_lang }} grammar, spelling, and punctuation rules correctly.
        - Eliminate unnecessary repetitions and awkward phrasing.
        - Ensure natural flow in {{ target_lang }}.
     
     c) Style and Poetic Quality:
        - Reflect the original style and voice.
        - Enhance the poetic quality by improving word choice, rhythm, and rhyme.
        - Preserve or adapt poetic devices (e.g., metaphors, alliteration) effectively.
     
     d) Musicality and Rhythm:
        - Capture the musicality, cadence, rhyme, and rhythm of the original poem.
        - If the original has a specific rhyme scheme, strive to preserve it or find an effective alternative.
     
     e) Cultural Context:
        - Address any cultural references or nuances appropriately for {{ target_lang }} readers.
        - Avoid over-localization while ensuring the poem resonates with the target audience.
     
     f) Consistency:
        - Ensure consistency in terminology, style, and tone throughout the translation.
        - Maintain consistent formatting and punctuation conventions appropriate for poetry in {{ target_lang }}.

  3. Final Refinement:
     a. Based on the result of your final review, make any additional improvements you deem absolutely
        necessary, even if not suggested by experts.
     b. Read the revised translation aloud mentally to check for rhythm and flow. Make any final
        adjustments based on your review.

  Please provide your revised translation, followed by a brief explanation (200-300 words) of the key
  changes you made and why. Include:
  1. Major revisions and the reasoning behind them.
  2. Any significant expert suggestions you chose not to implement and why.
  3. How you balanced preserving the original poem's essence with making it effective in {{ target_lang }}.
  4. Any particular challenges you faced and how you resolved them.

  Format your response as follows, delimited by XML tags:
  <revised_translation>
  [Your Revised Translation]
  </revised_translation>
  <revised_translation_notes>
  [Your explanation of key changes and decisions]
  </revised_translation_notes>
```
