from fastapi import APIRouter, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.database.models import Business
from app.schemas.user import BusinessRead
from fastapi import Depends

router = APIRouter(prefix="/public", tags=["public"])


@router.get("/{slug}", response_model=BusinessRead)
def public_business(slug: str, db: Session = Depends(get_db)) -> BusinessRead:
    business = db.scalar(select(Business).where(Business.slug == slug))
    if not business:
        raise HTTPException(status_code=404, detail="Business not found.")
    return BusinessRead.model_validate(business)
