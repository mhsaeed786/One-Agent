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


def ingest_once(store: ExperienceStore = None, graph: KnowledgeGraph = None) -> dict:
    """One heartbeat: all senses -> store -> graph. Returns a report."""
    store = store or ExperienceStore()
    graph = graph or KnowledgeGraph()
    report = {"senses": {}, "absorbed": 0, "dupes": 0, "graph_folded": 0, "ts": time.time()}

    sensors = discover_sensors()
    for sensor in sensors:
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
