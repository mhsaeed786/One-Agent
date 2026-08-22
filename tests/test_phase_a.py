"""
Phase A Tests - Verify all core components work
"""

import pytest
import os
import tempfile
import time


# =============================================================================
# Config Tests
# =============================================================================

class TestConfig:
    """Test configuration loading."""

    def test_default_settings(self):
        from oneagent.core.config import OneAgentSettings
        settings = OneAgentSettings()
        assert settings.log_level == "INFO"
        assert settings.default_llm.provider == "openai"
        assert settings.budget.daily_limit_usd == 10.0

    def test_from_env(self):
        from oneagent.core.config import OneAgentSettings
        settings = OneAgentSettings.from_env()
        assert settings is not None
        assert settings.budget.daily_limit_usd > 0


# =============================================================================
# Cache Tests
# =============================================================================

class TestCache:
    """Test SQLite cache."""

    def _make_cache(self):
        from oneagent.core.llm.cache import SQLiteCache
        db_path = os.path.join(tempfile.gettempdir(), f"test_cache_{os.getpid()}.db")
        return SQLiteCache(db_path=db_path), db_path

    def test_set_and_get(self):
        cache, db_path = self._make_cache()
        try:
            cache.set("test_key", {"content": "hello"})
            result = cache.get("test_key")
            assert result == {"content": "hello"}
        finally:
            cache._conn.close()
            try:
                os.unlink(db_path)
            except Exception:
                pass

    def test_miss(self):
        cache, db_path = self._make_cache()
        try:
            result = cache.get("nonexistent")
            assert result is None
        finally:
            cache._conn.close()
            try:
                os.unlink(db_path)
            except Exception:
                pass

    def test_clear_all(self):
        cache, db_path = self._make_cache()
        try:
            cache.set("key1", "val1")
            cache.set("key2", "val2")
            cache.clear_all()
            assert cache.get("key1") is None
            assert cache.get("key2") is None
        finally:
            cache._conn.close()
            try:
                os.unlink(db_path)
            except Exception:
                pass


# =============================================================================
# Budget Tests
# =============================================================================

class TestBudget:
    """Test budget tracker."""

    def _make_budget(self):
        from oneagent.core.budget.tracker import BudgetTracker
        from oneagent.core.llm.cache import SQLiteCache
        db_path = os.path.join(tempfile.gettempdir(), f"test_budget_{os.getpid()}.db")
        cache = SQLiteCache(db_path=db_path)
        return BudgetTracker(
            daily_limit=10.0, monthly_limit=100.0,
            cache_db=cache,
        ), cache, db_path

    def test_can_spend(self):
        budget, cache, db_path = self._make_budget()
        try:
            assert budget.can_spend(1.0) is True
            assert budget.can_spend(100.0) is False
        finally:
            cache._conn.close()
            try:
                os.unlink(db_path)
            except Exception:
                pass

    def test_record_usage(self):
        budget, cache, db_path = self._make_budget()
        try:
            budget.record_usage(0.05, {"prompt_tokens": 100, "completion_tokens": 50}, "openai", "gpt-4")
            status = budget.get_status()
            assert status.daily_spent == pytest.approx(0.05, abs=0.001)
        finally:
            cache._conn.close()
            try:
                os.unlink(db_path)
            except Exception:
                pass

    def test_usage_breakdown(self):
        budget, cache, db_path = self._make_budget()
        try:
            budget.record_usage(0.01, {"prompt_tokens": 100, "completion_tokens": 50}, "openai", "gpt-4")
            budget.record_usage(0.02, {"prompt_tokens": 200, "completion_tokens": 100}, "anthropic", "claude-3")
            breakdown = budget.get_usage_breakdown()
            assert "openai/gpt-4" in breakdown
            assert "anthropic/claude-3" in breakdown
        finally:
            cache._conn.close()
            try:
                os.unlink(db_path)
            except Exception:
                pass


# =============================================================================
# Memory Tests
# =============================================================================

