from fastapi import APIRouter, Depends
from src.schemas.user import PasswordChange
from src.models.user import User
from src.core.security import get_current_user
from src.core.database import get_db
from sqlalchemy.ext.asyncio import AsyncSession


router = APIRouter()

@router.post("/change-password")
async def change_password(
    password_change: PasswordChange,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # Verify current password
    # Update to new password
    pass