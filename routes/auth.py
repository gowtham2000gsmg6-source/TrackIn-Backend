from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from database import get_db
import models
import schemas
import auth as auth_utils

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/login", response_model=schemas.TokenResponse)
def admin_login(payload: schemas.AdminLogin, db: Session = Depends(get_db)):
    """Gate staff / admin login. Seeded default: admin / admin123"""
    admin = db.query(models.Admin).filter(models.Admin.username == payload.username).first()
    if not admin or not auth_utils.verify_password(payload.password, admin.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )

    token = auth_utils.create_access_token(data={"sub": admin.username, "role": "admin"})
    return schemas.TokenResponse(access_token=token, role="admin")


@router.post("/register-admin", response_model=schemas.TokenResponse, status_code=status.HTTP_201_CREATED)
def register_admin(payload: schemas.AdminLogin, db: Session = Depends(get_db)):
    """Create a new admin/gate-staff account. Open for first-run setup;
    lock this down (e.g. behind get_current_admin) once you have your first admin."""
    existing = db.query(models.Admin).filter(models.Admin.username == payload.username).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Username already exists")

    admin = models.Admin(username=payload.username, hashed_password=auth_utils.hash_password(payload.password))
    db.add(admin)
    db.commit()
    db.refresh(admin)

    token = auth_utils.create_access_token(data={"sub": admin.username, "role": "admin"})
    return schemas.TokenResponse(access_token=token, role="admin")
