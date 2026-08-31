"""Ingest loop — the Mind's heartbeat.

Poll every sense -> absorb experiences -> extract entities -> grow the graph.
Run once, or forever on an interval (the infinite learning loop).
"""
from __future__ import annotations

import time
import logging
from typing import Callable, List

from .store import ExperienceStore
from .graph import KnowledgeGraph
from . import discover_sensors

logger = logging.getLogger("mind.ingest")


def ingest_once(store: ExperienceStore = None, graph: KnowledgeGraph = None,
                engine: "AnticipationEngine" = None) -> dict:
    """One heartbeat: all senses -> store -> graph -> anticipation."""
    from .permissions import PermissionGate
    store = store or ExperienceStore()
    graph = graph or KnowledgeGraph()
    gate = PermissionGate()
    report = {"senses": {}, "absorbed": 0, "dupes": 0, "graph_folded": 0,
              "proposals": [], "ts": time.time()}

    allowed = gate.allowed_senses()
    sensors = discover_sensors()
    for sensor in sensors:
        # CONSENT GATE: a sense only polls if the user granted permission.
        # ai_sessions + filesystem were granted during initial setup (2026-08-29).
        if sensor.id not in allowed:
            report["senses"][sensor.id] = {"status": gate.state(sensor.id),
                                           "note": "awaiting user permission"}
            continue
        try:
            experiences = sensor.poll()
        except Exception as e:
            report["senses"][sensor.id] = {"error": str(e)[:200]}
            continue
        for exp in experiences:
            if not exp.entities:
                exp.entities = store.extract_entities(exp.title + " " + exp.text[:2000])
        a, d = store.absorb(experiences)
        report["senses"][sensor.id] = {"absorbed": a, "dupes": d, "seen": len(experiences)}
        report["absorbed"] += a
        report["dupes"] += d

    report["graph_folded"] = graph.grow_from_store(store)

    # ANTICIPATION: notice patterns, propose automations, wait for 'yes'.
    from .anticipate import AnticipationEngine
    engine = engine or AnticipationEngine()
    try:
        report["proposals"] = engine.anticipate(store, graph)
    except Exception as e:
        report["proposal_error"] = str(e)[:200]
    return report


def run_forever(interval_s: int = 300, max_cycles: int = None,
                on_report: Callable = None):
    """The infinite loop. Polls senses, learns, sleeps, repeats."""
    store, graph = ExperienceStore(), KnowledgeGraph()
    cycle = 0
    while max_cycles is None or cycle < max_cycles:
        cycle += 1
        try:
            report = ingest_once(store, graph)
        except Exception as e:
            logger.exception("ingest cycle failed: %s", e)
            report = {"error": str(e)}
        if on_report:
            on_report(report)
        logger.info("cycle %d: %s", cycle, report)
        time.sleep(interval_s)