class TestMemory:
    """Test memory components."""

    def test_short_term_add_and_retrieve(self):
        from oneagent.core.memory.short_term import ShortTermMemory
        mem = ShortTermMemory()
        mem.add("user", "Hello")
        mem.add("assistant", "Hi there!")
        messages = mem.to_llm_format()
        assert len(messages) == 2
        assert messages[0]["role"] == "user"
        assert messages[0]["content"] == "Hello"

    def test_short_term_max_messages(self):
        from oneagent.core.memory.short_term import ShortTermMemory
        mem = ShortTermMemory(max_messages=3)
        for i in range(5):
            mem.add("user", f"Message {i}")
        assert len(mem) == 3

    def test_long_term_add_and_search(self):
        from oneagent.core.memory.long_term import LongTermMemory
        ltm = LongTermMemory()
        ltm.add("FHIR Patient resource has id, name, and birthDate fields")
        ltm.add("LEAP UDS reporting requires annual submission")
        results = ltm.search("FHIR")
        assert len(results) > 0


# =============================================================================
# Tool Registry Tests
# =============================================================================

class TestToolRegistry:
    """Test tool registry."""

    def test_register_and_execute(self):
        from oneagent.core.tools.registry import ToolRegistry
        registry = ToolRegistry()

        @registry.register(name="add_numbers", description="Add two numbers")
        def add_numbers(a: int, b: int) -> int:
            return a + b

        import asyncio
        result = asyncio.run(registry.execute("add_numbers", {"a": 3, "b": 4}))
        assert result == 7

    def test_tool_not_found(self):
        from oneagent.core.tools.registry import ToolRegistry, ToolNotFoundError
        registry = ToolRegistry()
        import asyncio
        with pytest.raises(ToolNotFoundError):
            asyncio.run(registry.execute("nonexistent", {}))

    def test_builtin_tools_registered(self):
        import oneagent.core.tools.builtins  # Triggers registration
        from oneagent.core.tools.registry import get_registry
        registry = get_registry()
        assert registry.has_tool("calculator")
        assert registry.has_tool("echo")

    def test_calculator_tool(self):
        import oneagent.core.tools.builtins  # Triggers registration
        from oneagent.core.tools.registry import get_registry
        registry = get_registry()
        import asyncio
        result = asyncio.run(registry.execute("calculator", {"expression": "2 + 2"}))
        assert result == "4"


# =============================================================================
# Provider Tests
# =============================================================================

class TestProviders:
    """Test LLM provider registration."""

    def test_available_providers(self):
        from oneagent.core.llm.providers import AIProviderFactory
        providers = AIProviderFactory.available_providers()
        assert "openai" in providers
        assert "anthropic" in providers
        assert "ollama" in providers
        assert "gemini" in providers

    def test_create_provider(self):
        from oneagent.core.llm.providers import AIProviderFactory
        provider = AIProviderFactory.create("openai", api_key="test-key")
        assert provider.model == "gpt-4"

    def test_unknown_provider(self):
        from oneagent.core.llm.providers import AIProviderFactory
        with pytest.raises(ValueError):
            AIProviderFactory.create("unknown_provider")


# =============================================================================
# Router Tests
# =============================================================================

class TestRouter:
    """Test model router."""

    def test_default_ranking(self):
        from oneagent.core.llm.router import ModelRouter
        router = ModelRouter()
        models = router.get_models("classify")
        assert len(models) > 0
        assert "gpt-3.5-turbo" in models

    def test_provider_fallback(self):
        from oneagent.core.llm.router import ModelRouter
        router = ModelRouter()
        providers = router.get_providers("openai")
        assert providers[0] == "openai"
        assert len(providers) > 1

    def test_custom_provider_hint(self):
        from oneagent.core.llm.router import ModelRouter
        router = ModelRouter()
        providers = router.get_providers(provider_hint="gemini")
        assert providers[0] == "gemini"


# =============================================================================
# RAG Tests
# =============================================================================

class TestRAG:
    """Test RAG store (in-memory fallback)."""

    def test_fallback_add_and_query(self):
        from oneagent.core.rag.chroma_store import ChromaStore, Document
        store = ChromaStore(
            collection_name="test_collection",
            persist_directory=os.path.join(tempfile.gettempdir(), f"chroma_test_{os.getpid()}"),
        )
        store.add([
            Document(id="doc1", content="FHIR Patient resource definition", metadata={"source": "test"}),
            Document(id="doc2", content="LEAP UDS reporting guide", metadata={"source": "test"}),
        ])
        results = store.query("FHIR")
        assert len(results) > 0

    def test_add_text(self):
        from oneagent.core.rag.chroma_store import ChromaStore
        store = ChromaStore(
            collection_name="test_single",
            persist_directory=os.path.join(tempfile.gettempdir(), f"chroma_test2_{os.getpid()}"),
        )
        doc_id = store.add_text("This is a test document about healthcare")
        assert doc_id is not None


