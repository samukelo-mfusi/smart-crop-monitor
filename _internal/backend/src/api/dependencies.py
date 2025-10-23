from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session
from ..database.database import get_db
from ..core.security import get_current_user
from ..database.models import User

def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user

def get_db_session() -> Session:
    db = next(get_db())
    try:
        yield db
    finally:
        db.close()