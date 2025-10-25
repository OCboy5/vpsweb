# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**VPSWeb (Vox Poetica Studio Web)** is a professional AI-powered poetry translation platform that implements a collaborative Translator→Editor→Translator workflow to produce high-fidelity translations between English and Chinese (and other languages).

**Tech Stack**: Python, Poetry, FastAPI, SQLAlchemy, Pydantic, AsyncIO, OpenAI-compatible APIs, YAML configuration, Tailwind CSS

# Development Guidelines
## Philosophy
### Core Beliefs
- **Incremental progress over big bangs** - Small changes that compile and pass tests
- **Learning from existing code** - Study and plan before implementing
- **Pragmatic over dogmatic** - Adapt to project reality
- **Clear intent over clever code** - Be boring and obvious
### Simplicity Means
- Single responsibility per function/class
- Avoid premature abstractions
- No clever tricks, choose the boring solution
- If you need to explain it, it's too complex

## Process
### 1. Planning & Staging
Use Brainstorming and Debating Guidelines to make non-trivial decisions in the plan.
Break complex work into 3-5 stages. Document in `IMPLEMENTATION_PLAN.md`:
```markdown
## Stage N: [Name]
**Goal**: [Specific deliverable]
**Success Criteria**: [Testable outcomes]
**Tests**: [Specific test cases]
**Status**: [Not Started|In Progress|Complete]
```
- Update status as you progress
### 2. Implementation Flow
1. **Understand** - Study existing patterns in codebase
2. **Test** - Write test first (red)
3. **Implement** - Minimal code to pass (green)
4. **Refactor** - Clean up with tests passing
5. **Commit** - With clear message linking to plan
### 3. When Stuck (After 3 Attempts)
**CRITICAL**: Maximum 3 attempts per issue, then STOP.
1. **Document what failed**:   
- What you tried   
- Specific error messages   
- Why you think it failed
2. **Research alternatives**:   
- Find 2-3 similar implementations   
- Note different approaches used
3. **Question fundamentals**:   
- Is this the right abstraction level?   
- Can this be split into smaller problems?   
- Is there a simpler approach entirely?
4. **Try different angle**:   
- Different library/framework feature?   
- Different architectural pattern?   
- Remove abstraction instead of adding?
## Technical Standards
### Architecture Principles
- **Composition over inheritance**
 - Use dependency injection
- **Interfaces over singletons**
 - Enable testing and flexibility
- **Explicit over implicit**
 - Clear data flow and dependencies
- **Test-driven when possible**
 - Never disable tests, fix them
### Code Quality
- **Every commit must**:
  - Compile successfully
  - Pass all existing tests
  - Include tests for new functionality
  - Follow project formatting/linting
- **Before committing**:
  - Run formatters/linters
  - Self-review changes
  - Ensure commit message explains "why"
### Error Handling
- Fail fast with descriptive messages
- Include context for debugging
- Handle errors at appropriate level
- Never silently swallow exceptions
## Decision Framework
When multiple valid approaches exist, choose based on:
1. **Testability** - Can I easily test this?
2. **Readability** - Will someone understand this in 6 months?
3. **Consistency** - Does this match project patterns?
4. **Simplicity** - Is this the simplest solution that works?
5. **Reversibility** - How hard to change later?
## Project Integration
### Learning the Codebase
- Find 3 similar features/components
- Identify common patterns and conventions
- Use same libraries/utilities when possible
- Follow existing test patterns
### Tooling
- Use project's existing build system
- Use project's test framework
- Use project's formatter/linter settings
- Don't introduce new tools without strong justification
## Quality Gates
### Definition of Done
- [ ] Tests written and passing
- [ ] Code follows project conventions
- [ ] No linter/formatter warnings
- [ ] Commit messages are clear
- [ ] Implementation matches plan
- [ ] No TODOs without issue numbers
### Test Guidelines
- Test behavior, not implementation
- One assertion per test when possible
- Clear test names describing scenario
- Use existing test utilities/helpers
- Tests should be deterministic
## Important Reminders
**NEVER**:
- Use `--no-verify` to bypass commit hooks
- Disable tests instead of fixing them
- Commit code that doesn't compile
- Make assumptions - verify with existing code
**ALWAYS**:
- Commit working code incrementally
- Update plan documentation as you go
- Learn from existing implementations
- Stop after 3 failed attempts and reassess
- Always use context7 when I need code generation, setup or configuration steps, or library/API documentation. This means you should automatically use the Context7 MCPtools to resolve library id and get library docs without me having to explicitly ask.

### Brainstorming and Debating Guidelines

