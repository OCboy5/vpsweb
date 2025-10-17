# VPSWeb WeChat Integration - Revised Project Specification

**Version**: 0.3.0 (Revised)
**Date**: 2025-10-12
**Based on**: Author's approved PSD + LLM synthesis preference

## Executive Summary

This specification combines the author's approved scope with LLM-based translation notes synthesis to create a high-quality WeChat integration for VPSWeb. The focus is on simplicity, quality, and adherence to the author's specific design decisions.

## 1. Strategic Decisions & Scope

### 1.1 Author-Approved Scope (Fixed)
- **No cover image handling** (simplifies WeChat API integration)
- **Author name**: "施知韵VoxPoetica"
- **Digest length**: 80-120 characters
- **Slug format**: `poetname-poemtitle-YYYYMMDD`
- **Output structure**: `outputs/wechat_articles/{slug}/`

### 1.2 LLM Synthesis Enhancement (User Preference)
- **Translation notes generation** using LLM synthesis
- **Intelligent extraction** from all workflow sources
- **Quality-focused approach** over simple heuristics
- **Leveraging existing LLM infrastructure**

### 1.3 Combined Architecture Benefits
- **Simplified API integration** (no image handling)
- **High-quality content generation** (LLM synthesis)
- **Author's design preferences** (structure and naming)
- **Robust technical implementation** (error handling, testing)

## 2. Article Structure (Author-Approved)

```html
<section style="font-size: 16px; line-height: 1.8; color: #222;">
  <!-- Title Section -->
  <h1 style="font-size: 22px; margin: 12px 0;">【知韵译诗】{poem_title}（{poet_name}）</h1>
  <small style="color: #666;">作者：施知韵VoxPoeticaStudio</small>
  <hr>

  <!-- Original Poem -->
  <h2 style="font-size: 18px; margin: 16px 0 8px;">原诗</h2>
  <div style="font-family: serif; margin: 8px 0; white-space: pre-wrap;">{original_poem}</div>

  <!-- Translation -->
  <h2 style="font-size: 18px; margin: 16px 0 8px;">英译</h2>
  <div style="font-family: serif; margin: 8px 0; white-space: pre-wrap;">{final_translation}</div>

  <!-- Translation Notes (LLM Synthesized) -->
  <h2 style="font-size: 18px; margin: 16px 0 8px;">译注</h2>
  <ul style="margin: 4px 0;">
    {llm_generated_bullets}
  </ul>

  <!-- Copyright -->
  <hr>
  <small style="color: #666;">
    本译文与导读由【知韵译诗】施知韵VoxPoetica原创制作。未经授权，不得转载。若需引用，请注明出处。
  </small>
</section>
```

## 3. LLM Translation Notes Synthesis

### 3.1 Input Sources (Priority Order)
1. `revised_translation.revised_translation_notes`
2. `editor_review.editor_suggestions`
3. `initial_translation.initial_translation_notes`

### 3.2 LLM Synthesis Prompt
```python
TRANSLATION_NOTES_PROMPT = """
基于以下诗歌翻译工作流记录，生成3-6条面向诗歌爱好者的翻译札记要点：

【最终译注】
{revised_translation_notes}

【编辑建议】
{editor_suggestions}

【初译说明】
{initial_translation_notes}

要求：
- 目标读者：对诗歌翻译感兴趣的普通读者
- 每条要点18-40字，简洁明了
- 重点突出：关键词汇选择、意象处理、文化元素保留、韵律节奏调整
- 语言平实，避免学术术语
- 使用项目符号列表格式（• 要点内容）
- 生成digest摘要：80-120字，概括翻译特色和难点

请按以下格式输出：
digest: [80-120字摘要]
notes:
• 翻译要点1
• 翻译要点2
• 翻译要点3
...
"""
```

### 3.3 LLM Integration Strategy
- **Use existing LLM infrastructure** (tongyi/deepseek providers)
- **Hybrid approach**: reasoning model for synthesis, non-reasoning for refinement if needed
- **Quality validation**: Check length, content, and readability
- **Fallback mechanism**: Use heuristic extraction if LLM fails

## 4. CLI Commands (Author-Specified)

### 4.1 vpsweb generate-article
```bash
vpsweb generate-article --input-json PATH [--output-dir PATH] [--author STR] [--digest STR] [--dry-run]
```

**Implementation Details**:
- Parse JSON with congregation preference
- Extract metadata (poem_title, poet_name, series_index)
- Generate translation notes via LLM
- Create article HTML with author's template
- Generate slug: `poetname-poemtitle-YYYYMMDD`

### 4.2 vpsweb publish-article
```bash
vpsweb publish-article --article-html PATH [--author STR] [--digest STR] [--config PATH] [--dry-run]
```

**Implementation Details**:
- Load article metadata from JSON
- WeChat API integration (no image handling)
- Draft creation with simplified payload
- Result tracking and error handling

