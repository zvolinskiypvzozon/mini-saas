import uuid
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, EmailStr, Field

TaskStatus = Literal["todo", "in_progress", "done"]


class RegisterIn(BaseModel):
    organization_name: str = Field(min_length=2, max_length=200)
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    email: EmailStr
    role: str
    organization_id: uuid.UUID


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)
    role: Literal["admin", "member"] = "member"


class FileOut(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    filename: str
    content_type: str
    size: int
    created_at: datetime


class DownloadOut(BaseModel):
    url: str
    expires_in: int


class ProjectIn(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    description: str | None = Field(default=None, max_length=2000)


class ProjectOut(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    name: str
    description: str | None
    created_at: datetime


class MemberIn(BaseModel):
    user_id: uuid.UUID


class TaskIn(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    description: str | None = Field(default=None, max_length=5000)
    assignee_id: uuid.UUID | None = None
    due_date: date | None = None


class TaskUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=300)
    description: str | None = Field(default=None, max_length=5000)
    status: TaskStatus | None = None
    assignee_id: uuid.UUID | None = None
    due_date: date | None = None


class TaskOut(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    project_id: uuid.UUID
    title: str
    description: str | None
    status: str
    assignee_id: uuid.UUID | None
    due_date: date | None
    created_at: datetime
    updated_at: datetime
