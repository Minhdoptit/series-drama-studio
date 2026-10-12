from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select
from datetime import datetime
import pathlib, os, aiofiles

from app.database import get_session
from app.models import Document, Project, User, DocumentType, utcnow
from app.services.auth_service import get_current_user
from app.services.document_service import extract_text, count_tokens

router = APIRouter()
DATA_DIR = pathlib.Path(os.getenv("DATA_DIR", "../data"))


def resolve_document_path(rel_path: str) -> pathlib.Path:
    """
    Trả về đường dẫn tuyệt đối của file tài liệu.

    Bản ghi cũ lưu path tương đối với DATA_DIR.parent (dạng "data/uploads/..."),
    bản ghi mới lưu tương đối với DATA_DIR như Image/Video. Thử cả hai để không
    làm hỏng dữ liệu đã có.
    """
    primary = DATA_DIR / rel_path
    if primary.exists():
        return primary
    return DATA_DIR.parent / rel_path


async def _assert_project_owned(project_id: str, user: User, session: AsyncSession) -> None:
    """Xác nhận project thuộc về user; nếu không, ai biết project_id cũng đọc được tài liệu."""
    result = await session.execute(
        select(Project.id).where(Project.id == project_id, Project.user_id == user.id)
    )
    if result.scalar_one_or_none() is None:
        raise HTTPException(404, "Không tìm thấy project")


@router.post("/{project_id}/documents", status_code=201)
async def upload_document(
    project_id: str,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    await _assert_project_owned(project_id, current_user, session)

    # Validate file type
    ext = pathlib.Path(file.filename).suffix.lower().lstrip(".")
    if ext not in ["pdf", "docx", "txt", "md"]:
        raise HTTPException(400, f"Định dạng file không hỗ trợ: .{ext}. Chỉ hỗ trợ PDF, DOCX, TXT, MD")

    # Save file
    upload_dir = DATA_DIR / "uploads" / project_id
    upload_dir.mkdir(parents=True, exist_ok=True)
    safe_name = f"{utcnow().strftime('%Y%m%d%H%M%S')}_{file.filename}"
    file_path = upload_dir / safe_name

    async with aiofiles.open(file_path, "wb") as f:
        content = await file.read()
        await f.write(content)

    # Extract text
    try:
        text = extract_text(str(file_path), ext)
    except Exception as e:
        text = f"[Không thể đọc file: {e}]"

    token_count = count_tokens(text)

    doc = Document(
        project_id=project_id,
        file_name=file.filename,
        # Nhất quán với Image/Video: lưu tương đối với DATA_DIR
        file_path=str(file_path.relative_to(DATA_DIR)).replace("\\", "/"),
        file_type=DocumentType(ext) if ext in ["pdf", "docx", "txt", "md"] else DocumentType.txt,
        extracted_text=text,
        token_count=token_count,
    )
    session.add(doc)
    await session.commit()
    await session.refresh(doc)
    return {
        "id": doc.id,
        "file_name": doc.file_name,
        "file_type": doc.file_type,
        "token_count": doc.token_count,
        "created_at": doc.created_at,
    }


@router.get("/{project_id}/documents")
async def list_documents(
    project_id: str,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    await _assert_project_owned(project_id, current_user, session)
    result = await session.execute(
        select(Document).where(Document.project_id == project_id).order_by(Document.created_at.desc())
    )
    docs = result.scalars().all()
    return [
        {"id": d.id, "file_name": d.file_name, "file_type": d.file_type,
         "token_count": d.token_count, "created_at": d.created_at}
        for d in docs
    ]


@router.delete("/{project_id}/documents/{doc_id}", status_code=204)
async def delete_document(
    project_id: str,
    doc_id: str,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    await _assert_project_owned(project_id, current_user, session)
    result = await session.execute(
        select(Document).where(Document.id == doc_id, Document.project_id == project_id)
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(404, "Không tìm thấy tài liệu")
    # Delete file
    try:
        full_path = resolve_document_path(doc.file_path)
        if full_path.exists():
            full_path.unlink()
    except Exception:
        pass
    await session.delete(doc)
    await session.commit()
