# OneAgent

An open-source **generalist AI agent** that learns from your data (emails, Teams, Slack, files, Jira, Azure DevOps) and evolves into specialist **Limbs**.

## Base Capabilities

- Web fetch / scrape
- Browser automation
- Web search / deep research
- Code execution
- Coding specialist
- File operations
- LLM router (OpenAI, Gemini, Anthropic, Ollama)

## Architecture

Native agent core built by studying 14 open-source AI frameworks:

| Module | Inspiration |
|---|---|
| `core/llm/` | GPT Researcher, Goose, Cline |
| `core/tools/` | OpenManus, smolagents, Cline |
| `core/agent/` | OpenManus |
| `core/scraper/` | Firecrawl |
| `core/coding/` | Aider, Anthropic |
| `core/skills/` | GPT Researcher |
| `core/context/` | Gemini CLI, Cline |
| `core/policy/` | Gemini CLI, Goose |
| `core/scheduler/` | Gemini CLI, Super-App |
| `core/workspace/` | OpenClaw |
| `core/session/` | OpenClaw |
| `core/security/` | Super-App, Goose |
| `core/recipe/` | Super-App |
| `core/harness/` | OpenClaw |
| `core/subagent/` | OpenManus, Goose |
| `core/hooks/` | OpenClaw, Gemini CLI |
| `core/diagnostics/` | OpenClaw |
| `core/capabilities/` | OpenClaw |
| `core/queue/` | OpenClaw |

## Running

1. `npm install`
2. Set `GEMINI_API_KEY` in `.env.local`
3. `npm run dev`

## Python core smoke test

```bash
cd core
python -c "from core.llm import GLOBAL_REGISTRY; print(GLOBAL_REGISTRY.list())"
```
