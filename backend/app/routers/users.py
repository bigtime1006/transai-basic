from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from .. import crud, models, schemas, auth
from ..database import get_db

router = APIRouter()

@router.post("/register", response_model=schemas.User)
def create_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    # Check if registration is allowed (default: allowed)
    allow = True
    try:
        allow_reg_setting = crud.get_system_setting_by_key(db, key="allow_registration")
        if allow_reg_setting and isinstance(allow_reg_setting.value, str):
            if allow_reg_setting.value.strip().lower() in ["false", "0", "no"]:
                allow = False
    except Exception:
        # if settings table not ready, allow registration by default
        allow = True
    if not allow:
        raise HTTPException(status_code=403, detail="User registration is currently disabled")

    db_user = crud.get_user_by_username(db, username=user.username)
    if db_user:
        raise HTTPException(status_code=400, detail="Username already registered")
    return crud.create_user(db=db, user=user)

@router.get("/me", response_model=schemas.User)
async def read_users_me(current_user: models.User = Depends(auth.get_current_active_user)):
    return current_user

@router.post("/me/change-password")
def change_password(payload: schemas.PasswordChangeRequest, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_active_user)):
    if not auth.verify_password(payload.old_password, current_user.password):
        raise HTTPException(status_code=400, detail="旧密码不正确")
    if not _validate_password(payload.new_password):
        raise HTTPException(status_code=400, detail="新密码不满足复杂度要求")
    current_user.password = auth.get_password_hash(payload.new_password)
    db.commit()
    return {"message": "密码已更新"}

@router.post("/admin/users/{user_id}/reset-password")
def admin_reset_password(user_id: int, payload: schemas.AdminPasswordResetRequest, db: Session = Depends(get_db), admin_user: models.User = Depends(auth.get_current_admin_user)):
    user = crud.get_user(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    if not _validate_password(payload.new_password):
        raise HTTPException(status_code=400, detail="新密码不满足复杂度要求")
    user.password = auth.get_password_hash(payload.new_password)
    db.commit()
    return {"message": "用户密码已重置"}

def _validate_password(pw: str) -> bool:
    # 默认策略
    min_len = 8
    req_upper = True
    req_lower = True
    req_digit = True
    req_special = False
    try:
        # 读取系统设置
        # 这些键由系统设置页面维护
        setting_map = {
            'password_min_length': 'min_len',
            'password_require_uppercase': 'req_upper',
            'password_require_lowercase': 'req_lower',
            'password_require_digit': 'req_digit',
            'password_require_special': 'req_special',
        }
        # 使用直接查询，避免循环发请求
        # 此处简化：逐项查询，系统设置数量很小
        from .. import crud as _crud
        from ..database import get_db as _get_db
        # FastAPI 依赖外部，此处仅在请求上下文内调用，因此创建一个会话
        db = _get_db().__next__()
        def get_val(key, default):
            row = _crud.get_system_setting_by_key(db, key)
            if row is None: return default
            v = str(row.value).strip().lower()
            if isinstance(default, bool):
                return v in ['true','1','yes','y']
            try:
                return int(v)
            except:
                return default
        min_len = get_val('password_min_length', min_len)
        req_upper = get_val('password_require_uppercase', req_upper)
        req_lower = get_val('password_require_lowercase', req_lower)
        req_digit = get_val('password_require_digit', req_digit)
        req_special = get_val('password_require_special', req_special)
    except Exception:
        pass
    if pw is None or len(pw) < int(min_len):
        return False
    if req_upper and not any(c.isupper() for c in pw):
        return False
    if req_lower and not any(c.islower() for c in pw):
        return False
    if req_digit and not any(c.isdigit() for c in pw):
        return False
    if req_special and not any(not c.isalnum() for c in pw):
        return False
    return True
