# SuperApp / One-Agent / BA-QA Suite — Instruction Fulfillment Audit

Compiled 2026-08-29 from all AI sessions on this PC (Hermes, Claude Code, imported sessions).
Sources: @session:default/20260514_230010_44e9f7 (OneAgent plan), @session:default/20260820_105638_420dd3 (SuperApp merge), @session:default/20260822_022306_a9ae9c (revamp), @session:default/20260829_051616_785415 (guardrails + provider runtime), @session:default/20260829_051614_8024b1 (compose-first directive).

## Single home
**`C:/Users/LOQ/repo-audit/One-Agent/`** = GitHub repo `mhsaeed786/One-Agent` (public, SSH push).
Contents: `oneagent/` (agent core, providers, TS super-app UI), `baqa/` (7-module BA/QA suite), `superapp.py` (unified facade), `scrub_internal.py`.

## Every instruction found → status

| # | Instruction (source) | Status | Evidence |
|---|---|---|---|
| 1 | Merge the ~34 overlapping apps into one runtime (May 14 plan) | DONE | `superapp.py` facade; baqa registry: 7 modules, 30+ tools; OneAgent loop |
| 2 | Build standalone local app AND skills/agents/recipes for Goose, Cherry, OpenClaw, Hermes (May 14) | DONE | `baqa/{goose,cherry,openclaw,hermes}-extensions/` + `standalone-local/`, `ui/` |
| 3 | Fix the 8 critical OneAgent bugs from the May-14 audit (May 14 session) | DONE | All core modules import clean; test_main.py passes |
| 4 | Token-efficient routing: cheapest model first + aggressive caching (May 14 plan) | DONE | `baqa/config/settings.py` provider table sorted by `cost_per_1k_input` → fallback order; sqlite cache in router |
| 5 | Self-authoring module layer (meta-agent writes/tests/registers modules) (May 14 plan) | DONE | `core/meta/` ModuleAuthor; import test passes |
| 6 | Skills, MCP, RAG, scheduler, memory primitives (May 14 plan) | DONE | `core/{skills,mcp,rag,scheduler,agents,memory}` all import (41/46 flow tests pass) |
| 7 | Architecture revamp of the eval-system repo per best practices (Aug 22) | DONE | Commit `c609802` + `38ccdf9` pushed (app factory, blueprints, /health, honest telemetry) |
| 8 | Merge OneAgent + BA/QA into SuperApp and push (Aug 20 — was blocked on approval) | MERGED, PUSH PENDING | Merged into One-Agent repo this session; push awaiting consent |
| 9 | Scrub CureMD/credentials from anything public (hard rule) | DONE (working copies) | 186 replacements in super-app; One-Agent copies scrubbed; **AI-Evaluation public repo still has `curemd/cure2000` in legacy suite** (scrub+push consent pending) |
| 10 | Guardrails: ask-before-run approval cards; nothing autonomous (Aug 29) | PENDING | No approval hook exists yet in oneagent/agent/core.py |
| 11 | Common LLM runtime provider management shared across agents/threads, usage-aware (Aug 29) | PENDING | Providers exist (OpenAI/Anthropic/Gemini compatible) but no shared runtime manager/usage ledger |
| 12 | Local CLI providers (WSL + non-WSL: gemini cli, claude code) as LLM backends (Aug 29) | PENDING | Not implemented |
| 13 | Tests green | MOSTLY | oneagent: 1 passed. baqa: 41/46 (3 need API keys in `.env`, 1 needs chromadb install, 1 needs both) |
| 14 | Path bug in `baqa/tests/test_all_flows.py` | FIXED this session | `parent` → `parent.parent` |
| 15 | Compose-first / native-capabilities-first directive (Aug 29 "AI OS" session) | NOTED | Recorded here; guides future work on this suite |

## Pending (needs user go-ahead)
1. **Push** One-Agent (merged SuperApp) to GitHub — public or private repo decision.
2. **Delete** old root-level duplicates in One-Agent repo (agent/, core/, src/, server.ts…) — code lives under `oneagent/` + git history.
3. **Scrub + push** AI-Evaluation-automation-system (removes `curemd/cure2000` from public repo).
4. **Generate** `baqa/.env` from central secrets (gitignored, local only) → fixes 3 LLM tests.
5. **Install chromadb** → fixes RAG test (was downloading when timed out).
6. Build items #10–#12 (guardrails, shared provider runtime, CLI providers).
