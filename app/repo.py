import sqlite3
from datetime import UTC, datetime

COLUMNS = "id, title, description, status, priority, due_date, created_at, updated_at"
UPDATABLE = {"title", "description", "status", "priority", "due_date", "updated_at"}


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _escape_like(s: str) -> str:
    return s.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def create(conn: sqlite3.Connection, data: dict) -> dict:
    now = _now()
    row = conn.execute(
        f"INSERT INTO tasks (title, description, status, priority, due_date, created_at, updated_at) "
        f"VALUES (?, ?, ?, ?, ?, ?, ?) RETURNING {COLUMNS}",
        (data["title"], data.get("description"), data["status"], data["priority"],
         data.get("due_date"), now, now),
    ).fetchone()
    return dict(row)


def get(conn: sqlite3.Connection, task_id: int) -> dict | None:
    row = conn.execute(f"SELECT {COLUMNS} FROM tasks WHERE id = ?", (task_id,)).fetchone()
    return dict(row) if row else None


def list_(conn: sqlite3.Connection, status: str | None = None, priority: str | None = None,
          search: str | None = None, limit: int = 20, offset: int = 0) -> tuple[list[dict], int]:
    clauses, params = [], []
    if status:
        clauses.append("status = ?")
        params.append(status)
    if priority:
        clauses.append("priority = ?")
        params.append(priority)
    if search:
        # SQLite LIKE is case-insensitive for ASCII.
        clauses.append("(title LIKE ? ESCAPE '\\' OR description LIKE ? ESCAPE '\\')")
        pattern = f"%{_escape_like(search)}%"
        params += [pattern, pattern]
    where = f" WHERE {' AND '.join(clauses)}" if clauses else ""
    total = conn.execute(f"SELECT COUNT(id) FROM tasks{where}", params).fetchone()[0]
    rows = conn.execute(
        f"SELECT {COLUMNS} FROM tasks{where} ORDER BY created_at DESC, id DESC LIMIT ? OFFSET ?",
        [*params, limit, offset],
    ).fetchall()
    return [dict(r) for r in rows], total


def update(conn: sqlite3.Connection, task_id: int, changes: dict) -> dict | None:
    if not changes:
        return get(conn, task_id)
    fields = {k: v for k, v in {**changes, "updated_at": _now()}.items() if k in UPDATABLE}
    set_clause = ", ".join(f"{k} = ?" for k in fields)
    row = conn.execute(
        f"UPDATE tasks SET {set_clause} WHERE id = ? RETURNING {COLUMNS}",
        [*fields.values(), task_id],
    ).fetchone()
    return dict(row) if row else None


def delete(conn: sqlite3.Connection, task_id: int) -> bool:
    return conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,)).rowcount > 0
