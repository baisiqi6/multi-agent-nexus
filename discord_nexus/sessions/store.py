import sqlite3
import time
from pathlib import Path


def _row_to_dict(row: tuple) -> dict:
    return {
        "scope_id": row[0],
        "agent_id": row[1],
        "adapter": row[2],
        "session_id": row[3],
        "work_dir": row[4],
        "status": row[5],
        "turn_count": row[6],
        "created_at": row[7],
        "updated_at": row[8],
    }


class SessionStore:
    """Persist CLI session IDs scoped to channel + agent."""

    def __init__(self, db_path: str):
        self.path = Path(db_path).expanduser()
        if not self.path.is_absolute():
            self.path = Path.cwd() / self.path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path, timeout=10)
        conn.execute("PRAGMA busy_timeout=10000")
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS sessions (
                    scope_id TEXT NOT NULL,
                    agent_id TEXT NOT NULL,
                    adapter TEXT NOT NULL,
                    session_id TEXT NOT NULL,
                    work_dir TEXT,
                    status TEXT NOT NULL DEFAULT 'active',
                    turn_count INTEGER NOT NULL DEFAULT 0,
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL,
                    PRIMARY KEY (scope_id, agent_id)
                )
                """
            )

    def get(
        self, *, scope_id: str, agent_id: str
    ) -> dict | None:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT scope_id, agent_id, adapter, session_id, work_dir,
                       status, turn_count, created_at, updated_at
                FROM sessions
                WHERE scope_id = ? AND agent_id = ? AND status = 'active'
                """,
                (scope_id, agent_id),
            ).fetchone()
        if not row:
            return None
        return _row_to_dict(row)

    def list_by_agent(
        self, *, agent_id: str, include_stale: bool = False
    ) -> list[dict]:
        sql = (
            "SELECT scope_id, agent_id, adapter, session_id, work_dir, "
            "status, turn_count, created_at, updated_at "
            "FROM sessions WHERE agent_id = ?"
        )
        params: list[str] = [agent_id]
        if not include_stale:
            sql += " AND status = 'active'"
        sql += " ORDER BY updated_at DESC"
        with self._connect() as conn:
            rows = conn.execute(sql, params).fetchall()
        return [_row_to_dict(row) for row in rows]

    def upsert(
        self,
        *,
        scope_id: str,
        agent_id: str,
        adapter: str,
        session_id: str,
        work_dir: str | None = None,
    ) -> None:
        now = time.time()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO sessions
                    (scope_id, agent_id, adapter, session_id, work_dir,
                     status, turn_count, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, 'active', 1, ?, ?)
                ON CONFLICT(scope_id, agent_id) DO UPDATE SET
                    session_id = excluded.session_id,
                    adapter = excluded.adapter,
                    work_dir = excluded.work_dir,
                    turn_count = turn_count + 1,
                    updated_at = excluded.updated_at,
                    status = 'active'
                """,
                (scope_id, agent_id, adapter, session_id, work_dir, now, now),
            )

    def mark_stale(self, *, scope_id: str, agent_id: str) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE sessions SET status = 'stale', updated_at = ?
                WHERE scope_id = ? AND agent_id = ?
                """,
                (time.time(), scope_id, agent_id),
            )
