from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.core.deps import get_current_user
from app.db.session import get_db
from app.services.user_service import UserService
from shared.models.user import User

router = APIRouter()


class UpdatePreferencesRequest(BaseModel):
    preferences: dict


@router.get("/me", response_model=User)
async def get_me(current_user: User = Depends(get_current_user)):
    return current_user


@router.patch("/me/preferences")
async def update_preferences(
    payload: UpdatePreferencesRequest,
    current_user: User = Depends(get_current_user),
    db=Depends(get_db),
):
    svc = UserService(db)
    user = await svc.get_by_id(current_user.id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.preferences = {**user.preferences, **payload.preferences}
    return {"status": "updated", "preferences": user.preferences}


@router.delete("/me", status_code=204)
async def delete_account(
    current_user: User = Depends(get_current_user),
    db=Depends(get_db),
):
    """GDPR right to erasure — triggers async deletion pipeline."""
    from shared.utils.kafka import get_producer, publish
    producer = await get_producer()
    try:
        await publish(producer, "user.deletion_requested", {
            "user_id": str(current_user.id),
            "email_hash": __import__("hashlib").sha256(
                current_user.email.encode()
            ).hexdigest(),
        })
    finally:
        await producer.stop()
