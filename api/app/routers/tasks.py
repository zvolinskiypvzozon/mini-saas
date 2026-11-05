import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.access import get_project_for_user, get_task_for_user, is_project_member
from app.db import get_db
from app.deps import get_current_user
from app.models import Task, User
from app.schemas import TaskIn, TaskOut, TaskStatus, TaskUpdate

router = APIRouter(prefix="/api", tags=["tasks"])

NOT_NULL_FIELDS = ("title", "status")


def _check_assignee(db: Session, project_id: uuid.UUID, assignee_id: uuid.UUID | None) -> None:
    if assignee_id is not None and not is_project_member(db, project_id, assignee_id):
        raise HTTPException(status_code=422, detail="Assignee must be a project member")


@router.post("/projects/{project_id}/tasks", response_model=TaskOut, status_code=201)
def create_task(
    project_id: uuid.UUID,
    data: TaskIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    project = get_project_for_user(db, project_id, user)
    _check_assignee(db, project.id, data.assignee_id)
    task = Task(project_id=project.id, created_by=user.id, **data.model_dump())
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


@router.get("/projects/{project_id}/tasks", response_model=list[TaskOut])
def list_tasks(
    project_id: uuid.UUID,
    status: TaskStatus | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    project = get_project_for_user(db, project_id, user)
    query = select(Task).where(Task.project_id == project.id)
    if status is not None:
        query = query.where(Task.status == status)
    return db.scalars(query.order_by(Task.created_at)).all()


@router.patch("/tasks/{task_id}", response_model=TaskOut)
def update_task(
    task_id: uuid.UUID,
    data: TaskUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    task = get_task_for_user(db, task_id, user)
    changes = data.model_dump(exclude_unset=True)
    for field in NOT_NULL_FIELDS:
        if field in changes and changes[field] is None:
            raise HTTPException(status_code=422, detail=f"{field} cannot be null")
    if "assignee_id" in changes:
        _check_assignee(db, task.project_id, changes["assignee_id"])
    for field, value in changes.items():
        setattr(task, field, value)
    db.commit()
    db.refresh(task)
    return task


@router.delete("/tasks/{task_id}", status_code=204)
def delete_task(
    task_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    task = get_task_for_user(db, task_id, user)
    db.delete(task)
    db.commit()
