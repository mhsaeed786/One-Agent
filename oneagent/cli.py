"""
OneAgent CLI - Command-line interface
"""

import argparse
import asyncio
import json
import sys
from pathlib import Path


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        prog="oneagent",
        description="OneAgent - Unified Personal Super-App",
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # ask command
    ask_parser = subparsers.add_parser("ask", help="Ask a question (quick LLM call)")
    ask_parser.add_argument("question", help="Question to ask")
    ask_parser.add_argument("--task", default="default", help="Task class (classify, extract, reason, code)")
    ask_parser.add_argument("--provider", default=None, help="Provider hint")
    ask_parser.add_argument("--model", default=None, help="Model override")

    # run-agent command
    agent_parser = subparsers.add_parser("run-agent", help="Run an agent with tools")
    agent_parser.add_argument("agent_name", help="Agent to run")
    agent_parser.add_argument("goal", help="Goal for the agent")
    agent_parser.add_argument("--max-iter", type=int, default=10, help="Max iterations")

    # budget command
    subparsers.add_parser("budget", help="Show budget status")

    # smoke-test command
    subparsers.add_parser("smoke-test", help="Run Phase A smoke test")

    # providers command
    subparsers.add_parser("providers", help="List available LLM providers")

    # ranking command
    ranking_parser = subparsers.add_parser("ranking", help="Show or edit model rankings")
    ranking_parser.add_argument("--task", default=None, help="Show ranking for task class")

    # schedule command
    schedule_parser = subparsers.add_parser("schedule", help="Manage scheduled jobs")
    schedule_parser.add_argument("--list", action="store_true", help="List jobs")

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        return

    if args.command == "smoke-test":
        asyncio.run(_run_smoke_test())
    elif args.command == "ask":
        asyncio.run(_ask(args))
    elif args.command == "run-agent":
        asyncio.run(_run_agent(args))
    elif args.command == "budget":
        _show_budget()
    elif args.command == "providers":
        _show_providers()
    elif args.command == "ranking":
        _show_ranking(args)
    elif args.command == "schedule":
        _show_schedule(args)
    else:
        parser.print_help()


async def _run_smoke_test():
    """Run the Phase A smoke test."""
    from oneagent.modules.hello_world import smoke_test
    await smoke_test()


async def _ask(args):
    """Quick LLM call."""
    from oneagent.core.config import OneAgentSettings
    from oneagent.core.budget.tracker import BudgetTracker
    from oneagent.core.llm.gateway import LLMGateway

    settings = OneAgentSettings.from_env()
    budget = BudgetTracker(
        daily_limit=settings.budget.daily_limit_usd,
        monthly_limit=settings.budget.monthly_limit_usd,
    )
    gateway = LLMGateway(budget_tracker=budget, fallback_order=settings.llm_fallback_order)

    try:
        response = await gateway.generate(
            prompt=args.question,
            task_class=args.task,
            provider_hint=args.provider,
        )
        print(f"\n{response.content}")
        print(f"\n[provider={response.provider} model={response.model} "
              f"cost=${response.cost_usd:.6f} cached={response.cached}]")
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


async def _run_agent(args):
    """Run an agent."""
    from oneagent.core.config import OneAgentSettings
    from oneagent.core.budget.tracker import BudgetTracker
    from oneagent.core.llm.gateway import LLMGateway
    from oneagent.core.agent.loop import AgentLoop
    from oneagent.core.agent.types import AgentConfig
    from oneagent.core.tools.registry import ToolRegistry
    from oneagent.core.tools.builtins import register_builtin_tools
    from oneagent.core.memory.short_term import ShortTermMemory
    import oneagent.core.tools.builtins  # noqa: triggers decorator registrations

    settings = OneAgentSettings.from_env()
    budget = BudgetTracker(
        daily_limit=settings.budget.daily_limit_usd,
        monthly_limit=settings.budget.monthly_limit_usd,
    )
    gateway = LLMGateway(budget_tracker=budget, fallback_order=settings.llm_fallback_order)
    registry = ToolRegistry()

    config = AgentConfig(
        name=args.agent_name,
        max_iterations=args.max_iter,
    )
    agent = AgentLoop(config, gateway, registry, ShortTermMemory())

    result = await agent.run(args.goal)
    print(json.dumps(result, indent=2, default=str))


def _show_budget():
    """Show budget status."""
    from oneagent.core.config import OneAgentSettings
    from oneagent.core.budget.tracker import BudgetTracker

    settings = OneAgentSettings.from_env()
    budget = BudgetTracker(
        daily_limit=settings.budget.daily_limit_usd,
        monthly_limit=settings.budget.monthly_limit_usd,
    )

    status = budget.get_status()
    breakdown = budget.get_usage_breakdown()

    print("Budget Status:")
    print(f"  Daily:   ${status.daily_spent:.4f} / ${status.daily_limit}")
    print(f"  Monthly: ${status.monthly_spent:.4f} / ${status.monthly_limit}")
    print(f"  Can spend: {status.can_spend}")
    print(f"  Warning: {'YES' if status.warning_active else 'no'}")

    if breakdown:
        print("\nBreakdown:")
        for key, data in breakdown.items():
            print(f"  {key}: ${data['cost']:.4f} ({data['requests']} requests)")


def _show_providers():
    """List available providers."""
    from oneagent.core.llm.providers import AIProviderFactory

    providers = AIProviderFactory.available_providers()
    print("Available LLM providers:")
    for p in providers:
        print(f"  - {p}")


def _show_ranking(args):
    """Show model rankings."""
    from oneagent.core.llm.router import ModelRouter

    router = ModelRouter()

    if args.task:
        models = router.get_models(args.task)
        print(f"Ranking for '{args.task}':")
        for i, m in enumerate(models, 1):
            print(f"  {i}. {m}")
    else:
        for task_class in router._rankings:
            models = router._rankings[task_class].models
            print(f"\n{task_class}:")
            for i, m in enumerate(models, 1):
                print(f"  {i}. {m}")


def _show_schedule(args):
    """Show scheduled jobs."""
    from oneagent.core.scheduler.tasks import TaskScheduler

    scheduler = TaskScheduler()
    jobs = scheduler.list_jobs()

    if not jobs:
        print("No scheduled jobs.")
        return

    print(f"Scheduled jobs ({len(jobs)}):")
    for job in jobs:
        status = "enabled" if job.enabled else "disabled"
        print(f"  [{job.id}] {job.name} ({status}) cron={job.cron_expr} "
              f"agent={job.agent_name} runs={job.run_count}")


if __name__ == "__main__":
    main()
