<div align="center">
<img width="1200" height="475" alt="GHBanner" src="https://ai.google.dev/static/site-assets/images/share-ais-513315318.png" />
</div>

# Run and deploy your AI Studio app

This contains everything you need to run your app locally.

View your app in AI Studio: https://ai.studio/apps/dec9d92d-3e27-4b75-bc7b-de0b1c193fb3

## Run Locally

**Prerequisites:**  Node.js


1. Install dependencies:
   `npm install`
2. Set the `GEMINI_API_KEY` in [.env.local](.env.local) to your Gemini API key
3. Run the app:
   `npm run dev`
# Super AI Agent Framework

A highly capable, extensible, and open-source alternative to AI agent CLI tools like Goose, Claude Code, and OpenManus. This framework provides the scaffolding for a "do-it-all" agent capable of continuous memory, tool use, and multi-provider LLM support.

## Features

- **Multi-Provider Support**: Natively supports any model compatible with the OpenAI, Anthropic, or Gemini API formats. Relies only on standard Python `requests` for lightweight, dependency-free provider integration.
- **Continuous Memory**: Includes a JSON-backed memory storage system (`memory.json`) that saves conversation history and context across sessions, providing the foundation for neurosymbolic learning and user preference adaptation.
- **Extensible Tool Harness**: Easily create and register new tools. Includes skeleton tools out of the box:
  - **Web Scraper**: Built with `beautifulsoup4` for scraping website data (similar to Firecrawl).
  - **Computer Controller**: Safely executes local OS commands (similar to OpenManus, restricted to a safe whitelist to prevent arbitrary code execution).
  - **Graph API Integration**: Skeleton for fetching Microsoft Graph API data (mail, calendar, teams).
- **CLI Interface**: A rich, beautiful command-line interface powered by the `rich` library.

## Prerequisites

- Python 3.8+

## Installation

1. Clone this repository or download the source code.
2. Install the required dependencies:

```bash
pip install -r requirements.txt
```

## Configuration

Set the API keys for the LLM providers you wish to use as environment variables.

For OpenAI (or compatible endpoints like vLLM, Groq, Ollama):
```bash
export OPENAI_API_KEY="your-openai-key-here"
```

For Anthropic:
```bash
export ANTHROPIC_API_KEY="your-anthropic-key-here"
```

For Gemini:
```bash
export GEMINI_API_KEY="your-gemini-key-here"
```

## Usage

Run the main application to start the interactive CLI agent loop:

```bash
python main.py
```

To run the basic smoke test to ensure the agent loop and tools are functioning:

```bash
python test_main.py
```

## Architecture

OneAgent is a full-stack agent app: a React dashboard (Vite) talks to an Express API server (`server.ts`), which drives a Python agent core.

### Components

- **Agent core** (`agent/core.py` + `core/agent/`): the `SuperAgent` plan → tool → observe loop. Tool results are structured JSON envelopes (`{status: 'ok'|'error', data}`) so the loop can react to failures; each iteration is logged (tool name, args summary, duration) at DEBUG. Tool loops are capped at 10 iterations.
- **Tools** (`tools/`, `core/tools/`): web scraper, computer controller, Graph API integration, Tavily search, MCP client. Registered on the agent with generated function-call schemas.
- **Providers** (`providers/llm.py`, `core/llm/`): lightweight wrappers for OpenAI-compatible, Anthropic, and Gemini APIs. All HTTP calls carry a provider-level timeout (30s); API failures raise `ProviderError` instead of masquerading as model output.
- **Server** (`server.ts`): Express API gateway serving the dashboard and Python bridge. Request validation middleware rejects non-JSON content types, bodies over 1 MB, and non-object JSON with `400`. A central error middleware returns `{error: 'internal error', correlationId}` — details are logged server-side only.
- **Dashboard** (`src/`): React/Vite UI (chat workspace, agent runner, skills, scheduler, observability panels).
- **Memory** (`memory/storage.py`): append-only JSONL store — one line per interaction; reads aggregate only the last 500 entries (no full-file rewrite per message).

### Environment variables

| Variable | Used by | Purpose |
| --- | --- | --- |
| `HOST` | server.ts | Bind address (default: `127.0.0.1`) |
| `GEMINI_API_KEY` | server.ts, providers | Google Gemini API key |
| `OPENAI_API_KEY` | providers/llm.py | OpenAI / OpenAI-compatible key |
| `ANTHROPIC_API_KEY` | providers/llm.py | Anthropic API key |
| `NODE_ENV` | server.ts | `production` serves static `dist/`; otherwise Vite dev middleware |

No `AUTH_TOKEN` is required; the server binds to localhost by default.

## Quickstart

```bash
# 1. Install dependencies
npm install
pip install -r requirements.txt

# 2. Configure keys (.env or environment)
export GEMINI_API_KEY="your-gemini-key"

# 3. Run the web app (server + dashboard)
npm run dev            # http://127.0.0.1:3000

# Or run the CLI agent only
python main.py

# Smoke test
python test_main.py
```