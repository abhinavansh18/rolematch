from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from app.core.security import create_access_token, verify_password
from app.db.session import get_db
from app.schemas.auth import TokenResponse, RegisterRequest
from app.services.user_service import UserService
from shared.config.settings import get_settings

router = APIRouter()
settings = get_settings()


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(payload: RegisterRequest, db=Depends(get_db)):
    svc = UserService(db)
    if await svc.get_by_email(payload.email):
        raise HTTPException(status_code=409, detail="Email already registered")
    user = await svc.create(payload.email, payload.password)
    token = create_access_token(
        data={"sub": str(user.id), "tier": user.tier},
        expires_delta=timedelta(minutes=settings.jwt_access_token_expire_minutes),
    )
    return TokenResponse(access_token=token, token_type="bearer")


@router.post("/login", response_model=TokenResponse)
async def login(form: OAuth2PasswordRequestForm = Depends(), db=Depends(get_db)):
    svc = UserService(db)
    user = await svc.get_by_email(form.username)
    if not user or not verify_password(form.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = create_access_token(
        data={"sub": str(user.id), "tier": user.tier},
        expires_delta=timedelta(minutes=settings.jwt_access_token_expire_minutes),
    )
    return TokenResponse(access_token=token, token_type="bearer")


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout():
    # Token invalidation handled client-side; server-side blocklist optional for enterprise
    return
