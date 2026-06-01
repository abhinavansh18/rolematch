from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from app.core.security import decode_token
from app.db.session import get_db
from app.services.user_service import UserService
from shared.models.user import User, UserTier

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db=Depends(get_db),
) -> User:
    try:
        payload = decode_token(token)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    svc = UserService(db)
    db_user = await svc.get_by_id(payload["sub"])
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    return User(
        id=db_user.id,
        email=db_user.email,
        tier=UserTier(db_user.tier),
        preferences=db_user.preferences,
        created_at=db_user.created_at,
        last_active_at=db_user.last_active_at,
    )


async def require_pro(user: User = Depends(get_current_user)) -> User:
    if user.tier not in (UserTier.PRO, UserTier.ENTERPRISE):
        raise HTTPException(status_code=403, detail="Pro subscription required")
    return user


async def require_enterprise(user: User = Depends(get_current_user)) -> User:
    if user.tier != UserTier.ENTERPRISE:
        raise HTTPException(status_code=403, detail="Enterprise subscription required")
    return user
