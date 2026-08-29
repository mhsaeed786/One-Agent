import sys
from rich.console import Console
from rich.prompt import Prompt

from agent.core import SuperAgent
from providers.llm import OpenAICompatibleProvider
from memory.storage import MemorySystem
from tools.scraper import WebScraperTool
from tools.controller import ComputerControllerTool
from tools.graph import GraphAPITool

console = Console()

def main():
    console.print("[bold green]Welcome to Super AI Agent[/bold green] (Goose/Claude Code Alternative)")
    console.print("Initializing continuous memory and learning systems...")

    # Initialize components
    memory = MemorySystem()
    provider = OpenAICompatibleProvider() # Default provider

    agent = SuperAgent(provider=provider, memory_system=memory)

    # Add tools
    agent.add_tool(WebScraperTool())
    agent.add_tool(ComputerControllerTool())
    agent.add_tool(GraphAPITool())

    console.print("[bold blue]Agent is ready. Type 'exit' or 'quit' to stop.[/bold blue]\n")

    while True:
        try:
            user_input = Prompt.ask("[bold magenta]You[/bold magenta]")

            if user_input.strip().lower() in ['exit', 'quit']:
                console.print("[bold blue]Shutting down agent. Memory saved.[/bold blue]")
                break

            # Process with agent
            response = agent.process_input(user_input)

            # Print response
            console.print(f"[bold cyan]Agent:[/bold cyan] {response}\n")

        except KeyboardInterrupt:
            console.print("\n[bold blue]Shutting down agent. Memory saved.[/bold blue]")
            break
        except Exception as e:
            console.print(f"[bold red]Error:[/bold red] {str(e)}")

if __name__ == "__main__":
    main()
