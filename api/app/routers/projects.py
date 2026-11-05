import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.access import ADMIN_ROLES, get_project_for_user, is_project_member, require_roles
from app.db import get_db
from app.deps import get_current_user
from app.models import Project, ProjectMember, User
from app.schemas import MemberIn, ProjectIn, ProjectOut, UserOut

router = APIRouter(prefix="/api/projects", tags=["projects"])
admin_only = require_roles(*ADMIN_ROLES)


@router.post("", response_model=ProjectOut, status_code=201)
def create_project(
    data: ProjectIn,
    db: Session = Depends(get_db),
    user: User = Depends(admin_only),
):
    project = Project(
        organization_id=user.organization_id,
        name=data.name,
        description=data.description,
        created_by=user.id,
    )
    db.add(project)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Project with this name already exists")
    db.add(ProjectMember(project_id=project.id, user_id=user.id))
    db.commit()
    db.refresh(project)
    return project


@router.get("", response_model=list[ProjectOut])
def list_projects(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    query = select(Project).where(Project.organization_id == user.organization_id)
    if user.role not in ADMIN_ROLES:
        query = query.join(ProjectMember, ProjectMember.project_id == Project.id).where(
            ProjectMember.user_id == user.id
        )
    return db.scalars(query.order_by(Project.created_at)).all()


@router.get("/{project_id}", response_model=ProjectOut)
def get_project(
    project_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return get_project_for_user(db, project_id, user)


@router.delete("/{project_id}", status_code=204)
def delete_project(
    project_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(admin_only),
):
    project = get_project_for_user(db, project_id, user)
    db.delete(project)
    db.commit()


@router.get("/{project_id}/members", response_model=list[UserOut])
def list_members(
    project_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    project = get_project_for_user(db, project_id, user)
    return db.scalars(
        select(User)
        .join(ProjectMember, ProjectMember.user_id == User.id)
        .where(ProjectMember.project_id == project.id)
        .order_by(ProjectMember.added_at)
    ).all()


@router.post("/{project_id}/members", response_model=UserOut, status_code=201)
def add_member(
    project_id: uuid.UUID,
    data: MemberIn,
    db: Session = Depends(get_db),
    user: User = Depends(admin_only),
):
    project = get_project_for_user(db, project_id, user)
    member = db.scalar(
        select(User).where(User.id == data.user_id, User.organization_id == user.organization_id)
    )
    if member is None:
        raise HTTPException(status_code=404, detail="User not found")
    if is_project_member(db, project.id, member.id):
        raise HTTPException(status_code=409, detail="User is already a member")
    db.add(ProjectMember(project_id=project.id, user_id=member.id))
    db.commit()
    return member


@router.delete("/{project_id}/members/{user_id}", status_code=204)
def remove_member(
    project_id: uuid.UUID,
    user_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(admin_only),
):
    project = get_project_for_user(db, project_id, user)
    link = db.get(ProjectMember, (project.id, user_id))
    if link is None:
        raise HTTPException(status_code=404, detail="Member not found")
    db.delete(link)
    db.commit()
