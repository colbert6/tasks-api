import sqlite3
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Response, status

from app import repo
from app.db import get_db
from app.models import Priority, Status, Task, TaskCreate, TaskPage, TaskUpdate

router = APIRouter(prefix="/tasks", tags=["tasks"])
Conn = Annotated[sqlite3.Connection, Depends(get_db)]
MAX_INT = 2**63 - 1
TaskId = Annotated[int, Path(ge=1, le=MAX_INT)]


def _or_404(task: dict | None) -> dict:
    if task is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Task not found")
    return task


@router.post("", response_model=Task, status_code=status.HTTP_201_CREATED)
def create_task(body: TaskCreate, conn: Conn):
    return repo.create(conn, body.model_dump(mode="json"))


@router.get("", response_model=TaskPage)
def list_tasks(
    conn: Conn,
    status_: Annotated[Status | None, Query(alias="status")] = None,
    priority: Priority | None = None,
    search: str | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0, le=MAX_INT)] = 0,
):
    items, total = repo.list_(conn, status_, priority, search, limit, offset)
    return {"items": items, "total": total, "limit": limit, "offset": offset}


@router.get("/{task_id}", response_model=Task)
def get_task(task_id: TaskId, conn: Conn):
    return _or_404(repo.get(conn, task_id))


@router.patch("/{task_id}", response_model=Task)
def update_task(task_id: TaskId, body: TaskUpdate, conn: Conn):
    return _or_404(repo.update(conn, task_id, body.model_dump(mode="json", exclude_unset=True)))


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(task_id: TaskId, conn: Conn):
    if not repo.delete(conn, task_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Task not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)
