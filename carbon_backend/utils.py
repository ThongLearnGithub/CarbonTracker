from fastapi import HTTPException
from sqlalchemy.orm import Session

from orm_models import User, Token


def get_user_by_token(token: str, db: Session) -> User:
    token_record = db.query(Token).filter(Token.token == token).first()
    if not token_record:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    user = db.query(User).filter(User.id == token_record.user_id).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    return user
