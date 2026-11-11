from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, require_owner
from app.database.connection import get_db
from app.database.models import Business, Service, User
from app.schemas.service import ServiceCreate, ServiceRead, ServiceUpdate

router = APIRouter(prefix="/services", tags=["services"])
public_router = APIRouter(prefix="/public/{slug}/services", tags=["public"])


@router.get("", response_model=list[ServiceRead])
def list_services(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[Service]:
    return list(
        db.scalars(select(Service).where(Service.business_id == current_user.business_id).order_by(Service.name))
    )


@router.post("", response_model=ServiceRead, status_code=status.HTTP_201_CREATED)
def create_service(
    payload: ServiceCreate,
    current_user: User = Depends(require_owner),
    db: Session = Depends(get_db),
) -> Service:
    service = Service(business_id=current_user.business_id, **payload.model_dump())
    db.add(service)
    db.commit()
    db.refresh(service)
    return service


@router.patch("/{service_id}", response_model=ServiceRead)
def update_service(
    service_id: int,
    payload: ServiceUpdate,
    current_user: User = Depends(require_owner),
    db: Session = Depends(get_db),
) -> Service:
    service = db.scalar(
        select(Service).where(Service.id == service_id, Service.business_id == current_user.business_id)
    )
    if not service:
        raise HTTPException(status_code=404, detail="Service not found.")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(service, field, value)
    db.commit()
    db.refresh(service)
    return service


@router.delete("/{service_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_service(
    service_id: int,
    current_user: User = Depends(require_owner),
    db: Session = Depends(get_db),
) -> None:
    service = db.scalar(
        select(Service).where(Service.id == service_id, Service.business_id == current_user.business_id)
    )
    if not service:
        raise HTTPException(status_code=404, detail="Service not found.")
    service.is_active = False
    db.commit()


@public_router.get("", response_model=list[ServiceRead])
def public_list_services(slug: str, db: Session = Depends(get_db)) -> list[Service]:
    business = db.scalar(select(Business).where(Business.slug == slug))
    if not business:
        raise HTTPException(status_code=404, detail="Salon not found.")
    return list(
        db.scalars(
            select(Service).where(Service.business_id == business.id, Service.is_active.is_(True)).order_by(Service.name)
        )
    )
