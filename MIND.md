# MIND — the OneAgent Vision

## Fundamental aim
One base agent (**the Mind**) with a growing set of **Senses** — sensors that absorb everything
its user touches — and an **infinite learning loop** that turns absorbed data into limbs,
skills, knowledge bases, knowledge graphs, extensions, and MCPs until the user's whole
life is automated.

The Mind is persistent, self-extending, and learns from ALL accessible sources:
- Communication: email (Outlook/Graph), Teams, Slack, WhatsApp
- Work: Azure DevOps / Jira work items, SharePoint, FHIR servers
- AI context: local AI session chats (Hermes, Claude Code, Codex, Goose, OpenClaw…),
  online AI chats (via browser/Chrome extension), search history, bookmarks
- Everything else the user shares: files, notes, screenshots, voice

## Architecture: Mind = Senses + Cortex + Limbs

```
        ┌─────────────────────────────────────────────┐
        │                  MIND                       │
        │                                             │
Senses  │  ingest ──► Experience Store ──► Knowledge  │  Limbs
(web,   │   loop      (sqlite: raw +     Graph + KB   │  (modules,
mail,   │  (cron,     normalized,        (topics,     │  skills,
teams,  │   events)   deduped)           entities,    │  MCPs,
AI      │                                edges)       │  extensions)
chats…) │        │                            │       │
        │        ▼                            ▼       │
        │   Cortex: LLM router + agent loop + meta-  │
        │   author (writes new limbs from patterns)  │
        └─────────────────────────────────────────────┘
```

- **Senses** (`baqa/senses/sensors/`): each sensor implements `Sensor.poll() -> list[Experience]`.
  Normalized schema: `{id, source, kind, ts, title, text, entities, uri, hash}`.
  Deduped by content hash. Nothing is ever ingested twice.
- **Experience Store** (`store.py`): SQLite. Raw + FTS5 search. Zero heavy deps.
- **Knowledge Graph** (`graph.py`): nodes = entities/topics, edges = co-occurrence within
  experiences. Powers "what do I know about X".
- **Ingest loop** (`ingest.py`): polls all enabled sensors, absorbs, extracts entities,
  grows the graph. Runs on-demand, on a cron heartbeat, or on file-change events.
- **Cortex**: existing `core/llm` router + `core/agents` loop + `core/meta` self-authoring.
- **Limbs**: existing `modules/` (fhir, research, content, coding, files, leap, work_ops)
  + anything the meta-agent authors next.

## Feature absorption (market research → base variant)
Track competitors' features in `SENSORS_BACKLOG.md`. Every notable feature of every agent
product (browser-use, deep-research, openclaw, hermes, graphify, openworkers, odysseus…)
gets: researched → mapped to a sense/limb → implemented or queued. The base variant
absorbs all of it.

## Operating rules
1. Never lose an experience: append-only store, hash-deduped.
2. Senses are read-only over source systems. Never write back without approval.
3. The loop never stops: cron heartbeat ingests, digests, and proposes new limbs.
4. Guardrails: destructive or outbound actions require user approval (Aug-29 directive).
