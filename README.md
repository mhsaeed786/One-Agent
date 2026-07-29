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

- `main.py`: The CLI entrypoint.
- `agent/core.py`: Contains the `SuperAgent` class, which handles the core execution loop, tool invocation, and memory integration.
- `providers/llm.py`: Contains the simplified API wrappers for OpenAI, Anthropic, and Gemini.
- `memory/storage.py`: Contains the `MemorySystem` for saving and loading interaction history.
- `tools/`: Directory containing all agent tools.