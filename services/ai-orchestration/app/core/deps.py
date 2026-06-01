from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt

from shared.config.settings import get_settings
from shared.models.user import User, UserTier

settings = get_settings()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="http://user-service/api/v1/auth/login")


async def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return User(
        id=payload["sub"],
        email=payload.get("email", ""),
        tier=UserTier(payload.get("tier", "free")),
        preferences={},
        created_at=__import__("datetime").datetime.utcnow(),
    )
