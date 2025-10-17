# WeChat Official Account Integration

VPSWeb includes comprehensive WeChat Official Account integration for automatic article publishing.

## Overview

The WeChat integration provides:
- **Article Generation**: Automatically formats translations as WeChat articles
- **Translation Notes Synthesis**: AI-powered synthesis of translation commentary
- **Draft Management**: Save as drafts for manual review or auto-publish
- **Media Management**: Handle images and formatting for WeChat platform

## Configuration Setup

### config/wechat.yaml
```yaml
appid: "${WECHAT_APPID}"
secret: "${WECHAT_SECRET}"
article_generation:
  include_translation_notes: true
  copyright_text: "本译文与导读由【知韵译诗】施知韵VoxPoetica原创制作"
publishing:
  save_as_draft: true  # Safe default
  auto_publish: false  # Manual control
```

### Environment Variables
```bash
# Required for WeChat integration
WECHAT_APPID="your-wechat-appid"
WECHAT_SECRET="your-wechat-secret"
```

## Usage Commands

```bash
# Generate WeChat article from translation
vpsweb generate-article -j translation_output.json

# Generate with custom options
vpsweb generate-article -j translation.json -o my_articles/ --author "My Name"

# Publish to WeChat (if configured)
vpsweb publish-article -a article_metadata.json
```

## Template System

VPSWeb uses a flexible template system for WeChat articles:

- **HTML Templates**: `config/html_templates/wechat_articles/` - Control article layout and styling
- **Prompt Templates**: `config/prompts/wechat_article_notes_*.yaml` - Control LLM behavior for translation notes
- **Template Variables**: Uses Jinja2 templating with variables like `{{ poem_title }}`, `{{ poet_name }}`, etc.

### Creating Custom Templates

#### HTML Templates (Article Layout)
1. Copy `config/html_templates/wechat_articles/default.html` to a new file
2. Modify the HTML structure and CSS styling as needed
3. Use supported template variables (see template file for examples)
4. Update `config/wechat.yaml`: `article_template: "your_template_name"`

#### Prompt Templates (Translation Notes)
1. Create a new prompt template in `config/prompts/` (e.g., `wechat_article_notes_custom.yaml`)
2. Customize the prompt for different LLM behaviors or output styles
3. Update `config/wechat.yaml`: `prompt_template: "wechat_article_notes_custom"`

### Available Prompt Templates
- `wechat_article_notes_reasoning` - For reasoning models, detailed analysis
- `wechat_article_notes_nonreasoning` - For standard models, concise output

## Implementation Details

The WeChat integration handles:
- Article metadata extraction and formatting
- Template rendering with Jinja2
- Image processing and media management
- WeChat API authentication and publishing
- Error handling and retry logic

For detailed implementation information, see the WeChat integration modules in `src/vpsweb/services/wechat/`.

## Troubleshooting

Common issues and solutions:
- **Authentication failures**: Verify WECHAT_APPID and WECHAT_SECRET are correctly set
- **Template errors**: Check Jinja2 template syntax and variable names
- **API rate limits**: WeChat has rate limits - implement appropriate delays
- **Media upload failures**: Ensure images meet WeChat format and size requirements