# OneAgent Architecture Research

## Sources Reviewed

| Repo | Language | Core Contribution | Adopted Pattern |
|------|----------|-------------------|---------------|
| OpenClaw | TypeScript | Harness, session lanes, workspace files, hooks, diagnostics | workspace, session, hooks, diagnostics, queue |
| Eigent | Python/TS | Domain-driven FastAPI, SSE playback, MCP service, Zustand | SSE stream, project grouping, file validation |
| Super-App | Python | Adapter-as-data, skill command maps, recipe runner, facade | security, recipe runner |
| Hermes | Python | SOUL persona, cron heartbeat, update stash | heartbeat/cron patterns |
| **GPT Researcher** | Python | Skill composition, 21 retrievers, GenericLLMProvider, cost callbacks, prompt family | **llm/provider.py**, **skills/**, budget cost callbacks |
| **OpenManus** | Python | Agent harness ladder (BaseAgent->ReActAgent->ToolCallAgent), ToolCollection, stuck detection, tool policies | **agent/base.py**, **agent/react.py**, **agent/toolcall.py** |
| **Goose** | Rust | Provider registry trait, MCP extensions, tool inspection chain, event streaming | provider registry, tool inspection, hooks |
| **Gemini CLI** | TypeScript | Scheduler, policy engine, context masking, loop detection, SDK tools | **scheduler/**, **policy/**, **context/** |
| **Cline** | TypeScript | createTool factory, prepareTurn seam, tool policy/approval, event stream | createTool factory, event-driven UI |
| **Firecrawl** | TypeScript | Scrape engine abstraction, fallback list, Zod config, queue | **scraper/** engine registry |
| **Aider** | Python | Repo map, str_replace_editor, linting, git integration | **coding/edit_tool.py**, read/shell tools |
| **smolagents** | Python | Code agent, local Python executor, tool decorator, memory | **tools/factory.py**, code agent concept |
| **OpenHands** | Python | Sandbox sidecar, event stream, dependency injection, agent controller | event architecture, tool isolation |
| **AutoGPT** | Python/TS | Block-graph agents, Forge framework, platform marketplace | composition/planning idea |
| **CrewAI** | Python | Crew composition, role/goal/backstory, task delegation | role system |
| **MetaGPT** | Python | Role/Action/SOP, message passing, environment, memory | role/action SOP |
| **SWE-agent** | Python | Agent-Computer Interface (ACI), command parsing, history processors | ACI command interface |
| **Chainlit** | Python | Chat UI framework, streaming, thinking blocks, file upload | **frontend/** chat UX patterns |
| **LobeChat** | TypeScript | Multi-agent UI, agent marketplace, plugin system | frontend agent orchestration UX |
| **LibreChat** | TypeScript | Multi-model UI, tool visualization, conversation management | frontend multi-model UX |
| **Dify** | Python/TS | LLM app builder, RAG pipeline builder, workflow orchestration | workflow/recipe engine |
| **Flowise** | TypeScript | Drag-and-drop LangChain workflow builder | visual workflow concepts |
| **n8n** | TypeScript | Visual workflow canvas, 1500+ integrations, AI agent nodes | workflow automation engine |
| **Haystack** | Python | Production RAG pipelines, agents, pipelines, document stores | **rag/** vector store + retrieval |
| **RAGFlow** | Python | Deep document understanding, RAG pipeline, chunking strategies | RAG document processing |
| **Chroma** | Python | Open-source vector database, embedding storage, similarity search | **rag/** ChromaStore backend |
| **Qdrant** | Rust | Vector database, filtering, payload indexing | vector store backend option |
| **Langfuse** | TypeScript/Python | LLM observability, tracing, cost tracking, datasets | **observability/** tracer + metrics |
| **Helicone** | TypeScript | LLM proxy, observability, cost tracking, automatic fallbacks | observability patterns |
| **LiteLLM** | Python | LLM gateway for 100+ models, fallback chains, spend tracking | **llm/fallback.py** provider fallbacks |
| **Portkey** | TypeScript | LLM gateway, virtual keys, fallbacks, load balancing | gateway patterns |
| **Tavily** | Python | Agent-optimized search API, answer extraction, raw context | **tools/tavily_search.py** web search |
| **DSPy** | Python | Programming LLMs with modules, optimizers, signatures | structured LLM programming |
| **Playwright MCP** | TypeScript | MCP server for browser automation, accessibility snapshots | **tools/mcp_client.py** MCP support |
| **Composio** | TypeScript | Integration platform for 100+ tools, auth management | integration marketplace concept |
| **Devika** | Python | Autonomous software engineer, planning, execution | autonomous coding patterns |
| **Steel** | TypeScript | Browser API for AI agents, headless browser automation | browser automation backend |
| **E2B** | TypeScript | Sandboxed code execution, cloud environments | secure execution patterns |
| **Qwen-Agent** | Python | Browser agent, tool use, multilingual support | agent patterns |
| **CAMEL** | Python | Role-playing multi-agent framework, message passing | multi-agent patterns |
| **BabyAGI** | Python | Task planning, autonomous execution, task queue | autonomous task management |
| **AgentGPT** | TypeScript | Browser-based autonomous agents, agent assembly | agent UX patterns |
| **Superagent** | TypeScript | Safe AI apps, MCP support, agent platform SDK | agent SDK patterns |

## Native OneAgent Modules

```
oneagent-super-app/core/
├── llm/            # Provider registry + GenericLLM + FallbackRegistry (GPT Researcher/Goose/LiteLLM style)
├── tools/          # BaseTool, ToolCollection, factory, registry + TavilySearchTool + MCPClient (OpenManus/smolagents/Cline)
├── agent/          # Harness ladder: BaseAgent -> ReActAgent -> ToolCallAgent
├── scraper/        # Engine abstraction + fallback (Firecrawl style)
├── coding/         # ReadFileTool, ShellTool, StrReplaceEditor (Aider/Anthropic style)
├── skills/         # Skill composition (GPT Researcher style)
├── context/        # Context manager + compression (Gemini CLI/Cline)
├── policy/         # Declarative per-tool policy (Gemini CLI/Goose)
├── scheduler/      # Async task scheduler (Gemini CLI/Super-App)
├── workspace/      # Structured workspace files (OpenClaw)
├── session/        # JSONL session persistence (OpenClaw)
├── security/       # Command/URL/file validation (Super-App/Goose)
├── recipe/         # Multi-step recipe runner (Super-App)
├── harness/        # Pluggable model harnesses (OpenClaw)
├── subagent/       # Background sub-agents (OpenManus/Goose)
├── hooks/          # Lifecycle hooks (OpenClaw/Gemini CLI)
├── diagnostics/    # Flags + timeline + liveness (OpenClaw)
├── capabilities/   # Capability registry (OpenClaw)
├── queue/          # Steering/followup queues (OpenClaw)
├── observability/  # Tracing, cost tracking, latency percentiles (Langfuse/Helicone)
└── rag/            # Vector store, document ingestion, retrieval (Haystack/Chroma)
```

## Key Adopted Patterns

1. **Agent Harness Ladder**: thin orchestrator layers (BaseAgent, ReActAgent, ToolCallAgent) lets specialists like CodeAgent inherit safely.
2. **ToolCollection + BaseTool**: declarative tools with `to_param()`, runtime add, error isolation.
3. **Provider Registry**: `provider:model` string resolution + lazy client creation + automatic fallback chains (LiteLLM/Portkey).
4. **Skill Composition**: research/coding/browser skills are pluggable and receive a SkillContext.
5. **Scraper Engine Registry**: fetch + playwright engines with feature flags and fallback.
6. **Policy Engine**: per-tool ALLOW/DENY/ASK_USER decisions, wildcard defaults.
7. **Event Stream**: AgentEvent union drives UI and can be serialized.
8. **Cost Callbacks**: threaded through LLM calls for observability.
9. **Stuck Detection**: duplicate assistant messages trigger recovery prompt.
10. **Context Compression**: drop oldest low-priority messages under token budget.
11. **MCP Integration**: Model Context Protocol client for connecting to external MCP servers (Playwright MCP style).
12. **Observability Tracing**: lightweight span-based tracing with cost/latency tracking (Langfuse/Helicone patterns).
13. **Vector Store RAG**: in-memory and Chroma-backed vector stores for document retrieval (Haystack/Chroma patterns).
14. **Web Search**: Tavily-style agent-optimized search with answer extraction.

## Frontend Views

- Agent Architecture
- Skill Runner
- Web Scraper
- Coding Agent Harness
- Specialist Evolution
- Integrations Hub
- LLM Gateway
- Scheduler
- Scraper Panel
- Settings Page
- Meta Authoring
- Open Source Suite

All wired into Sidebar and App.tsx.

## API Endpoints (30 total)

| # | Endpoint | Purpose |
|---|----------|---------|
| 1 | GET /api/health | Health check |
| 2 | POST /api/llm/generate | LLM generation with fallback |
| 3 | POST /api/agent/run | Agent loop execution |
| 4 | POST /api/fhir/audit | FHIR inconsistency audit |
| 5 | POST /api/meta/author | Meta module authoring |
| 6 | GET /api/meta/list | List self-authored modules |
| 7 | POST /api/meta/status | Update module status |
| 8 | POST /api/meta/run | Execute module in sandbox |
| 9 | POST /api/knowledge/query | RAG knowledge query |
| 10 | POST /api/tools/firecrawl | Web scraping |
| 11 | POST /api/tools/browser-use | Browser automation |
| 12 | POST /api/research/run | Deep research |
| 13 | GET /api/workspace/context | Workspace context |
| 14 | POST /api/workspace/initialize | Initialize workspace |
| 15 | GET /api/sessions | Session list |
| 16 | POST /api/sessions/create | Create session |
| 17 | GET /api/sessions/:id/liveness | Session liveness |
| 18 | GET /api/agent/stream/:id | SSE streaming |
| 19 | POST /api/subagent/spawn | Spawn sub-agent |
| 20 | GET /api/subagent/:id | Sub-agent status |
| 21 | GET /api/subagent | Sub-agent list |
| 22 | GET /api/harnesses | Harness registry |
| 23 | GET /api/capabilities | Capabilities registry |
| 24 | GET /api/hooks | Hook system |
| 25 | POST /api/hooks/register | Register hook |
| 26 | GET /api/recipes | Recipe list |
| 27 | POST /api/recipes/:id/run | Run recipe |
| 28 | GET /api/diagnostics/flags | Diagnostics flags |
| 29 | POST /api/security/validate-command | Command validation |
| 30 | GET /api/providers | Provider registry |
| 31 | POST /api/skills/:name/run | Run skill |
| 32 | POST /api/coding/run | Run coding agent |
| 33 | POST /api/scrape | Scrape URL |
| 34 | POST /api/research/run | Research stub |
| 35 | GET /api/tools | Tool registry |
| 36 | POST /api/policy/check | Policy check |
| 37 | POST /api/search/tavily | Tavily web search |
| 38 | GET /api/mcp/servers | MCP server list |
| 39 | POST /api/mcp/servers | Connect MCP server |
| 40 | POST /api/mcp/servers/:name/call | Call MCP tool |
| 41 | DELETE /api/mcp/servers/:name | Disconnect MCP server |
| 42 | GET /api/observability/traces | Get traces |
| 43 | POST /api/observability/traces/clear | Clear traces |
| 44 | POST /api/rag/ingest | Ingest documents |
| 45 | POST /api/rag/search | Search documents |
| 46 | GET /api/providers/fallbacks | Provider fallback chains |

## Repos Cloned for Research (54 total)

### Previously Explored (18)
aider, AutoGPT, browser-use, cline, crewAI, firecrawl, gemini-cli, goose, gpt-researcher, MetaGPT, open-interpreter, OpenHands, OpenManus, smolagents, SWE-agent, autogen, crawl4ai, dspy, langgraph, mem0, playwright-mcp, qwen-agent, stagehand

### Newly Explored (36)
chainlit, lobe-chat, librechat, appsmith, n8n, dify, flowise, devika, steel, daytona, e2b, qdrant, chroma, weaviate, haystack, ragflow, quivr, fastgpt, composio, superagent, langfuse, helicone, litellm, portkey, tavily, babyagi, agentgpt, camel, OpenManus_review, llamaindex, qwen-agent, dspy

## Feature Adoption Matrix

| Feature | Source Repos | OneAgent Module | Status |
|---------|-------------|-----------------|--------|
| Agent Harness Ladder | OpenManus, smolagents, Cline | agent/ | Implemented |
| Tool Registry + BaseTool | OpenManus, smolagents, Cline | tools/ | Implemented |
| Provider Registry | Goose, Cline, GPT Researcher | llm/provider.py | Implemented |
| Provider Fallbacks | LiteLLM, Portkey | llm/fallback.py | Implemented |
| Skill Composition | GPT Researcher | skills/ | Implemented |
| Scraper Engines | Firecrawl | scraper/ | Implemented |
| Coding Tools | Aider | coding/ | Implemented |
| Context Compression | Gemini CLI, Cline | context/ | Implemented |
| Policy Engine | Gemini CLI, Goose | policy/ | Implemented |
| Scheduler | Gemini CLI | scheduler/ | Implemented |
| Workspace/Session | OpenClaw | workspace/, session/ | Implemented |
| Hooks | OpenClaw, Gemini CLI | hooks/ | Implemented |
| MCP Client | Playwright MCP, Goose | tools/mcp_client.py | Implemented |
| Observability Tracing | Langfuse, Helicone | observability/tracer.py | Implemented |
| Cost/Latency Metrics | Langfuse, LiteLLM | observability/metrics.py | Implemented |
| Vector Store RAG | Haystack, Chroma, LlamaIndex | rag/vector_store.py | Implemented |
| Web Search | Tavily | tools/tavily_search.py | Implemented |
| Workflow Engine | n8n, Dify, Flowise | recipe/ | Conceptual |
| Chat UI | Chainlit, LibreChat, LobeChat | src/ | Partial |
| Vector DB Backends | Qdrant, Weaviate, Chroma | rag/ | Partial |
