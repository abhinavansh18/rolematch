import hashlib
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

from app.core.deps import get_current_user
from app.db.session import get_db
from app.services.resume_service import ResumeService
from shared.models.user import User

router = APIRouter()

ALLOWED_CONTENT_TYPES = {"application/pdf", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB


@router.post("/upload", status_code=status.HTTP_202_ACCEPTED)
async def upload_resume(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db=Depends(get_db),
):
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(status_code=415, detail="Only PDF and DOCX are supported")

    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="File exceeds 5 MB limit")

    file_hash = hashlib.sha256(content).hexdigest()
    svc = ResumeService(db)
    resume = await svc.create_and_enqueue(
        user_id=current_user.id,
        filename=file.filename,
        content=content,
        file_hash=file_hash,
        content_type=file.content_type,
    )
    return {"resume_id": resume.id, "status": "queued", "message": "Resume queued for parsing"}


@router.get("/{resume_id}")
async def get_resume(
    resume_id: UUID,
    current_user: User = Depends(get_current_user),
    db=Depends(get_db),
):
    svc = ResumeService(db)
    resume = await svc.get_by_id(resume_id, current_user.id)
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")
    return resume


@router.get("/")
async def list_resumes(current_user: User = Depends(get_current_user), db=Depends(get_db)):
    svc = ResumeService(db)
    return await svc.list_for_user(current_user.id)


@router.delete("/{resume_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_resume(
    resume_id: UUID,
    current_user: User = Depends(get_current_user),
    db=Depends(get_db),
):
    svc = ResumeService(db)
    deleted = await svc.delete(resume_id, current_user.id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Resume not found")
