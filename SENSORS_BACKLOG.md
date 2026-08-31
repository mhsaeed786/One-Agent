# SENSORS_BACKLOG — Feature Absorption Ledger

The Mind absorbs features from every notable agent product until the base
variant contains them all. Each row: product → its core capability → where it
lands in our architecture → status.

Status legend: ✅ live · 🔨 built, awaiting permission/keys · 📋 designed · 🔭 queued

## Agent harnesses

| Product | Core capability | Lands as | Status |
|---|---|---|---|
| Hermes Desktop | session memory, skills, cron, MCP host | Mind core + baqa `core/{skills,scheduler,mcp}` | ✅ |
| OpenClaw | multi-agent gateway, session pools | `core/agents` loop + subagent registry | 📋 |
| Goose | recipes, extensions, multi-provider | `goose-extensions/` + provider router | ✅ |
| OpenManus / AutoGPT / BabyAGI | plan→act loops | `core/agents/loop.py` plan-tool-observe | ✅ |
| OpenHands | sandboxed code execution | `core/meta/sandbox.py` | ✅ |
| SuperAGI / MetaGPT / ChatDev | role-based agent teams | `core/subagent` roles | 🔭 |
| openworkers / odysseus | distributed worker orchestration | cron runner + `core/queue` | 📋 |

## Browser & web

| Product | Core capability | Lands as | Status |
|---|---|---|---|
| browser-use | LLM-driven browser control | browser limb (Playwright) + capture sense | 🔭 (needs Playwright keys) |
| Mind Capture (ours) | online AI-chat prompt capture | `extensions/mind-capture` + `web_ai_chats` sense | 🔨 |
| LaVague / stagehand / skyvern | vision-based web automation | `browser/vision.py` | 🔭 |
| deep-research / GPT Researcher / storm | multi-hop research reports | `research` limb `deep_research` tool | ✅ |
| crawl4ai / FireCrawl | site crawling → clean markdown | `research.web_scrape` tool | ✅ |

## Knowledge & memory

| Product | Core capability | Lands as | Status |
|---|---|---|---|
| graphify / GraphRAG | entity-relation knowledge graphs | `senses/graph.py` (nodes/edges, growing) | ✅ |
| anything-llm / khoj | personal KB + RAG | `core/rag` + session_digest action | ✅ |
| MemGPT-style memory | tiered recall | ExperienceStore (raw) + FTS5 + graph | ✅ |
| Obsidian-style linking | backlinks between notes | KG edges (co-occurrence) today; backlinks 🔭 | ✅/🔭 |

## Comms senses (each gated behind explicit permission)

| Source | Lands as | Status |
|---|---|---|
| Outlook / Graph mail | `outlook_mail` sense | 📋 (needs Graph creds) |
| Teams chats + pending tasks | `teams` sense → teams_scrape_merge action | 📋 (needs Graph creds) |
| Slack | `slack` sense | 🔭 |
| WhatsApp | `whatsapp` sense | 🔭 |
| Azure DevOps / Jira work items | `devops` sense | 📋 (connector JSONs exist) |
| Chrome history / bookmarks | `browser_history` / `bookmarks` senses | 🔨 (pending grant) |
| Local repos | `github_repos` sense | 🔨 (pending grant) |
| Local AI sessions | `ai_sessions` sense | ✅ |
| Local files | `filesystem` sense | ✅ |

## Self-extension

| Product | Core capability | Lands as | Status |
|---|---|---|---|
| meta-agent (own plan) | writes/tests/registers new modules | `core/meta` ModuleAuthor | ✅ (needs .env for LLM) |
| pattern→proposal anticipation | instincts that ask for yes | `senses/anticipate.py` + cronrun | ✅ |
| skill authoring from repetition | frequent flows become skills | 🔭 after .env (LLM summarization) | 🔭 |

## Next absorption queue
1. DevOps work-items sensor (connector specs already in `baqa/goose-extensions/connectors/`)
2. Outlook/Graph sensor (creds → .env)
3. Playwright browser limb (needs `pip install playwright` + browser download)
4. Backlink views on the knowledge graph
