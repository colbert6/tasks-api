# Plan: interfaz web para tasks-api

## Resumen
SPA sin build (HTML + JS + CSS) servida por FastAPI desde el mismo origen. Navegador y API comparten host y puerto, así que **no hace falta CORS**. Cada agente toca archivos distintos: el merge no debería dar conflictos.

## Reparto

**BACKEND (`feat/backend-static`)** — solo `app/`, `tests/` y `README.md`:
- `app/main.py`:
  - `STATIC_DIR = Path(os.getenv("TASKS_STATIC_DIR", <raíz>/static))`.
  - `GET /` devuelve `FileResponse(STATIC_DIR / "index.html")` con `include_in_schema=False`; 404 si no existe.
  - `app.mount("/static", StaticFiles(directory=STATIC_DIR, check_dir=False), name="static")`, después de los routers.
  - `/docs`, `/openapi.json`, `/health` y `/tasks` no cambian.
- `tests/test_static.py`: `/` con index falso en tmp → 200 `text/html`; sin index → 404; `/static/no-existe.js` → 404; `/docs` → 200; `/health` ok.
- `README.md`: sección "Interfaz web".
- La API no cambia.

**FRONTEND (`feat/frontend`)** — solo `static/`:
- `static/index.html`, `static/app.js`, `static/styles.css`.

## Contrato
- Directorio `static/` en la raíz del repo.
- `/` sirve `index.html`; assets con ruta absoluta (`/static/app.js`, `/static/styles.css`); API con rutas relativas (`/tasks`).
- Task: `id` (int), `title` (1–200, se recorta), `description` (≤10000 o null), `status` (`pending` | `in_progress` | `done`), `priority` (`low` | `medium` | `high`), `due_date` (`YYYY-MM-DD` o null), `created_at` y `updated_at` (ISO datetime).
- `GET /tasks?status&priority&search&limit(1..100, def 20)&offset(>=0)` → 200 `{items,total,limit,offset}`, orden `created_at` DESC. **Omitir filtros vacíos** (`status=""` da 422).
- `POST /tasks` → 201 Task; sin campos extra.
- `PATCH /tasks/{id}` → 200 Task; solo campos cambiados; `due_date` y `description` aceptan null; null en `title`/`status`/`priority` → 422.
- `DELETE /tasks/{id}` → 204 **sin body** (no llamar a `res.json()`).
- 404: `{"detail":"Task not found"}`.
- 422: `{"detail":[{loc:[...], msg, type}]}`; mostrar `loc` final traducido (`title` → "Título") con `msg`.

## Funcionalidades de la UI (en español)
- Filtros: estado, prioridad y búsqueda con debounce de ~300 ms.
- Paginación "Anterior/Siguiente" y "X–Y de N"; si una página queda vacía tras borrar, retrocede.
- Formulario de creación.
- Edición en formulario dentro de la tarjeta.
- Checkbox para marcar `done` (PATCH).
- Borrar con `confirm()`.
- Errores 422 bajo cada campo; aviso general para 404 y errores de red.
- Estado vacío ("No hay tareas" / "Sin resultados").
- Responsive (móvil primero), sin CDN.
- Texto del usuario con `textContent` (evita XSS).

## Criterios de aceptación
1. `uvicorn app.main:app --reload` y http://localhost:8000 carga la UI sin errores en consola.
2. `/docs` funciona y `/` no aparece en OpenAPI.
3. `python -m pytest -q` pasa en cada rama y tras el merge.
4. Crear, filtrar, paginar, editar, completar y borrar funcionan contra la API real.
5. Título vacío o de 201 caracteres muestra el error en español junto al campo.
6. Ningún archivo lo modifican las dos ramas.

## Riesgos
- `static/` no existe en la rama backend → `check_dir=False` y tests con tmp; tras el merge verificar `/static/app.js` = 200.
- Mensajes de Pydantic en inglés → traducir nombre del campo y mapear por `type`.
- Montar en `/` en vez de `/static` taparía la API.
- `<input type="date">` vacío da `""` → null en PATCH, omitir en POST.
- Búsqueda sin distinguir mayúsculas solo en ASCII.
