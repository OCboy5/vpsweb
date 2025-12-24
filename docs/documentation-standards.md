# Documentation Standards

This document outlines the documentation standards and requirements for VPSWeb.

## Code Documentation

### Docstring Requirements
All public APIs must have comprehensive docstrings following Google/NumPy style:

```python
def translate_poem(poem_text: str, source_lang: str, target_lang: str) -> str:
    """Translate a poem from source language to target language.

    This function uses the configured workflow to perform a complete
    3-step translation process, including initial translation,
    editorial review, and final revision.

    Args:
        poem_text: The original poem text to translate
        source_lang: Source language code (e.g., 'English', 'Chinese')
        target_lang: Target language code (e.g., 'English', 'Chinese')

    Returns:
        The translated poem text

    Raises:
        ValueError: If poem_text is empty or languages are invalid
        ProviderError: If LLM provider encounters an error

    Example:
        >>> result = translate_poem("Roses are red", "English", "Chinese")
        >>> print(result)
        玫瑰是红色的
    """
```

### Inline Comments
Complex algorithms need inline comments explaining the logic:

```python
# Calculate the optimal token limit based on model constraints
# DeepSeek models have different limits for reasoning vs standard modes
if model_type == "reasoning":
    # Reasoning models need extra tokens for chain-of-thought
    max_tokens = min(8000, base_limit * 0.7)  # Reserve 30% for reasoning
else:
    # Standard models can use full limit for output
    max_tokens = min(4000, base_limit)
```

### Configuration Examples
Include configuration examples in docstrings:

```python
def create_workflow(config: WorkflowConfig) -> TranslationWorkflow:
    """Create a translation workflow from configuration.

    Args:
        config: Workflow configuration object

    Example:
        >>> config = WorkflowConfig(
        ...     mode=WorkflowMode.HYBRID,
        ...     providers={
        ...         'tongyi': ProviderConfig(api_key='...', model='qwen-max'),
        ...         'deepseek': ProviderConfig(api_key='...', model='deepseek-reasoner')
        ...     }
        ... )
        >>> workflow = create_workflow(config)
    """
```

### Usage Examples
Provide practical usage examples in docstrings:

```python
async def batch_translate(poems: List[str]) -> List[str]:
    """Translate multiple poems in batch.

    Args:
        poems: List of poem texts to translate

    Returns:
        List of translated poems in the same order

    Example:
        >>> poems = ["Poem 1", "Poem 2", "Poem 3"]
        >>> results = await batch_translate(poems)
        >>> print(results)
        ['诗 1', '诗 2', '诗 3']
    """
```

## Project Documentation

### README.md
- **Project overview**: Brief description of what VPSWeb does
- **Quick start**: Installation and basic usage instructions
- **Features**: Key features and capabilities
- **Installation**: Step-by-step installation guide
- **Usage**: Basic usage examples
- **Contributing**: Guidelines for contributors

### DEVELOPMENT.md
- **Development setup**: Detailed development environment setup
- **Architecture**: System architecture overview
- **Development workflow**: How to contribute code
- **Testing**: How to run and write tests
- **Code style**: Coding standards and conventions

### CHANGELOG.md
- **Version history**: Chronological list of versions
- **Changes**: Detailed change descriptions for each version
- **Migration guides**: Instructions for upgrading between versions
- **Breaking changes**: Clearly marked breaking changes

### API Documentation
- **Module documentation**: Documentation for all modules
- **Class documentation**: Documentation for all public classes
- **Function documentation**: Documentation for all public functions
- **Type hints**: Comprehensive type annotations

## Documentation Structure

### docs/ Directory Organization
```
docs/
├── wechat-integration.md      # WeChat integration guide
├── workflow-modes.md          # Workflow mode documentation
├── api-patterns.md            # API integration patterns
├── testing.md                 # Testing strategy and guidelines
├── future-development.md      # Future development roadmap
├── documentation-standards.md # This file
└── reflections/               # Project reflections and learnings
    ├── reflection-index.md
    └── 2025/
        └── yyyy-mm-dd-project-reflection.md
```

### Documentation Standards

#### Markdown Formatting
- Use consistent heading levels (# ## ### ####)
- Use bullet points for lists
- Use code blocks with language specification
- Use tables for structured data
- Use bold and italic sparingly for emphasis

#### Code Examples
- Use syntax highlighting in code blocks
- Provide complete, runnable examples
- Include error handling in examples
- Show expected output where appropriate

#### Cross-References
- Use relative links for internal documentation
- Use absolute URLs for external references
- Include section anchors where appropriate
- Verify all links work correctly

## Writing Guidelines

### Tone and Style
- **Clear and concise**: Use simple, direct language
- **Active voice**: Prefer active voice over passive
- **Present tense**: Use present tense for describing current functionality
- **Consistent terminology**: Use consistent terminology throughout

### Audience Consideration
- **Technical accuracy**: Ensure technical accuracy
- **Appropriate detail**: Provide appropriate level of detail
- **Progressive disclosure**: Organize information from simple to complex
- **Practical focus**: Focus on practical, actionable information

### Accessibility
- **Alt text**: Provide alt text for images
- **Descriptive links**: Use descriptive link text
- **Structure**: Use proper heading structure
- **Color contrast**: Ensure sufficient color contrast

## Review Process

### Documentation Review Checklist
- [ ] Content accuracy and completeness
- [ ] Consistent terminology and style
- [ ] Working code examples
- [ ] Valid internal and external links
- [ ] Proper formatting and structure
- [ ] Appropriate level of detail

### Review Workflow
1. **Author review**: Self-review for completeness
2. **Peer review**: Review by another team member
3. **Technical review**: Review for technical accuracy
4. **Final approval**: Approval for inclusion in documentation

## Maintenance

### Regular Updates
- **Code changes**: Update documentation when code changes
- **Feature additions**: Document new features
- **Deprecations**: Document deprecated features
- **Bug fixes**: Update documentation for bug fixes

### Documentation Quality
- **User feedback**: Collect and incorporate user feedback
- **Usage analytics**: Monitor documentation usage
- **Search optimization**: Optimize for searchability
- **Accessibility**: Ensure accessibility compliance

## Tools and Resources

### Documentation Tools
- **Markdown editors**: Recommended editors for documentation
- **Linting tools**: Markdown linting tools
- **Link checkers**: Tools to check broken links
- **Preview tools**: Tools to preview documentation

### Style Guides
- **Google Style Guide**: For docstring formatting
- **Microsoft Style Guide**: For technical writing
- **Chicago Manual of Style**: For general writing guidance
- **Project-specific style**: Project-specific conventions

### Reference Materials
- **API documentation**: Reference API documentation
- **Configuration examples**: Configuration reference examples
- **Troubleshooting guides**: Common issues and solutions
- **Best practices**: Industry best practices

Following these standards ensures high-quality, maintainable documentation that serves both developers and users effectively.