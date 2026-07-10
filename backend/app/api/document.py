import os
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..api.deps import get_current_user
from ..api.schemas import DocumentResponse
from ..database.database import get_db
from ..database import models

router = APIRouter(prefix="/documents", tags=["documents"])


@router.get("/", response_model=list[DocumentResponse])
def list_documents(current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    documents = db.query(models.Document).filter(models.Document.owner_id == current_user.id).all()
    return documents


@router.get("/{document_id}", response_model=DocumentResponse)
def get_document(document_id: int, current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    document = (
        db.query(models.Document)
        .filter(models.Document.id == document_id, models.Document.owner_id == current_user.id)
        .first()
    )
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    return document


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(document_id: int, current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    document = (
        db.query(models.Document)
        .filter(models.Document.id == document_id, models.Document.owner_id == current_user.id)
        .first()
    )
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    # Clean up physical file
    upload_dir = os.path.join(os.path.dirname(__file__), "..", "..", "uploads")
    filepath = os.path.join(upload_dir, document.filename)
    if os.path.exists(filepath):
        try:
            os.remove(filepath)
        except Exception as exc:
            print(f"Warning: Failed to delete file {filepath}: {exc}")

    db.delete(document)
    db.commit()
    return

