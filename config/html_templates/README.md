# HTML Templates Directory

This directory contains HTML templates used by VPSWeb for generating formatted output.

## Structure

```
html_templates/
├── README.md                    # This file
└── wechat_articles/             # WeChat Official Account article templates
    ├── default.html             # Default WeChat article template
    ├── modern.html              # Modern style template (future)
    ├── minimal.html             # Minimal style template (future)
    └── custom/                  # User custom templates directory
```

## WeChat Article Templates

### Available Templates

- **`default.html`**: The standard WeChat article template with traditional styling
- Future templates can be added for different styling preferences

### Template Variables

WeChat article templates support the following Jinja2 variables:

- `{{ poem_title }}`: The title of the poem
- `{{ poet_name }}`: The name of the poet
- `{{ poem_text }}`: The original poem text (formatted with line breaks)
- `{{ translation_text }}`: The English translation text
- `{{ translation_notes_section }}`: The generated translation notes HTML
- `{{ copyright_text }}`: Copyright notice from configuration

### Template Configuration

Templates are selected using the `article_template` setting in `config/wechat.yaml`:

```yaml
article_generation:
  article_template: "default"  # Points to html_templates/wechat_articles/default.html
```

### Creating Custom Templates

To create a custom WeChat article template:

1. Copy `default.html` to a new file (e.g., `my_custom.html`)
2. Modify the HTML structure and styling as needed
3. Use the supported template variables
4. Update `config/wechat.yaml` to use your template:
   ```yaml
   article_generation:
     article_template: "my_custom"
   ```

### Styling Guidelines

- Use inline CSS styles (WeChat platform limitations)
- Keep fonts readable on mobile devices
- Use responsive design principles
- Test on WeChat editor before publishing

## Future Expansion

This template system is designed to be extensible for:
- Different output formats (Markdown, PDF, etc.)
- Multiple WeChat article styles
- Custom branding templates
- A/B testing different layouts