#### **Effective Brainstorming Session**
**Purpose**: Generate diverse approaches before settling on a solution

**Process**:
1. **Divergent Thinking**: Generate as many approaches as possible without judgment
2. **Consider Multiple Dimensions**:
   - Technical approaches (different patterns, libraries, architectures)
   - Implementation strategies (phased vs. big-bang, monolithic vs. modular)
   - User experience considerations
   - Maintenance and scalability implications
3. **Document All Ideas**: Capture every approach with brief pros/cons
4. **Encourage Creativity**: Consider unconventional solutions that might reveal new insights

**Brainstorming Output Format**:
```markdown
## Brainstorming: [Decision Name]

### Approach 1: [Approach Name]
- **Description**: Brief description of the approach
- **Pros**: List of advantages
- **Cons**: List of disadvantages
- **Risks**: Potential risks and challenges
- **Best For**: Situations where this approach excels

### Approach 2: [Alternative Approach]
- **Description**: Brief description of the approach
- **Pros**: List of advantages
- **Cons**: List of disadvantages
- **Risks**: Potential risks and challenges
- **Best For**: Situations where this approach excels

### Approach 3: [Another Alternative]
- ... continue for all approaches considered
```

#### **Structured Debating Session**
**Purpose**: Critical evaluation of approaches through systematic comparison

**Process**:
1. **Establish Criteria**: Define evaluation criteria relevant to the decision
   - Technical complexity and risk
   - Implementation time and effort
   - Maintenance burden
   - Scalability and performance
   - Alignment with project goals
   - User impact

2. **Systematic Comparison**: Compare each approach against all criteria
3. **Challenge Assumptions**: Question underlying assumptions for each approach
4. **Identify Hidden Risks**: Look for risks that might not be immediately obvious
5. **Consider Context**: Evaluate approaches based on specific project constraints

**Debating Output Format**:
```markdown
## Debating Session: [Decision Name]

### Evaluation Criteria
- **Technical Risk**: [Description of what this means for the decision]
- **Implementation Complexity**: [Description]
- **Maintenance Impact**: [Description]
- **Scalability**: [Description]
- **User Experience**: [Description]

### Approach Comparison Matrix
| Approach | Technical Risk | Complexity | Maintenance | Scalability | UX | Overall Score |
|----------|----------------|------------|-------------|-------------|----|--------------|
| Approach 1 | High/Medium/Low | High/Medium/Low | High/Medium/Low | High/Medium/Low | High/Medium/Low | [Score] |
| Approach 2 | High/Medium/Low | High/Medium/Low | High/Medium/Low | High/Medium/Low | High/Medium/Low | [Score] |

### Key Debating Points
- **Point 1**: [Critical discussion point with resolution]
- **Point 2**: [Another critical discussion point with resolution]
- **Point 3**: [Additional point where approaches differ significantly]

### Risk Analysis
- **Approach 1 Risks**: [Specific risks with mitigation strategies]
- **Approach 2 Risks**: [Specific risks with mitigation strategies]

### Final Recommendation
- **Selected Approach**: [Which approach and why]
- **Key Reasons**: [Top 3 reasons for this choice]
- **Mitigation Strategy**: [How we'll address the chosen approach's risks]
```

#### **Integration with Plan Phase**
**Enhanced Plan Presentation**:
When presenting plan for user approval, include:
1. **Brainstorming Summary**: Brief overview of approaches considered
2. **Key Debating Points**: Most important trade-offs discussed
3. **Decision Rationale**: Clear explanation of why chosen approach is optimal
4. **Risk Mitigation**: How identified risks will be addressed

### 2. Decision Classification

**Trivial Decisions** (Direct Implementation):
- Simple bug fixes with clear solutions
- Adding comments or improving documentation
- Single-file refactorings that don't affect interfaces
- Configuration value updates

**Non-Trivial Decisions**:
- Adding new workflow steps or modes
- Changing API interfaces or data models
- Modifying core workflow orchestration
- Adding new LLM providers or integration patterns
- Changes affecting multiple configuration files
- Architectural refactoring
- New feature implementations

### Key Configuration Files
- `config/default.yaml`: Main workflow configuration
- `config/models.yaml`: Provider configurations
- `config/wechat.yaml`: WeChat Official Account integration
- `config/repository.yaml`: Central Repository and WebUI configurations

### Configuration Structure
- YAML format for readability
- Environment variable substitution using `${VAR_NAME}` syntax
- Pydantic model validation
- Support for workflow modes: reasoning, non_reasoning, hybrid

## Quick References

### Release Management
🚨 **CRITICAL**: All releases MUST follow the strict workflow in `VERSION_WORKFLOW.md`.
