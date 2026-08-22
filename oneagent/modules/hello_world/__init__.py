"""
Hello World Module - Phase A Smoke Test
=======================================
This module verifies that the core runtime is working correctly.
"""

import asyncio
from oneagent.core import (
    OneAgentSettings,
    LLMGateway,
    AgentLoop,
    ToolRegistry,
    ShortTermMemory,
    BudgetTracker,
)


async def smoke_test():
    """
    Run smoke test to verify Phase A core runtime.
    """
    print("=" * 60)
    print("OneAgent Phase A - Smoke Test")
    print("=" * 60)

    # 1. Load settings
    print("\n[1/5] Loading settings...")
    settings = OneAgentSettings.from_env()
    print(f"     Provider: {settings.default_llm.provider}")
    print(f"     Model: {settings.default_llm.model}")
    print(f"     Daily budget: ${settings.budget.daily_limit_usd}")

    # 2. Initialize budget tracker
    print("\n[2/5] Initializing budget tracker...")
    budget = BudgetTracker(
        daily_limit=settings.budget.daily_limit_usd,
        monthly_limit=settings.budget.monthly_limit_usd,
        warn_at_percent=settings.budget.warn_at_percent,
    )
    print(f"     Daily limit: ${budget.daily_limit}")
    print(f"     Can spend $1: {budget.can_spend(1.0)}")

    # 3. Initialize LLM gateway
    print("\n[3/5] Initializing LLM gateway...")
    gateway = LLMGateway(
        budget_tracker=budget,
        fallback_order=settings.llm_fallback_order,
    )
    print("     Gateway initialized")

    # 4. Initialize tool registry
    print("\n[4/5] Initializing tool registry...")
    from oneagent.core.tools.builtins import (
        calculator, read_file, write_file, search,
        grep, json_parse, json_query, echo,
    )
    registry = ToolRegistry()

    # Register builtins
    registry.register("calculator", calculator.__doc__ or "")(calculator)
    registry.register("echo", echo.__doc__ or "")(echo)

    tool_names = registry.get_tool_names()
    print(f"     Registered tools: {tool_names}")

    # 5. Initialize agent loop
    print("\n[5/5] Initializing agent loop...")
    from oneagent.core.agent import AgentConfig
    config = AgentConfig(
        name="hello_world",
        model=settings.default_llm.model,
        provider=settings.default_llm.provider,
        max_iterations=5,
    )
    conversation = ShortTermMemory()
    agent = AgentLoop(config, gateway, registry, conversation)
    print("     Agent loop initialized")

    print("\n" + "=" * 60)
    print("All core components initialized successfully!")
    print("=" * 60)

    # Run a simple test
    print("\n--- Running Simple Test ---")
    try:
        result = await agent.run("Use the calculator tool to compute 15 * 23")
        print(f"\nResult: {result}")
        print(f"Success: {result.get('success')}")
        if result.get('steps'):
            print(f"Steps taken: {len(result['steps'])}")
    except Exception as e:
        print(f"\nTest error (expected if no API keys): {e}")

    # Show budget status
    print("\n--- Budget Status ---")
    status = budget.get_status()
    print(f"Daily spent: ${status.daily_spent:.4f} / ${status.daily_limit}")
    print(f"Monthly spent: ${status.monthly_spent:.4f} / ${status.monthly_limit}")
    print(f"Can spend: {status.can_spend}")

    print("\n" + "=" * 60)
    print("Smoke test complete!")
    print("=" * 60)

    return True


if __name__ == "__main__":
    asyncio.run(smoke_test())