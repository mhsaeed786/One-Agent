"""
Module Author - Generates new modules on demand
"""

import os
import uuid
import json
from datetime import datetime
from typing import Any, Dict, Optional
from dataclasses import dataclass

from ..logging import get_logger

logger = get_logger("meta.module_author")


@dataclass
class AuthoredModule:
    """A self-authored module."""
    id: str
    name: str
    description: str
    source_prompt: str
    model_used: str
    created_at: str
    code: str
    tests: str
    status: str = "draft"  # draft, testing, approved, rejected, active
    test_results: Optional[Dict] = None
    review_notes: str = ""


class ModuleAuthor:
    """
    Self-extension engine for OneAgent.

    When existing skills/tools can't handle a task, this agent:
    1. Drafts a new Python module
    2. Writes tests for it
    3. Runs tests in an isolated environment
    4. Registers the module if tests pass
    """

    def __init__(self, modules_dir: Optional[str] = None):
        self.modules_dir = modules_dir or os.getenv(
            "ONEAGENT_MODULES_DIR",
            os.path.join(os.path.dirname(__file__), "..", "..", "modules"),
        )
        self._llm_gateway = None

    def set_llm_gateway(self, gateway):
        """Set the LLM gateway for code generation."""
        self._llm_gateway = gateway

    async def propose_module(
        self,
        task_description: str,
        context: Optional[Dict] = None,
    ) -> AuthoredModule:
        """
        Propose a new module based on a task description.

        This generates the module code and tests but does NOT register it.
        The user must review and approve.
        """
        if not self._llm_gateway:
            raise RuntimeError("LLM gateway not set. Call set_llm_gateway() first.")

        module_id = str(uuid.uuid4())[:8]
        module_name = self._infer_module_name(task_description)

        logger.info(f"Proposing module: {module_name} (id={module_id})")

        # Generate module code
        code_prompt = self._build_code_prompt(module_name, task_description, context)
        code_response = await self._llm_gateway.generate(
            prompt=code_prompt,
            system_prompt=self._CODE_SYSTEM_PROMPT,
            task_class="code",
        )

        # Generate tests
        test_prompt = self._build_test_prompt(module_name, code_response.content)
        test_response = await self._llm_gateway.generate(
            prompt=test_prompt,
            system_prompt=self._TEST_SYSTEM_PROMPT,
            task_class="code",
        )

        module = AuthoredModule(
            id=module_id,
            name=module_name,
            description=task_description,
            source_prompt=task_description,
            model_used=code_response.model,
            created_at=datetime.now().isoformat(),
            code=code_response.content,
            tests=test_response.content,
            status="draft",
        )

        return module

    async def test_module(self, module: AuthoredModule) -> Dict[str, Any]:
        """
        Run tests for a proposed module in isolation.

        Returns test results.
        """
        import tempfile
        import subprocess

        module_dir = os.path.join(tempfile.gettempdir(), f"oneagent_test_{module.id}")
        os.makedirs(module_dir, exist_ok=True)

        # Write module code
        code_path = os.path.join(module_dir, f"{module.name}.py")
        with open(code_path, "w") as f:
            # Strip markdown code fences if present
            code = module.code
            if code.startswith("```python"):
                code = code[len("```python"):]
            if code.startswith("```"):
                code = code[3:]
            if code.endswith("```"):
                code = code[:-3]
            f.write(code.strip())

        # Write test code
        test_path = os.path.join(module_dir, f"test_{module.name}.py")
        with open(test_path, "w") as f:
            tests = module.tests
            if tests.startswith("```python"):
                tests = tests[len("```python"):]
            if tests.startswith("```"):
                tests = tests[3:]
            if tests.endswith("```"):
                tests = tests[:-3]
            f.write(tests.strip())

        # Run tests
        try:
            result = subprocess.run(
                ["python", "-m", "pytest", test_path, "-v", "--tb=short"],
                capture_output=True,
                text=True,
                timeout=60,
                cwd=module_dir,
            )

            test_results = {
                "success": result.returncode == 0,
                "returncode": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
            }

            module.test_results = test_results
            module.status = "testing"

            if test_results["success"]:
                logger.info(f"Module {module.name} tests passed")
            else:
                logger.warning(f"Module {module.name} tests failed")

            return test_results

        except subprocess.TimeoutExpired:
            error_msg = "Test execution timed out (60s)"
            module.test_results = {"success": False, "error": error_msg}
            module.status = "testing"
            return module.test_results

        except Exception as e:
            error_msg = f"Test execution failed: {e}"
            module.test_results = {"success": False, "error": error_msg}
            module.status = "testing"
            return module.test_results

    async def approve_module(self, module: AuthoredModule) -> bool:
        """
        Approve and register a tested module.
        Writes it to the modules directory with a manifest.
        """
        if module.status not in ("testing", "draft"):
            logger.error(f"Cannot approve module in status: {module.status}")
            return False

        module_dir = os.path.join(self.modules_dir, module.name)
        os.makedirs(module_dir, exist_ok=True)

        # Write module code
        code_path = os.path.join(module_dir, "__init__.py")
        code = module.code
        if code.startswith("```python"):
            code = code[len("```python"):]
        if code.endswith("```"):
            code = code[:-3]
        with open(code_path, "w") as f:
            f.write(code.strip())

        # Write tests
        test_path = os.path.join(module_dir, "test_module.py")
        tests = module.tests
        if tests.startswith("```python"):
            tests = tests[len("```python"):]
        if tests.endswith("```"):
            tests = tests[:-3]
        with open(test_path, "w") as f:
            f.write(tests.strip())

        # Write manifest
        manifest = {
            "name": module.name,
            "description": module.description,
            "version": "0.1.0",
            "author": "oneagent-meta",
            "created_at": module.created_at,
            "source_prompt": module.source_prompt,
            "model_used": module.model_used,
            "test_results": module.test_results,
            "status": "active",
        }
        manifest_path = os.path.join(module_dir, "manifest.json")
        with open(manifest_path, "w") as f:
            json.dump(manifest, f, indent=2)

        module.status = "active"
        logger.info(f"Approved module: {module.name}")
        return True

    def reject_module(self, module: AuthoredModule, reason: str = ""):
        """Reject a proposed module."""
        module.status = "rejected"
        module.review_notes = reason

    def _infer_module_name(self, description: str) -> str:
        """Infer a module name from the description."""
        # Take first few meaningful words
        words = description.lower().split()
        # Filter out common stop words
        stop_words = {"a", "an", "the", "that", "this", "to", "for", "is", "are", "of", "in", "it"}
        meaningful = [w for w in words[:10] if w not in stop_words]
        name = "_".join(meaningful[:3])
        # Clean up
        name = "".join(c if c.isalnum() or c == "_" else "" for c in name)
        return name or "custom_module"

    def _build_code_prompt(self, name: str, description: str, context: Optional[Dict]) -> str:
        return f"""Generate a Python module named '{name}' for the following task:

{description}

{f"Context: {json.dumps(context)}" if context else ""}

Requirements:
1. The module should be self-contained in a single file
2. Include proper type hints
3. Include docstrings
4. Handle errors gracefully
5. Follow Python best practices

Output ONLY the Python code, no markdown fences."""

    def _build_test_prompt(self, name: str, code: str) -> str:
        return f"""Write pytest tests for this Python module:

```python
{code}
```

Requirements:
1. Test all public functions
2. Include edge cases
3. Use pytest fixtures where appropriate
4. Tests should be self-contained (no external dependencies)

Output ONLY the Python test code, no markdown fences."""

    _CODE_SYSTEM_PROMPT = (
        "You are a Python code generator. Generate clean, well-documented, "
        "production-ready Python code. Follow PEP 8. Include proper type hints "
        "and docstrings. Handle errors gracefully."
    )

    _TEST_SYSTEM_PROMPT = (
        "You are a Python test writer. Write comprehensive pytest tests. "
        "Include edge cases and error scenarios. Tests should be self-contained."
    )
