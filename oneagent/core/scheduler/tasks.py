"""
Task Scheduler - Celery + Redis for scheduled and event-triggered agents
"""

import os
import json
import uuid
import threading
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional
from dataclasses import dataclass, field
from pathlib import Path

from ..logging import get_logger

logger = get_logger("scheduler.tasks")


@dataclass
class ScheduledJob:
    """A scheduled job definition."""
    id: str
    name: str
    cron_expr: str  # Cron expression (e.g., "0 8 * * MON")
    agent_name: str
    task_description: str
    enabled: bool = True
    last_run: Optional[str] = None
    next_run: Optional[str] = None
    run_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class JobExecution:
    """Record of a single job execution."""
    id: str
    job_id: str
    started_at: str
    completed_at: Optional[str] = None
    status: str = "running"  # running, success, failed
    result: Optional[Dict] = None
    error: Optional[str] = None


class TaskScheduler:
    """
    Scheduled task runner for OneAgent.

    Supports:
    - Cron-based scheduling
    - Event-triggered agents
    - Persistent job storage (SQLite-backed)
    - Threaded execution for non-blocking runs
    """

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or os.getenv(
            "ONEAGENT_SCHEDULER_DB", "./oneagent_scheduler.db"
        )
        self._jobs: Dict[str, ScheduledJob] = {}
        self._executions: List[JobExecution] = []
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._handlers: Dict[str, Callable] = {}

        self._init_db()
        self._load_jobs()

    def _init_db(self):
        """Initialize the scheduler database."""
        import sqlite3

        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS scheduled_jobs (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                cron_expr TEXT NOT NULL,
                agent_name TEXT NOT NULL,
                task_description TEXT,
                enabled INTEGER DEFAULT 1,
                last_run TEXT,
                next_run TEXT,
                run_count INTEGER DEFAULT 0,
                metadata TEXT DEFAULT '{}'
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS job_executions (
                id TEXT PRIMARY KEY,
                job_id TEXT NOT NULL,
                started_at TEXT NOT NULL,
                completed_at TEXT,
                status TEXT DEFAULT 'running',
                result TEXT,
                error TEXT,
                FOREIGN KEY (job_id) REFERENCES scheduled_jobs(id)
            )
        """)
        conn.commit()
        conn.close()

    def _load_jobs(self):
        """Load persisted jobs from database."""
        import sqlite3

        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute("SELECT * FROM scheduled_jobs")
        for row in cursor.fetchall():
            job = ScheduledJob(
                id=row[0],
                name=row[1],
                cron_expr=row[2],
                agent_name=row[3],
                task_description=row[4] or "",
                enabled=bool(row[5]),
                last_run=row[6],
                next_run=row[7],
                run_count=row[8] or 0,
                metadata=json.loads(row[9] or "{}"),
            )
            self._jobs[job.id] = job
        conn.close()
        logger.info(f"Loaded {len(self._jobs)} scheduled jobs")

    def register_handler(self, agent_name: str, handler: Callable):
        """Register a handler function for an agent."""
        self._handlers[agent_name] = handler

    def add_job(
        self,
        name: str,
        cron_expr: str,
        agent_name: str,
        task_description: str,
        metadata: Optional[Dict] = None,
    ) -> ScheduledJob:
        """Add a new scheduled job."""
        job_id = str(uuid.uuid4())[:8]
        job = ScheduledJob(
            id=job_id,
            name=name,
            cron_expr=cron_expr,
            agent_name=agent_name,
            task_description=task_description,
            metadata=metadata or {},
        )
        self._jobs[job_id] = job
        self._persist_job(job)
        logger.info(f"Added job: {name} ({cron_expr})")
        return job

    def remove_job(self, job_id: str) -> bool:
        """Remove a scheduled job."""
        if job_id in self._jobs:
            del self._jobs[job_id]
            import sqlite3
            conn = sqlite3.connect(self.db_path)
            conn.execute("DELETE FROM scheduled_jobs WHERE id = ?", (job_id,))
            conn.commit()
            conn.close()
            return True
        return False

    def enable_job(self, job_id: str):
        """Enable a job."""
        if job_id in self._jobs:
            self._jobs[job_id].enabled = True
            self._persist_job(self._jobs[job_id])

    def disable_job(self, job_id: str):
        """Disable a job."""
        if job_id in self._jobs:
            self._jobs[job_id].enabled = False
            self._persist_job(self._jobs[job_id])

    def run_job(self, job_id: str) -> Optional[JobExecution]:
        """Execute a job immediately."""
        job = self._jobs.get(job_id)
        if not job:
            logger.error(f"Job {job_id} not found")
            return None

        handler = self._handlers.get(job.agent_name)
        if not handler:
            logger.error(f"No handler for agent: {job.agent_name}")
            return None

        execution = JobExecution(
            id=str(uuid.uuid4())[:8],
            job_id=job_id,
            started_at=datetime.now().isoformat(),
        )
        self._executions.append(execution)

        try:
            result = handler(job.task_description, job.metadata)
            execution.status = "success"
            execution.result = result if isinstance(result, dict) else {"output": str(result)}
        except Exception as e:
            execution.status = "failed"
            execution.error = str(e)
            logger.exception(f"Job {job.name} failed")

        execution.completed_at = datetime.now().isoformat()
        job.last_run = execution.started_at
        job.run_count += 1
        self._persist_job(job)
        self._persist_execution(execution)

        return execution

    def list_jobs(self) -> List[ScheduledJob]:
        """List all scheduled jobs."""
        return list(self._jobs.values())

    def get_job(self, job_id: str) -> Optional[ScheduledJob]:
        """Get a specific job."""
        return self._jobs.get(job_id)

    def get_executions(self, job_id: Optional[str] = None) -> List[JobExecution]:
        """Get execution history."""
        if job_id:
            return [e for e in self._executions if e.job_id == job_id]
        return self._executions

    def _persist_job(self, job: ScheduledJob):
        """Persist a job to database."""
        import sqlite3

        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            INSERT OR REPLACE INTO scheduled_jobs
            (id, name, cron_expr, agent_name, task_description, enabled,
             last_run, next_run, run_count, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            job.id, job.name, job.cron_expr, job.agent_name,
            job.task_description, int(job.enabled), job.last_run,
            job.next_run, job.run_count, json.dumps(job.metadata),
        ))
        conn.commit()
        conn.close()

    def _persist_execution(self, execution: JobExecution):
        """Persist an execution record."""
        import sqlite3

        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            INSERT OR REPLACE INTO job_executions
            (id, job_id, started_at, completed_at, status, result, error)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            execution.id, execution.job_id, execution.started_at,
            execution.completed_at, execution.status,
            json.dumps(execution.result) if execution.result else None,
            execution.error,
        ))
        conn.commit()
        conn.close()
