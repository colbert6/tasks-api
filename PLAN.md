# Plan: Task Manager REST API (FastAPI + sqlite3)

## File tree
```
tasks-api/
  app/
    __init__.py
    main.py      # app, lifespan, routers, /health
    db.py        # connection dependency, schema init, settings
    models.py    # Pydantic models + enums
    repo.py      # SQL functions (explicit columns)
    routes.py    # /tasks APIRouter
  tests/
    conftest.py  # temp DB fixture + dependency override + TestClient
    test_tasks.py
  requirements.txt
  README.md      # run: uvicorn app.main:app --reload
```

## Modules
- db.py: `DB_PATH = os.getenv("TASKS_DB_PATH", "tasks.db")`; `init_db(path)` runs schema (CREATE TABLE IF NOT EXISTS); `get_db()` generator dependency: `sqlite3.connect(path, check_same_thread=False)`, `row_factory = sqlite3.Row`, yield, commit on success, rollback on error, always close.
- repo.py: `create, get, list_, update, delete` taking `conn`. `COLUMNS = "id, title, description, status, priority, due_date, created_at, updated_at"` defined once. Never `SELECT *`. All queries parameterized.
- routes.py: thin handlers calling repo, raising HTTPException(404).
- main.py: lifespan calls `init_db(DB_PATH)`; includes router; `GET /health` -> `{"status": "ok"}`.

## SQL schema
```sql
CREATE TABLE IF NOT EXISTS tasks (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  title       TEXT NOT NULL CHECK (length(title) BETWEEN 1 AND 200),
  description TEXT,
  status      TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending','in_progress','done')),
  priority    TEXT NOT NULL DEFAULT 'medium' CHECK (priority IN ('low','medium','high')),
  due_date    TEXT,
  created_at  TEXT NOT NULL,
  updated_at  TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_tasks_status_priority ON tasks (status, priority);
```
Timestamps set in Python: `datetime.now(UTC).isoformat()`.

## Pydantic models
- `Status(StrEnum)`: pending, in_progress, done. `Priority(StrEnum)`: low, medium, high.
- `TaskBase`: title (1-200), description optional, status default pending, priority default medium, due_date optional date.
- `TaskCreate(TaskBase)`; `TaskUpdate`: all optional, validator rejects explicit null for title/status/priority (422).
- `Task(TaskBase)`: id, created_at, updated_at. `TaskPage`: items, total, limit, offset.
- Input models: `extra="forbid"`.

## Endpoints
| Method | Path | Request | Response |
|---|---|---|---|
| GET | /health | - | 200 {"status":"ok"} |
| POST | /tasks | TaskCreate | 201 Task; 422 |
| GET | /tasks | status?, priority?, search? (case-insensitive LIKE with % and _ escaped, ESCAPE '\'), limit=20 (1..100), offset=0 (>=0) | 200 TaskPage ordered created_at DESC, id DESC; 422 |
| GET | /tasks/{id} | - | 200 Task; 404 |
| PATCH | /tasks/{id} | TaskUpdate | 200 Task; 404; 422 |
| DELETE | /tasks/{id} | - | 204; 404 |

PATCH: `model_dump(exclude_unset=True)`; empty -> return current; else add updated_at, build SET from whitelist, `UPDATE ... RETURNING` explicit columns.
GET /tasks: one WHERE clause reused for `COUNT(id)` and page query with LIMIT/OFFSET.

## Tests
conftest: tmp_path DB + init_db, override get_db, yield TestClient(app), clear overrides.
1. /health ok. 2. Create minimal -> 201 + defaults. 3. Create full, due_date round-trips.
4. 422: missing title, empty title, 201-char title, bad status, bad priority, bad due_date, extra field.
5. GET by id 200 / missing 404. 6. List total + order. 7. Filter status, priority, combined.
8. Search case-insensitive, `%` literal. 9. Pagination slices, total constant. 10. limit=0, limit=101, offset=-1 -> 422.
11. PATCH one field keeps others, updated_at >= created_at. 12. PATCH status -> done.
13. PATCH title "" and null -> 422. 14. PATCH missing -> 404. 15. DELETE 204, then GET 404, second DELETE 404.

## Risks
- check_same_thread=False; one connection per request.
- TestClient lifespan only as context manager; fixture calls init_db directly.
- Dates stored as text; Pydantic parses on output.
