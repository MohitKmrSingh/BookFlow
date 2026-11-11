import re
import unicodedata

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.core.security import create_access_token, hash_password, verify_password
from app.database.connection import get_db
from app.database.models import Business, User
from app.schemas.user import BusinessRead, MeRead, Token, UserRead, UserRegister

router = APIRouter(prefix="/auth", tags=["auth"])


def slugify(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-z0-9]+", "-", normalized.lower()).strip("-")
    return slug or "business"


def unique_slug(db: Session, name: str) -> str:
    base = slugify(name)
    slug = base
    suffix = 2
    while db.scalar(select(Business.id).where(Business.slug == slug)):
        slug = f"{base}-{suffix}"
        suffix += 1
    return slug


@router.post("/register", response_model=Token, status_code=status.HTTP_201_CREATED)
def register(payload: UserRegister, db: Session = Depends(get_db)) -> Token:
    existing = db.scalar(select(User).where(User.email == payload.email))
    if existing:
        raise HTTPException(status_code=400, detail="An account with this email already exists.")

    business = Business(
        name=payload.business_name,
        slug=unique_slug(db, payload.business_name),
        phone=payload.phone,
        address=payload.address,
    )
    db.add(business)
    db.flush()

    user = User(
        business_id=business.id,
        email=payload.email,
        hashed_password=hash_password(payload.password),
        full_name=payload.full_name,
        role="owner",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    token = create_access_token(user.id, extra_claims={"role": user.role, "business_id": user.business_id})
    return Token(access_token=token)


@router.post("/login", response_model=Token)
def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)) -> Token:
    user = db.scalar(select(User).where(User.email == form.username))
    if not user or not verify_password(form.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect email or password.")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="This account is disabled.")
    token = create_access_token(user.id, extra_claims={"role": user.role, "business_id": user.business_id})
    return Token(access_token=token)


@router.get("/me", response_model=MeRead)
def me(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> MeRead:
    business = db.get(Business, current_user.business_id)
    if not business:
        raise HTTPException(status_code=404, detail="Business not found.")
    return MeRead(user=UserRead.model_validate(current_user), business=BusinessRead.model_validate(business))
