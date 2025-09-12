from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import timedelta
from datetime import datetime

from .. import crud, schemas, auth
from ..database import get_db

router = APIRouter()

@router.post("/token", response_model=schemas.Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    print(f"--- ROUTE: /token START for user: {form_data.username} ---")
    try:
        user = crud.get_user_by_username(db, username=form_data.username)
        print(f"--- ROUTE: /token user found: {user.username if user else 'None'} ---")
        if not user or not auth.verify_password(form_data.password, user.password):
            print("--- ROUTE: /token authentication failed ---")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        print("--- ROUTE: /token authentication successful, creating token ---")
        access_token_expires = timedelta(minutes=auth.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = auth.create_access_token(
            data={"sub": user.username}, expires_delta=access_token_expires
        )
        # 更新 last_login
        try:
            user.last_login = datetime.utcnow()
            db.commit()
        except Exception:
            pass
        print("--- ROUTE: /token returning token ---")
        return {"access_token": access_token, "token_type": "bearer"}
    except Exception as e:
        print(f"--- ROUTE: /token ERROR: {e} ---")
        raise
