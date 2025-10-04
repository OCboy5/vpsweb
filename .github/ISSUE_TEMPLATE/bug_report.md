---
name: Bug Report
about: Report a bug or unexpected behavior in VPSWeb
title: '[BUG] '
labels: ['bug', 'needs-triage']
assignees: ''
---

## Bug Description

<!-- A clear and concise description of what the bug is -->

## Steps to Reproduce

<!-- Detailed steps to reproduce the behavior -->
1. **Configuration**: What configuration are you using? (attach or describe)
2. **Command**: What command did you run?
3. **Input**: What was your input poem or file?
4. **Error**: What error occurred?

**Example**:
```bash
vpsweb translate --input poem.txt --source English --target Chinese --verbose
```

## Expected Behavior

<!-- A clear description of what you expected to happen -->

## Actual Behavior

<!-- What actually happened, including any error messages, logs, or stack traces -->

```
Paste error logs here
```

## Environment

**Please complete the following information:**
- **OS**: [e.g. macOS 14.0, Ubuntu 22.04, Windows 11]
- **Python Version**: [e.g. 3.9.18, 3.10.12, 3.11.4]
- **VPSWeb Version**: [e.g. 0.1.0]
- **Poetry Version**: [e.g. 1.7.1]
- **LLM Provider(s)**: [e.g. Tongyi, DeepSeek, OpenAI]

## Configuration

<!-- If applicable, share your configuration (redact API keys) -->

```yaml
# config/default.yaml (redacted)
main:
  workflow:
    name: "professional_poetry_translation"
    steps:
      - name: "initial_translation"
        provider: "tongyi"
        model: "qwen-max"
        temperature: 0.7
        max_tokens: 1000
```

## Additional Context

<!-- Add any other context about the problem here -->
- Does this happen consistently or intermittently?
- Have you tried different poems or configurations?
- Any workarounds you've discovered?

## Checklist

- [ ] I have searched existing issues to avoid duplicates
- [ ] I have included all relevant environment details
- [ ] I have provided steps to reproduce the issue
- [ ] I have included error logs or stack traces
- [ ] I have redacted any sensitive information (API keys, etc.)