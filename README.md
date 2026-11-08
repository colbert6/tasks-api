# Tasks API

API REST de gestión de tareas con FastAPI y SQLite.

## Instalación

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

## Ejecución

```bash
uvicorn app.main:app --reload
```

La base de datos se crea en `tasks.db` (configurable con `TASKS_DB_PATH`). Documentación interactiva en http://localhost:8000/docs.

## Pruebas

```bash
python -m pytest -q
```

## Búsqueda

`search` busca en `title` y `description` sin distinguir mayúsculas solo para letras ASCII (comportamiento de `LIKE` en SQLite); las letras acentuadas sí distinguen mayúsculas.

## Ejemplos con curl

```bash
curl localhost:8000/health
curl -X POST localhost:8000/tasks -H 'Content-Type: application/json' \
  -d '{"title": "Revisar pipeline", "priority": "high", "due_date": "2026-12-01"}'
curl 'localhost:8000/tasks?status=pending&search=pipeline&limit=10&offset=0'
curl localhost:8000/tasks/1
curl -X PATCH localhost:8000/tasks/1 -H 'Content-Type: application/json' -d '{"status": "done"}'
curl -X DELETE localhost:8000/tasks/1
```
