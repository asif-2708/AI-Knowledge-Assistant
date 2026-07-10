from fastapi import APIRouter, Depends, File, UploadFile, HTTPException, status
from sqlalchemy.orm import Session

from ..api.deps import get_current_user
from ..database.database import get_db
from ..database import models
from ..services.upload_service import UploadService

router = APIRouter(prefix="/upload", tags=["upload"])


@router.post("/document")
async def upload_document(
    file: UploadFile = File(...),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        service = UploadService(db=db)
        document = service.save_file(user_id=current_user.id, upload=file)
        return {"id": document.id, "filename": document.filename, "uploaded_at": document.uploaded_at.isoformat()}
    except ValueError as val_err:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(val_err))
    except Exception as err:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to upload document: {str(err)}")
