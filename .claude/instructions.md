# Claude Code Project Instructions

## Available Tools Overview

You have access to powerful MCP tools that significantly improve your capabilities. **You MUST proactively use these tools** rather than relying on basic grep or manual searches.

**Your MCP Tools:**
- **vscode-mcp-server** - VS Code IDE integration (PRIMARY for code navigation)
- **context7** - Semantic code search and understanding
- **github** - Repository issues, PRs, commits, discussions
- **deepwiki** - Documentation search for libraries/frameworks
- **fetch** - External documentation and API specs
- **chrome-devtools** - Web application debugging

---

## Core Workflow (VS Code Integration)

You are working on an existing codebase, which you can access using your tools. These code tools interact with a VS Code workspace.

### WORKFLOW ESSENTIALS:
1. **Always start** exploration with `list_files_code` on root directory (.) first
2. **CRITICAL**: Run `get_diagnostics_code` after EVERY set of code changes before completing tasks
3. For **large changes, new files, or uncertain content**: use `create_file_code` with `overwrite=true`

### EXPLORATION STRATEGY:
- **Start**: `list_files_code` with path='.' (never recursive on root)
- **Understand structure**: read key files like package.json, README, main entry points
- **Find symbols**: use `search_symbols_code` for functions/classes, `get_document_symbols_code` for file overviews
- **Use context7**: for semantic searches like "where is authentication implemented?"
- **Before editing**: `read_file_code` the target file to understand current content

### EDITING BEST PRACTICES:
- **Modifications** Use Claude Code internal Edit tool
- **After any changes**: `get_diagnostics_code` to check for errors

---

## Tool Usage Rules (CRITICAL - Read This!)

### ❌ DON'T DO THIS:
- Use grep when `search_symbols_code` or `context7` would work
- Read entire files without checking `get_document_symbols_code` first
- Make changes without running `get_diagnostics_code` after
- Forget to use `github` tool when user mentions issues/PRs
- Skip `deepwiki` when encountering unfamiliar APIs or libraries
- Search the filesystem manually when `search_symbols_code` can find it

### ✅ ALWAYS DO THIS:
- Start with `list_files_code` on root directory
- Use `search_symbols_code` for finding functions, classes, variables by name
- Use `context7` for semantic/conceptual code searches
- Use `get_document_symbols_code` before reading entire files
- Run `get_diagnostics_code` after every modification
- Check `github` for project context (issues, PRs, recent commits)
- Use `deepwiki` for API/library documentation lookups
- Use `fetch` to get external documentation when needed

### When to Use Each Tool:

**vscode-mcp-server tools** (use these FIRST for code navigation):
- `list_files_code` - Start every task with this on '.'
- `search_symbols_code` - Find functions/classes/variables by name (faster than grep!)
- `get_document_symbols_code` - Get file structure before reading
- `read_file_code` - Read specific files after locating them
- `get_diagnostics_code` - After EVERY change

**context7**:
- Semantic searches: "where is user authentication handled?"
- Understanding code by meaning, not just names
- Cross-file dependency analysis
- Finding implementation patterns
- Code generation, setup/configuration steps
- Library/API documentation when deepwiki doesn't have it

**github**:
- User mentions issue numbers, PRs, or discussions
- Understanding recent changes or project history
- Finding similar problems/solutions
- Checking for related work

**deepwiki**:
- Looking up unfamiliar APIs or libraries
- Finding best practices for frameworks
- Understanding library usage patterns
- Getting official documentation

**fetch**:
- Downloading external API specifications
- Getting reference documentation not in deepwiki
- Fetching specific URLs user provides

---

## PLANNING REQUIREMENTS

Before making code modifications, present a comprehensive plan including:
1. **Confidence level (1-10)** and reasoning
2. **Search strategy**: Which tools you'll use to locate relevant code
   - Example: "I'll use `search_symbols_code` to find UserService, then `context7` to find all authentication flows"
3. **Files to modify**: Specific paths and modification approach (small edits vs complete rewrites)
4. **Verification plan**: How you'll verify the changes work (diagnostics, testing, manual review, etc.)

**IMPORTANT**: Only run code modification tools after presenting a plan and receiving explicit approval. Each change requires separate approval.

---

## ERROR HANDLING

- Let errors happen naturally - don't add unnecessary try/catch blocks
- For tool failures: follow the specific recovery guidance in each tool's description
- If uncertain about file content: use `read_file_code` to verify before making changes
- If `search_symbols_code` or `context7` don't find what you need, explain what you searched for and ask for guidance

---

## TESTING

Do not add tests unless specifically requested. If you believe testing is important, explain why and let the user decide.

---

## Remember: USE YOUR TOOLS!

You have powerful tools that make you significantly more effective than using basic grep searches:
- **search_symbols_code** finds code instantly by name
- **context7** understands code semantically
- **deepwiki** has library documentation
- **github** provides project context

**Don't default to manual searching when these tools can do it better and faster!** Proactively leverage them in every workflow.