# =============================================================================
# Scheduler Tests
# =============================================================================

class TestScheduler:
    """Test task scheduler."""

    def _make_scheduler(self):
        from oneagent.core.scheduler.tasks import TaskScheduler
        db_path = os.path.join(tempfile.gettempdir(), f"test_sched_{os.getpid()}.db")
        return TaskScheduler(db_path=db_path), db_path

    def test_add_job(self):
        scheduler, db_path = self._make_scheduler()
        try:
            job = scheduler.add_job(
                name="test_job",
                cron_expr="0 8 * * MON",
                agent_name="fhir",
                task_description="Run FHIR audit",
            )
            assert job.name == "test_job"
            assert job.enabled is True
        finally:
            try:
                os.unlink(db_path)
            except Exception:
                pass

    def test_list_jobs(self):
        scheduler, db_path = self._make_scheduler()
        try:
            scheduler.add_job("job1", "0 8 * * *", "agent1", "Task 1")
            scheduler.add_job("job2", "0 9 * * *", "agent2", "Task 2")
            jobs = scheduler.list_jobs()
            assert len(jobs) == 2
        finally:
            try:
                os.unlink(db_path)
            except Exception:
                pass


# =============================================================================
# Skills Tests
# =============================================================================

class TestSkills:
    """Test skill manager."""

    def test_empty_skills_dir(self):
        from oneagent.core.skills.manager import SkillManager
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = SkillManager(skills_dir=tmpdir)
            skills = manager.list_skills()
            assert len(skills) == 0


# =============================================================================
# Meta Tests
# =============================================================================

class TestMeta:
    """Test meta registry."""

    def _make_registry(self):
        from oneagent.core.meta.registry import MetaRegistry
        path = os.path.join(tempfile.gettempdir(), f"test_meta_{os.getpid()}.json")
        return MetaRegistry(registry_path=path), path

    def test_register_and_list(self):
        from oneagent.core.meta.registry import ModuleRecord
        registry, path = self._make_registry()
        try:
            record = ModuleRecord(
                name="test_module",
                description="A test module",
                status="draft",
                source_prompt="write a test module",
                model_used="gpt-4",
                created_at="2024-01-01T00:00:00",
            )
            registry.register(record)
            modules = registry.list_modules()
            assert len(modules) == 1
            assert modules[0].name == "test_module"
        finally:
            try:
                os.unlink(path)
            except Exception:
                pass

    def test_approve_module(self):
        from oneagent.core.meta.registry import ModuleRecord
        registry, path = self._make_registry()
        try:
            record = ModuleRecord(
                name="approve_test",
                description="Test approval",
                status="testing",
                source_prompt="test",
                model_used="gpt-4",
                created_at="2024-01-01T00:00:00",
            )
            registry.register(record)
            assert registry.approve("approve_test") is True
            assert registry.get("approve_test").status == "active"
        finally:
            try:
                os.unlink(path)
            except Exception:
                pass


# =============================================================================
# Profile Tests
# =============================================================================

class TestProfile:
    """Test profile manager."""

    def _make_profile(self):
        from oneagent.core.profile.manager import ProfileManager
        path = os.path.join(tempfile.gettempdir(), f"test_profile_{os.getpid()}.json")
        return ProfileManager(profile_path=path), path

    def test_default_profile(self):
        manager, path = self._make_profile()
        try:
            summary = manager.get_summary()
            assert "name" in summary
        finally:
            try:
                os.unlink(path)
            except Exception:
                pass

    def test_update_profile(self):
        manager, path = self._make_profile()
        try:
            manager.update(name="Hassan", role="FHIR BA/QA")
            assert manager.profile.name == "Hassan"
            assert manager.profile.role == "FHIR BA/QA"
        finally:
            try:
                os.unlink(path)
            except Exception:
                pass


# =============================================================================
# Auth Tests
# =============================================================================

class TestAuth:
    """Test auth manager."""

    def test_register_and_authenticate(self):
        from oneagent.core.auth.manager import AuthManager
        auth = AuthManager()
        key = auth.generate_api_key("testuser")
        user = auth.authenticate(key)
        assert user is not None
        assert user.username == "testuser"

    def test_invalid_key(self):
        from oneagent.core.auth.manager import AuthManager
        auth = AuthManager()
        user = auth.authenticate("invalid_key")
        assert user is None
