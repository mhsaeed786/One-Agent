"""REST API endpoints for AI Session Hub."""

import json
import sqlite3
from datetime import datetime, timezone
from flask import Flask, jsonify, request

from config import DB_PATH


def get_db():
    """Get a database connection."""
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.row_factory = sqlite3.Row
    return conn


def register_routes(app: Flask):
    """Register all API routes on the Flask app."""

    # --- Tools ---
    @app.route("/api/tools")
    def api_tools():
        conn = get_db()
        tools = conn.execute(
            "SELECT name, display_name, data_path, enabled, last_sync_at, session_count, total_size_mb FROM tools ORDER BY display_name"
        ).fetchall()
        conn.close()
        return jsonify([dict(t) for t in tools])

    # --- Stats ---
    @app.route("/api/stats")
    def api_stats():
        conn = get_db()
        total_sessions = conn.execute("SELECT COUNT(*) as c FROM sessions").fetchone()["c"]
        total_messages = conn.execute("SELECT COUNT(*) as c FROM messages").fetchone()["c"]
        total_size = conn.execute("SELECT COALESCE(SUM(file_size_bytes), 0) as s FROM sessions").fetchone()["s"]
        tools_with_data = conn.execute(
            "SELECT COUNT(DISTINCT tool) as c FROM sessions"
        ).fetchone()["c"]

        # Sessions by tool
        by_tool = conn.execute(
            "SELECT tool, COUNT(*) as count FROM sessions GROUP BY tool ORDER BY count DESC"
        ).fetchall()

        # Recent sessions
        recent = conn.execute("""
            SELECT id, tool, title, started_at, message_count
            FROM sessions
            ORDER BY COALESCE(started_at, first_synced_at) DESC
            LIMIT 10
        """).fetchall()

        last_sync = conn.execute(
            "SELECT MAX(sync_ended_at) as t FROM sync_log WHERE status != 'running'"
        ).fetchone()["t"]

        conn.close()
        return jsonify({
            "total_sessions": total_sessions,
            "total_messages": total_messages,
            "total_size_mb": round(total_size / 1048576, 2),
            "tools_with_data": tools_with_data,
            "by_tool": [dict(r) for r in by_tool],
            "recent_sessions": [dict(r) for r in recent],
            "last_sync": last_sync,
        })

    # --- Sessions List ---
    @app.route("/api/sessions")
    def api_sessions():
        conn = get_db()
        page = request.args.get("page", 1, type=int)
        per_page = request.args.get("per_page", 30, type=int)
        tool = request.args.get("tool", "")
        search = request.args.get("search", "")
        date_from = request.args.get("date_from", "")
        date_to = request.args.get("date_to", "")
        project = request.args.get("project", "")

        where_clauses = []
        params = []

        if tool:
            where_clauses.append("s.tool = ?")
            params.append(tool)
        if date_from:
            where_clauses.append("s.started_at >= ?")
            params.append(date_from)
        if date_to:
            where_clauses.append("s.started_at <= ?")
            params.append(date_to)
        if project:
            where_clauses.append("s.project_path LIKE ?")
            params.append(f"%{project}%")
        if search:
            # Use FTS for search
            where_clauses.append("""
                s.id IN (
                    SELECT m.session_fk FROM messages m
                    JOIN messages_fts fts ON m.id = fts.rowid
                    WHERE messages_fts MATCH ?
                )
            """)
            params.append(search)

        where_sql = (" WHERE " + " AND ".join(where_clauses)) if where_clauses else ""

        # Count
        count_row = conn.execute(
            f"SELECT COUNT(*) as c FROM sessions s{where_sql}", params
        ).fetchone()
        total = count_row["c"]

        # Fetch
        offset = (page - 1) * per_page
        rows = conn.execute(f"""
            SELECT s.id, s.tool, s.session_id, s.title, s.project_path,
                   s.model, s.status, s.started_at, s.ended_at,
                   s.message_count, s.file_size_bytes, s.last_synced_at
            FROM sessions s
            {where_sql}
            ORDER BY COALESCE(s.started_at, s.first_synced_at) DESC
            LIMIT ? OFFSET ?
        """, params + [per_page, offset]).fetchall()

        conn.close()
        return jsonify({
            "sessions": [dict(r) for r in rows],
            "total": total,
            "page": page,
            "per_page": per_page,
            "total_pages": (total + per_page - 1) // per_page,
        })

    # --- Session Detail ---
    @app.route("/api/sessions/<path:session_id>")
    def api_session_detail(session_id):
        conn = get_db()
        session = conn.execute(
            "SELECT * FROM sessions WHERE id = ?", (session_id,)
        ).fetchone()

        if not session:
            conn.close()
            return jsonify({"error": "Session not found"}), 404

        messages = conn.execute("""
            SELECT id, message_id, role, content_text, content_type,
                   model, timestamp, token_input, token_output, parent_id, seq
            FROM messages
            WHERE session_fk = ?
            ORDER BY seq, id
        """, (session_id,)).fetchall()

        conn.close()
        return jsonify({
            "session": dict(session),
            "messages": [dict(m) for m in messages],
        })

    # --- Session Messages (paginated) ---
    @app.route("/api/sessions/<path:session_id>/messages")
    def api_session_messages(session_id):
        conn = get_db()
        page = request.args.get("page", 1, type=int)
        per_page = request.args.get("per_page", 50, type=int)
        offset = (page - 1) * per_page

        total = conn.execute(
            "SELECT COUNT(*) as c FROM messages WHERE session_fk = ?",
            (session_id,)
        ).fetchone()["c"]

        messages = conn.execute("""
            SELECT id, message_id, role, content_text, content_type,
                   model, timestamp, token_input, token_output, parent_id, seq
            FROM messages
            WHERE session_fk = ?
            ORDER BY seq, id
            LIMIT ? OFFSET ?
        """, (session_id, per_page, offset)).fetchall()

        conn.close()
        return jsonify({
            "messages": [dict(m) for m in messages],
            "total": total,
            "page": page,
            "per_page": per_page,
        })

    # --- Search ---
    @app.route("/api/search")
    def api_search():
        conn = get_db()
        q = request.args.get("q", "")
        page = request.args.get("page", 1, type=int)
        per_page = request.args.get("per_page", 30, type=int)

        if not q:
            conn.close()
            return jsonify({"results": [], "total": 0})

        try:
            offset = (page - 1) * per_page

            # Search via FTS
            total = conn.execute("""
                SELECT COUNT(*) as c FROM messages_fts WHERE messages_fts MATCH ?
            """, (q,)).fetchone()["c"]

            results = conn.execute("""
                SELECT m.id, m.session_fk, m.role, m.content_text,
                       m.content_type, m.timestamp, m.seq,
                       s.tool, s.title as session_title
                FROM messages_fts fts
                JOIN messages m ON m.id = fts.rowid
                JOIN sessions s ON s.id = m.session_fk
                WHERE messages_fts MATCH ?
                ORDER BY rank
                LIMIT ? OFFSET ?
            """, (q, per_page, offset)).fetchall()

            conn.close()
            return jsonify({
                "results": [dict(r) for r in results],
                "total": total,
                "page": page,
                "per_page": per_page,
            })
        except Exception as e:
            conn.close()
            return jsonify({"results": [], "total": 0, "error": str(e)})

    # --- Trigger Sync ---
    @app.route("/api/sync", methods=["POST"])
    def api_sync():
        from sync.engine import SyncEngine
        try:
            engine = SyncEngine(force_full=False)
            results = engine.run_all()
            return jsonify({"status": "ok", "results": results})
        except Exception as e:
            return jsonify({"status": "error", "error": str(e)}), 500

    # --- Projects List ---
    @app.route("/api/projects")
    def api_projects():
        conn = get_db()
        projects = conn.execute("""
            SELECT project_path, COUNT(*) as session_count
            FROM sessions
            WHERE project_path IS NOT NULL AND project_path != ''
            GROUP BY project_path
            ORDER BY session_count DESC
        """).fetchall()
        conn.close()
        return jsonify([dict(p) for p in projects])
