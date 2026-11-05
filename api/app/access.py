import uuid

from fastapi import Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.deps import get_current_user
from app.models import Project, ProjectMember, Task, User

ADMIN_ROLES = ("owner", "admin")


def require_roles(*roles: str):
    def checker(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return user

    return checker


def is_project_member(db: Session, project_id: uuid.UUID, user_id: uuid.UUID) -> bool:
    return db.get(ProjectMember, (project_id, user_id)) is not None


def get_project_for_user(db: Session, project_id: uuid.UUID, user: User) -> Project:
    project = db.scalar(
        select(Project).where(
            Project.id == project_id,
            Project.organization_id == user.organization_id,
        )
    )
    has_access = project is not None and (
        user.role in ADMIN_ROLES or is_project_member(db, project.id, user.id)
    )
    if not has_access:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


def get_task_for_user(db: Session, task_id: uuid.UUID, user: User) -> Task:
    task = db.get(Task, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    try:
        get_project_for_user(db, task.project_id, user)
    except HTTPException:
        raise HTTPException(status_code=404, detail="Task not found")
    return task
