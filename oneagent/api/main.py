"""
OneAgent FastAPI Application
"""

import os
from typing import Optional

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from oneagent.core.config import OneAgentSettings
from oneagent.core.budget.tracker import BudgetTracker
from oneagent.core.llm.gateway import LLMGateway
from oneagent.core.llm.providers import AIProviderFactory
from oneagent.core.scheduler.tasks import TaskScheduler
from oneagent.core.skills.manager import SkillManager
from oneagent.core.mcp.host import MCPHost
from oneagent.core.profile.manager import ProfileManager
from oneagent.core.auth.manager import AuthManager
from oneagent.core.data.database import init_db
from oneagent.core.logging import get_logger

logger = get_logger("api.main")

# Load settings
settings = OneAgentSettings.from_env()

# Initialize core components
budget = BudgetTracker(
    daily_limit=settings.budget.daily_limit_usd,
    monthly_limit=settings.budget.monthly_limit_usd,
)
gateway = LLMGateway(budget_tracker=budget, fallback_order=settings.llm_fallback_order)
scheduler = TaskScheduler()
skills = SkillManager()
mcp_host = MCPHost()
profile = ProfileManager()
auth = AuthManager()

# Create FastAPI app
app = FastAPI(
    title="OneAgent",
    description="Unified Personal Super-App API",
    version="0.1.0",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Models ---

class AskRequest(BaseModel):
    question: str
    task_class: str = "default"
    provider_hint: Optional[str] = None
    system_prompt: Optional[str] = None


class AskResponse(BaseModel):
    content: str
    model: str
    provider: str
    cost_usd: float
    cached: bool


class AgentRunRequest(BaseModel):
    agent_name: str
    goal: str
    max_iterations: int = 10


class BudgetResponse(BaseModel):
    daily_spent: float
    daily_limit: float
    monthly_spent: float
    monthly_limit: float
    can_spend: bool
    warning_active: bool


class ScheduleJobRequest(BaseModel):
    name: str
    cron_expr: str
    agent_name: str
    task_description: str


# --- Endpoints ---

@app.on_event("startup")
async def startup():
    """Initialize database on startup."""
    init_db()
    logger.info("OneAgent API started")


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": "OneAgent",
        "version": "0.1.0",
        "status": "running",
    }


@app.post("/ask", response_model=AskResponse)
async def ask(request: AskRequest):
    """Quick LLM call."""
    try:
        response = await gateway.generate(
            prompt=request.question,
            system_prompt=request.system_prompt,
            task_class=request.task_class,
            provider_hint=request.provider_hint,
        )
        return AskResponse(
            content=response.content,
            model=response.model,
            provider=response.provider,
            cost_usd=response.cost_usd,
            cached=response.cached,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/budget", response_model=BudgetResponse)
async def get_budget():
    """Get budget status."""
    status = budget.get_status()
    return BudgetResponse(**status.__dict__)


@app.get("/providers")
async def list_providers():
    """List available LLM providers."""
    return {"providers": AIProviderFactory.available_providers()}


@app.get("/skills")
async def list_skills():
    """List loaded skills."""
    return {"skills": [{"name": s.name, "description": s.description} for s in skills.list_skills()]}


@app.get("/schedule")
async def list_scheduled_jobs():
    """List scheduled jobs."""
    jobs = scheduler.list_jobs()
    return {"jobs": [
        {"id": j.id, "name": j.name, "cron": j.cron_expr, "enabled": j.enabled}
        for j in jobs
    ]}


@app.post("/schedule")
async def add_scheduled_job(request: ScheduleJobRequest):
    """Add a scheduled job."""
    job = scheduler.add_job(
        name=request.name,
        cron_expr=request.cron_expr,
        agent_name=request.agent_name,
        task_description=request.task_description,
    )
    return {"id": job.id, "name": job.name}


@app.get("/profile")
async def get_profile():
    """Get user profile."""
    return profile.get_summary()


@app.get("/ranking")
async def get_ranking():
    """Get model rankings."""
    from oneagent.core.llm.router import ModelRouter
    router = ModelRouter()
    return {
        task_class: ranking.models
        for task_class, ranking in router._rankings.items()
    }
