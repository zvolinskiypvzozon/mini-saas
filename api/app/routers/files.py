import os
import uuid

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import storage
from app.db import get_db
from app.deps import get_current_user
from app.models import StoredFile, User
from app.schemas import DownloadOut, FileOut

router = APIRouter(prefix="/api/files", tags=["files"])

MAX_UPLOAD_BYTES = int(os.environ.get("MAX_UPLOAD_MB", "10")) * 1024 * 1024
DOWNLOAD_URL_TTL = 300


def _get_own_file(db: Session, file_id: uuid.UUID, user: User) -> StoredFile:
    record = db.scalar(
        select(StoredFile).where(
            StoredFile.id == file_id,
            StoredFile.organization_id == user.organization_id,
        )
    )
    if record is None:
        raise HTTPException(status_code=404, detail="File not found")
    return record


@router.post("", response_model=FileOut, status_code=201)
def upload_file(
    file: UploadFile,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    data = file.file.read(MAX_UPLOAD_BYTES + 1)
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="File too large")
    if not data:
        raise HTTPException(status_code=400, detail="Empty file")

    raw_name = (file.filename or "").replace("\\", "/")
    filename = os.path.basename(raw_name).strip()[:255] or "file"
    content_type = (file.content_type or "application/octet-stream")[:100]

    file_id = uuid.uuid4()
    key = f"{user.organization_id}/{file_id}"
    storage.put(key, data, content_type)

    record = StoredFile(
        id=file_id,
        organization_id=user.organization_id,
        owner_id=user.id,
        s3_key=key,
        filename=filename,
        content_type=content_type,
        size=len(data),
    )
    db.add(record)
    try:
        db.commit()
    except Exception:
        db.rollback()
        storage.delete(key)
        raise
    db.refresh(record)
    return record


@router.get("", response_model=list[FileOut])
def list_files(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return db.scalars(
        select(StoredFile)
        .where(StoredFile.organization_id == user.organization_id)
        .order_by(StoredFile.created_at.desc())
    ).all()


@router.get("/{file_id}/download", response_model=DownloadOut)
def download_file(
    file_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    record = _get_own_file(db, file_id, user)
    url = storage.presigned_get(record.s3_key, record.filename, DOWNLOAD_URL_TTL)
    return DownloadOut(url=url, expires_in=DOWNLOAD_URL_TTL)


@router.delete("/{file_id}", status_code=204)
def delete_file(
    file_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    record = _get_own_file(db, file_id, user)
    storage.delete(record.s3_key)
    db.delete(record)
    db.commit()
