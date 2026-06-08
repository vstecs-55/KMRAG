# n8n Workflow Design Skill — Design Spec

## Overview

Create a skill that helps Claude design complete, testable n8n workflows from natural language requirements. The skill focuses on education + production output: node-by-node explanation, importable JSON, testing guide, and Claude walkthrough.

## Problem Statement

When users ask Claude to help with n8n workflow design, common failures are:
1. Claude outputs raw JSON without explanation — users can't understand or modify it
2. Claude uses deprecated node types from old n8n versions
3. No testing guidance — users don't know how to verify the workflow works
4. No error handling strategy

## Design

### Skill Location
`~/.claude/skills/n8n-workflow-design/SKILL.md`

### Skill Structure
1. **Analysis** — classify the workflow pattern (RAG, Chatbot, Automation, etc.)
2. **Architecture** — diagram + node selection logic
3. **Node-by-Node Design** — config, expressions, error handling for each node
4. **JSON Export** — importable workflow with proper connections
5. **Testing Guide** — mock requests + checklist
6. **Claude Walkthrough** — natural language explanation

### Key Principles
- Always verify node types against docs.n8n.io/nodes/ (current version)
- Flag deprecated nodes and suggest modern alternatives
- Include error handling strategy for every external call
- Test before deployment (mock request + checklist)

### Red Flags — Deprecated Nodes
| Old | New |
|-----|-----|
| `Execute Command` for HTTP | `HTTP Request` |
| `JSON` node for transforms | `Code` (JS) |
| Raw HTTP for AI chat | `AI Agent` / `AI Chain` |
| `Set` node for logic | `Code` node |
| Hardcoded credentials | n8n Credentials system |

### Testing Requirements
- Mock request (curl/command) appropriate to trigger type
- Node-by-node verification checklist
- Error path testing instructions
- How to debug common issues

### Output Format
Every workflow output must include ALL of:
1. Explanation of architecture decisions
2. Node-by-node config with expressions
3. Importable JSON file
4. Testing guide with mock request
5. Claude walkthrough

## Verification
- [x] Skill created at `~/.claude/skills/n8n-workflow-design/SKILL.md`
- [x] Tested with RAG Chatbot scenario
- [x] JSON workflow generated and committed to `docs/n8n/rag-chatbot-workflow.json`
- [x] All 6 output sections generated correctly