## 5. WeChat API Integration (Simplified)

### 5.1 Configuration (config/wechat.yaml)
```yaml
appid: "${WECHAT_APPID}"
secret: "${WECHAT_SECRET}"
base_url: "https://api.weixin.qq.com"
timeouts:
  connect: 5s
  read: 20s
retry:
  attempts: 3
  backoff: exponential
```

### 5.2 API Endpoints Used
- `GET /cgi-bin/token` - Access token
- `POST /cgi-bin/draft/add` - Create draft
- **No image endpoints** (simplified scope)

### 5.3 Draft Payload (Simplified)
```json
{
  "articles": [{
    "title": "【知韵译诗】诗歌名（诗人名）",
    "author": "施知韵VoxPoetica",
    "digest": "80-120字摘要",
    "content": "<section>HTML内容</section>",
    "content_source_url": ""
  }]
}
```

## 6. Data Models & Structure

### 6.1 Output Structure
```
outputs/wechat_articles/{slug}/
├── article.html           # WeChat-compatible HTML
├── metadata.json          # Article metadata
└── publish_result.json    # Publishing result (after publish)
```

### 6.2 Metadata Structure
```json
{
  "title": "【知韵译诗】诗歌名（诗人名）",
  "slug": "poetname-poemtitle-20251012",
  "author": "施知韵VoxPoetica",
  "digest": "80-120字摘要",
  "source_json_path": "path/to/translation.json",
  "created_at": "2025-10-12T19:05:01Z",
  "translation_notes": {
    "digest": "摘要内容",
    "bullets": ["• 要点1", "• 要点2", "• 要点3"]
  }
}
```

## 7. Implementation Strategy

### 7.1 Module Structure
```
src/vpsweb/
├── services/wechat/
│   ├── __init__.py
│   ├── client.py              # WeChat API client
│   └── token_manager.py       # Token management
├── utils/
│   ├── article_generator.py   # Article generation logic
│   └── notes_synthesizer.py   # LLM translation notes
├── models/
│   └── wechat.py              # WeChat data models
└── __main__.py                # CLI commands
```

### 7.2 Development Phases

**Phase 1: Article Generation (2-3 days)**
- Article generator with LLM synthesis
- Author-approved HTML template
- CLI generate-article command
- Basic testing

**Phase 2: WeChat Integration (2-3 days)**
- Simplified WeChat API client
- Token management
- CLI publish-article command
- Integration testing

**Phase 3: Polish & Documentation (1-2 days)**
- Error handling refinement
- Documentation updates
- Final testing
- Release preparation

## 8. Quality Assurance

### 8.1 Testing Strategy
**Unit Tests**:
- LLM notes synthesis quality
- Article HTML generation
- Metadata extraction
- Slug generation

**Integration Tests**:
- CLI command flows
- WeChat API (mocked)
- File I/O operations
- Error scenarios

**Manual Testing**:
- Real WeChat API integration
- Article formatting validation
- Draft folder verification

### 8.2 Success Criteria
- ✅ Generate professional WeChat articles
- ✅ High-quality LLM translation notes
- ✅ Successful draft publishing
- ✅ Author's exact specifications followed
- ✅ Robust error handling

## 9. Configuration & Security

### 9.1 Environment Variables
```bash
# .env
WECHAT_APPID=your_appid
WECHAT_SECRET=your_secret
```

### 9.2 Security Practices
- Credentials in environment variables
- Local token caching with permissions
- No secrets in repository
- Error message sanitization

## 10. Acceptance Criteria

### 10.1 Functional Requirements
- ✅ `generate-article` creates HTML + metadata with author's format
- ✅ LLM synthesis produces 3-6 high-quality translation notes
- ✅ `publish-article` creates WeChat draft successfully
- ✅ Digest length 80-120 characters
- ✅ Slug format `poetname-poemtitle-YYYYMMDD`

### 10.2 Quality Requirements
- ✅ Professional article formatting
- ✅ Intelligent translation notes
- ✅ Robust error handling
- ✅ Clean CLI interface
- ✅ Comprehensive testing

## 11. Release Planning

### 11.1 Version Strategy
**v0.3.0 - Major Feature Release**
- WeChat integration complete
- LLM translation notes synthesis
- Author-approved design implementation
- Full documentation and examples

### 11.2 Launch Checklist
- [ ] Implementation complete
- [ ] Testing passed
- [ ] Documentation updated
- [ ] Version bump to 0.3.0
- [ ] Release notes prepared

## Conclusion

This revised specification combines the best of all approaches:
- **Author's design vision** (structure, naming, scope)
- **LLM quality synthesis** (intelligent translation notes)
- **Robust technical implementation** (modular, testable)
- **Simplified integration** (no image complexity)

The result is a focused, high-quality WeChat integration that leverages VPSWeb's strengths while respecting the author's specific design decisions.

**Next Step**: Create detailed TODO list for implementation approval.