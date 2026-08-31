"""Mind Chat — command the Mind in natural language.

Guardrail contract (Aug-29 directive, enforced here):
  - READ-ONLY intents (search, graph, stats, list)  -> answered directly
  - REPORT-ONLY registered actions (repo_hygiene…) -> run directly, show report
  - ANYTHING that writes/schedules/destroys        -> becomes a PENDING PROPOSAL;
    nothing executes until the user approves (via chat or API)

Intent grammar (kept deterministic; LLM used only for free-form replies):
  search|find|what do i know about <q>   -> memory search
  graph <node>                           -> graph neighbors
  run <action>                           -> report-only action if registered
  propose <description>                  -> create pending proposal
  approve <id|last> / deny <id|last>     -> decision on a proposal
  grant <sense> / deny <sense>           -> permission toggle
  absorb <text>                          -> store an experience
  ask|why|how|<anything else>            -> LLM (baqa router) w/ graceful fallback
"""
from __future__ import annotations

import time
import uuid
from typing import Dict, List, Optional


def handle(message: str) -> dict:
    msg = (message or "").strip()
    low = msg.lower()

    if not msg:
        return {"reply": "Say something — try: `search fhir`, `graph teams`, `run repo_hygiene`, `propose ...`"}

    # ── memory search ────────────────────────────────────────────────
    for prefix in ("search ", "find ", "what do i know about ", "what do you know about "):
        if low.startswith(prefix):
            q = msg[len(prefix):].strip()
            from .store import ExperienceStore
            results = ExperienceStore().search(q, 8)
            if not results:
                return {"reply": f"Nothing in memory about “{q}” yet."}
            lines = [f"• [{r['source']}] {r['title'][:100]}" for r in results]
            return {"reply": f"Found {len(results)} experiences for “{q}”:\n" + "\n".join(lines),
                    "results": results}

    # ── graph ────────────────────────────────────────────────────────
    if low.startswith("graph "):
        node = msg[6:].strip()
        from .graph import KnowledgeGraph
        related = KnowledgeGraph().neighbors(node, 10)
        if not related:
            return {"reply": f"Node “{node}” is not in the graph yet."}
        lines = [f"• {r['related']} ({r['weight']})" for r in related]
        return {"reply": f"“{node}” connects to:\n" + "\n".join(lines)}

    # ── run a registered action (report-only guardrail) ─────────────
    if low.startswith("run "):
        action = msg[4:].strip().replace(" ", "_").lower()
        from .runner import ACTIONS
        if action not in ACTIONS:
            return {"reply": (f"“{action}” is not a registered report-only action. "
                              f"Known: {', '.join(sorted(ACTIONS))}. "
                              f"For anything else, say `propose <what you want>` and approve it.")}
        try:
            report = ACTIONS[action]()
            import json
            return {"reply": f"Ran **{action}** (report-only):\n```json\n{json.dumps(report, indent=1, default=str)[:1200]}\n```"}
        except Exception as e:
            return {"reply": f"{action} failed: {e}"}

    # ── propose ──────────────────────────────────────────────────────
    if low.startswith("propose "):
        desc = msg[8:].strip()
        pid = uuid.uuid4().hex[:12]
        from .anticipate import AnticipationEngine
        import sqlite3, os
        eng = AnticipationEngine()
        with sqlite3.connect(eng.db_path) as conn:
            conn.execute(
                "INSERT OR IGNORE INTO proposals(id, signature, title, rationale, kind, schedule, action, desc, status, created_at)"
                " VALUES (?,?,?,?,?,?,?,?, 'pending', ?)",
                (pid, f"chat:{pid}", desc[:80], "Requested via chat", "manual",
                 "manual", "awaiting_implementation", desc, time.time()))
        return {"reply": (f"Proposal `{pid}` created and PENDING. Nothing runs until you approve it "
                          f"(say `approve {pid}`). Note: custom proposals wait for an implementation "
                          f"to exist; built-in actions execute on approval.")}

    # ── approve / deny proposals ─────────────────────────────────────
    if low.startswith("approve ") or low.startswith("deny "):
        verb, _, ref = msg.partition(" ")
        ref = ref.strip()
        from .anticipate import AnticipationEngine
        eng = AnticipationEngine()
        pending = eng.list("pending")
        target = None
        if ref == "last" and pending:
            target = pending[0]["id"]
        else:
            for p in pending:
                if p["id"].startswith(ref) or ref.lower() in p["title"].lower():
                    target = p["id"]
                    break
        if not target:
            return {"reply": f"No pending proposal matches “{ref}”. Say `proposals` to list them."}
        from .runner import register_approved
        if verb == "approve":
            proposal = eng.approve(target)
            result = register_approved(proposal)
            if result.get("executed"):
                import json
                return {"reply": f"Approved and executed (report-only):\n```json\n{json.dumps(result.get('report',{}), indent=1, default=str)[:1000]}\n```"}
            return {"reply": f"Approved `{target}`. " + result.get("note", "Registered.")}
        eng.deny(target)
        return {"reply": f"Denied `{target}`. It will not run."}

    if low in ("proposals", "list proposals", "show proposals"):
        from .anticipate import AnticipationEngine
        rows = AnticipationEngine().list("pending")
        if not rows:
            return {"reply": "No pending proposals."}
        lines = [f"• `{r['id']}` {r['title']} — {r['desc'][:80]}" for r in rows]
        return {"reply": "Pending proposals:\n" + "\n".join(lines)}

    # ── permissions ──────────────────────────────────────────────────
    if low.startswith("grant ") or low.startswith("deny "):
        verb, _, sense = msg.partition(" ")
        sense = sense.strip().lower()
        from .permissions import PermissionGate
        gate = PermissionGate()
        gate.grant(sense) if verb == "grant" else gate.deny(sense)
        return {"reply": f"Sense “{sense}” → {gate.state(sense)}."}

    # ── absorb ───────────────────────────────────────────────────────
    if low.startswith("absorb "):
        text = msg[7:].strip()
        from .sensors.web_capture import capture_instruction
        r = capture_instruction({"tool": "web:chat", "kind": "note",
                                 "title": text[:90], "text": text, "uri": "chat"})
        return {"reply": "Absorbed." if r.get("stored") else f"Not stored: {r.get('reason')}"}

    # ── free-form -> LLM cortex (keys now present) ───────────────────
    return _llm_reply(msg)


def _llm_reply(msg: str) -> dict:
    try:
        import asyncio, sys, os
        baqa = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
        if baqa not in sys.path:
            sys.path.insert(0, os.path.abspath(baqa))
        from core.llm.router import get_router
        router = get_router()
        resp = asyncio.run(
            router.complete(messages=[{"role": "system",
                                       "content": "You are the Mind, the user's personal super-app assistant. Be brief, practical, and suggest automations when relevant."},
                                      {"role": "user", "content": msg}],
                            task_class="reason"))
        text = getattr(resp, "text", None) or (resp.get("text") if isinstance(resp, dict) else None) or str(resp)
        return {"reply": text[:2000]}
    except Exception as e:
        return {"reply": ("LLM cortex unavailable (" + str(e)[:120] + ").\n"
                          "Commands that always work: `search <q>` · `graph <node>` · "
                          "`run repo_hygiene` · `proposals` · `approve last` · "
                          "`grant <sense>` · `absorb <text>` · `propose <idea>`")}
