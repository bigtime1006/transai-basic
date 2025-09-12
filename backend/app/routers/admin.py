from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from typing import List, Optional
from ..database import get_db
from ..auth import get_current_active_user, get_current_admin_user
from .. import crud, schemas, models
from datetime import datetime, timedelta
import secrets
import hashlib
from sqlalchemy import and_, func
import os

router = APIRouter(tags=["admin"])

# --- Dashboard and Statistics ---
@router.get("/dashboard", response_model=schemas.DashboardStats)
async def get_dashboard_stats(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_admin_user)
):
    """获取系统仪表板统计数据"""
    return crud.get_dashboard_stats(db)

# --- User Management ---
@router.get("/users", response_model=schemas.UserPage)
async def get_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    role: Optional[str] = Query(None),
    status: Optional[bool] = Query(None),
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_admin_user)
):
    """获取用户列表"""
    users, total = crud.get_users(db, skip=skip, limit=limit, role=role, status=status, search=search)
    return {"users": users, "total": total}

@router.get("/users/{user_id}", response_model=schemas.UserDetail)
async def get_user_detail(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_admin_user)
):
    """获取用户详细信息"""
    user = crud.get_user(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    return user

@router.post("/users", response_model=schemas.User)
async def create_user(
    user: schemas.UserCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_admin_user)
):
    """创建新用户"""
    # 检查用户名是否已存在
    if crud.get_user_by_username(db, user.username):
        raise HTTPException(status_code=400, detail="用户名已存在")
    
    # 检查邮箱是否已存在
    if user.email and crud.get_user_by_email(db, user.email):
        raise HTTPException(status_code=400, detail="邮箱已存在")
    
    return crud.create_user(db, user)

@router.put("/users/{user_id}", response_model=schemas.User)
async def update_user(
    user_id: int,
    user_update: schemas.UserUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_admin_user)
):
    """更新用户信息"""
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="不能修改自己的角色")
    
    updated_user = crud.update_user(db, user_id, user_update)
    if not updated_user:
        raise HTTPException(status_code=404, detail="用户不存在")
    return updated_user

@router.delete("/users/{user_id}")
async def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_admin_user)
):
    """删除用户"""
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="不能删除自己")
    
    if not crud.delete_user(db, user_id):
        raise HTTPException(status_code=404, detail="用户不存在")
    
    return {"message": "用户删除成功"}

# --- Quota Management ---
@router.get("/users/{user_id}/quotas", response_model=List[schemas.UserQuota])
async def get_user_quotas(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_admin_user)
):
    """获取用户配额信息"""
    user = crud.get_user(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    return crud.get_user_quotas(db, user_id)

@router.post("/users/{user_id}/quotas", response_model=schemas.UserQuota)
async def create_user_quota(
    user_id: int,
    quota: schemas.UserQuotaCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_admin_user)
):
    """为用户创建配额"""
    user = crud.get_user(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    # 检查是否已存在相同类型的配额
    existing_quota = crud.get_user_quota_by_type(db, user_id, quota.quota_type)
    if existing_quota:
        raise HTTPException(status_code=400, detail="该类型的配额已存在")
    
    quota.user_id = user_id
    return crud.create_user_quota(db, quota)

@router.put("/quotas/{quota_id}", response_model=schemas.UserQuota)
async def update_user_quota(
    quota_id: int,
    quota_update: schemas.UserQuotaUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_admin_user)
):
    """更新用户配额"""
    updated_quota = crud.update_user_quota(db, quota_id, quota_update)
    if not updated_quota:
        raise HTTPException(status_code=404, detail="配额不存在")
    return updated_quota

@router.post("/quotas/{quota_id}/reset")
async def reset_quota_usage(
    quota_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_admin_user)
):
    """重置配额使用量"""
    quota = db.query(models.UserQuota).filter(models.UserQuota.id == quota_id).first()
    if not quota:
        raise HTTPException(status_code=404, detail="配额不存在")
    
    quota.used_value = 0
    quota.reset_date = datetime.utcnow()
    quota.update_time = datetime.utcnow()
    db.commit()
    
    return {"message": "配额使用量重置成功"}

# --- API Token Management ---
@router.get("/users/{user_id}/tokens", response_model=List[schemas.ApiToken])
async def get_user_api_tokens(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_admin_user)
):
    """获取用户的API令牌"""
    user = crud.get_user(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    return crud.get_user_api_tokens(db, user_id)

@router.post("/users/{user_id}/tokens", response_model=schemas.ApiToken)
async def create_api_token(
    user_id: int,
    token: schemas.ApiTokenCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_admin_user)
):
    """为用户创建API令牌"""
    user = crud.get_user(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    # 生成令牌哈希
    token_value = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(token_value.encode()).hexdigest()
    
    token.user_id = user_id
    db_token = crud.create_api_token(db, token, token_hash)
    
    # 返回令牌值（仅此一次）
    return {
        **db_token.__dict__,
        "token_value": token_value
    }

@router.delete("/tokens/{token_id}")
async def delete_api_token(
    token_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_admin_user)
):
    """删除API令牌"""
    token = db.query(models.ApiToken).filter(models.ApiToken.id == token_id).first()
    if not token:
        raise HTTPException(status_code=404, detail="令牌不存在")
    
    db.delete(token)
    db.commit()
    
    return {"message": "API令牌删除成功"}

# --- Translation Engine Management ---
@router.get("/engines", response_model=List[schemas.TranslationEngine])
async def get_translation_engines(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    status: Optional[str] = Query(None),
    is_default: Optional[bool] = Query(None),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_admin_user)
):
    """获取翻译引擎列表"""
    return crud.get_translation_engines(db, skip=skip, limit=limit, status=status, is_default=is_default)

@router.get("/engines/{engine_id}", response_model=schemas.TranslationEngine)
async def get_translation_engine(
    engine_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_admin_user)
):
    """获取翻译引擎详情"""
    engine = crud.get_translation_engine(db, engine_id)
    if not engine:
        raise HTTPException(status_code=404, detail="翻译引擎不存在")
    return engine

@router.post("/engines", response_model=schemas.TranslationEngine)
async def create_translation_engine(
    engine: schemas.TranslationEngineCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_admin_user)
):
    """创建翻译引擎"""
    # 检查引擎名称是否已存在
    existing_engine = crud.get_translation_engine_by_name(db, engine.engine_name)
    if existing_engine:
        raise HTTPException(status_code=400, detail="引擎名称已存在")
    
    return crud.create_translation_engine(db, engine)

@router.put("/engines/{engine_id}", response_model=schemas.TranslationEngine)
async def update_translation_engine(
    engine_id: int,
    engine_update: schemas.TranslationEngineUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_admin_user)
):
    """更新翻译引擎"""
    # 如果要设为默认，则将其它引擎默认位清零，保证唯一
    if engine_update.is_default is True:
        engines = db.query(models.TranslationEngine).all()
        for e in engines:
            e.is_default = False
        db.commit()
    updated_engine = crud.update_translation_engine(db, engine_id, engine_update)
    if not updated_engine:
        raise HTTPException(status_code=404, detail="翻译引擎不存在")
    return updated_engine

@router.delete("/engines/{engine_id}")
async def delete_translation_engine(
    engine_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_admin_user)
):
    """删除翻译引擎"""
    engine = crud.get_translation_engine(db, engine_id)
    if not engine:
        raise HTTPException(status_code=404, detail="翻译引擎不存在")
    
    # 检查是否有策略依赖此引擎
    strategies = db.query(models.TranslationStrategy).filter(models.TranslationStrategy.engine_id == engine_id).count()
    if strategies > 0:
        raise HTTPException(status_code=400, detail="该引擎正在被翻译策略使用，无法删除")
    
    db.delete(engine)
    db.commit()
    
    return {"message": "翻译引擎删除成功"}

@router.post("/engines/{engine_id}/toggle")
async def toggle_engine_status(
    engine_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_admin_user)
):
    """切换引擎状态"""
    engine = crud.get_translation_engine(db, engine_id)
    if not engine:
        raise HTTPException(status_code=404, detail="翻译引擎不存在")
    
    if engine.status == models.EngineStatus.active:
        engine.status = models.EngineStatus.inactive
    else:
        engine.status = models.EngineStatus.active
    
    engine.update_time = datetime.utcnow()
    db.commit()
    
    return {"message": f"引擎状态已切换为 {engine.status}"}

# --- System Settings Management ---
# 注意：将更具体的静态路径放在动态路径之前，避免路由匹配到 /settings/{setting_id}
@router.get("/settings/registration", response_model=dict)
async def get_registration_setting(db: Session = Depends(get_db)):
    """获取用户注册是否开放的设置（公开，无需登录）。异常时默认允许。"""
    try:
        setting = crud.get_system_setting_by_key(db, "allow_registration")
        allow = True  # 默认允许注册
        if setting and isinstance(setting.value, str):
            if setting.value.strip().lower() in ["false", "0", "no"]:
                allow = False
        return {"allow_registration": allow}
    except Exception:
        # 任何异常均返回默认允许，避免登录页阻塞
        return {"allow_registration": True}

# 将“策略”相关静态路由放在动态 /settings/{setting_id} 之前
@router.get("/settings/strategies")
async def list_strategies(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_admin_user)):
    # 若库中无策略，初始化默认三种策略
    existing_count = db.query(models.TranslationStrategy).count()
    if existing_count == 0:
        defaults = [
            {
                "strategy_name": "text_direct",
                "display_name": "文本直接处理",
                "description": "针对 .txt/.md 的逐行翻译处理",
                "status": True,
                "priority": 0,
                "supported_formats": ["txt", "md"],
            },
            {
                "strategy_name": "ooxml_direct",
                "display_name": "OOXML直接处理",
                "description": "本地解析替换 DOCX/PPTX/XLSX 文本",
                "status": True,
                "priority": 10,
                "supported_formats": ["docx", "pptx", "xlsx"],
            },
            {
                "strategy_name": "aspose",
                "display_name": "Aspose 文档处理(预留)",
                "description": "通过 Aspose 云服务处理 Office 文档（预留，默认禁用）",
                "status": False,
                "priority": 20,
                "supported_formats": ["docx", "pptx", "xlsx"],
            },
        ]
        for s in defaults:
            db.add(models.TranslationStrategy(
                strategy_name=s["strategy_name"],
                display_name=s["display_name"],
                description=s.get("description"),
                engine_id=None,
                config=None,
                status=s["status"],
                priority=s["priority"],
                supported_formats=s["supported_formats"],
            ))
        db.commit()

    strategies = db.query(models.TranslationStrategy).order_by(models.TranslationStrategy.priority.asc()).all()

    return [
        {
            "strategy_name": s.strategy_name,
            "display_name": s.display_name,
            "description": s.description,
            "status": s.status,
            "priority": s.priority,
            "supported_formats": s.supported_formats or []
        } for s in strategies
    ]

@router.put("/settings/strategies/{strategy_name}")
async def update_strategy_status(
    strategy_name: str,
    payload: dict,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_admin_user)
):
    strategy = db.query(models.TranslationStrategy).filter(models.TranslationStrategy.strategy_name == strategy_name).first()
    if not strategy:
        raise HTTPException(status_code=404, detail="策略不存在")
    status = payload.get("status")
    priority = payload.get("priority")
    if status is not None:
        strategy.status = bool(status)
    if priority is not None:
        strategy.priority = int(priority)
    db.commit()
    return {"message": "策略已更新"}

@router.get("/settings", response_model=List[schemas.SystemSetting])
async def get_system_settings(
    category: Optional[str] = Query(None),
    is_public: Optional[bool] = Query(None),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_admin_user)
):
    """获取系统设置"""
    return crud.get_system_settings(db, category=category, is_public=is_public)

@router.get("/settings/{setting_id}", response_model=schemas.SystemSetting)
async def get_system_setting(
    setting_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_admin_user)
):
    """获取系统设置详情"""
    setting = db.query(models.SystemSetting).filter(models.SystemSetting.id == setting_id).first()
    if not setting:
        raise HTTPException(status_code=404, detail="系统设置不存在")
    return setting

@router.post("/settings", response_model=schemas.SystemSetting)
async def create_system_setting(
    setting: schemas.SystemSettingCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_admin_user)
):
    """创建系统设置"""
    # 检查键是否已存在
    existing_setting = crud.get_system_setting_by_key(db, setting.key)
    if existing_setting:
        raise HTTPException(status_code=400, detail="设置键已存在")
    
    return crud.create_system_setting(db, setting)

@router.put("/settings/{setting_id}", response_model=schemas.SystemSetting)
async def update_system_setting(
    setting_id: int,
    setting_update: schemas.SystemSettingUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_admin_user)
):
    """更新系统设置"""
    updated_setting = crud.update_system_setting(db, setting_id, setting_update)
    if not updated_setting:
        raise HTTPException(status_code=404, detail="系统设置不存在")
    return updated_setting

@router.delete("/settings/{setting_id}")
async def delete_system_setting(
    setting_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_admin_user)
):
    """删除系统设置"""
    setting = crud.get_system_setting(db, setting_id)
    if not setting:
        raise HTTPException(status_code=404, detail="系统设置不存在")
    
    if not setting.is_editable:
        raise HTTPException(status_code=400, detail="该设置不可编辑")
    
    db.delete(setting)
    db.commit()
    
    return {"message": "系统设置删除成功"}

# --- Engine/DeepSeek runtime settings (migrated from main.py) ---
@router.get("/settings/deepseek")
async def get_deepseek_settings():
    """获取DeepSeek设置（公开只读信息，不涉及密钥）"""
    try:
        from app.services.engine_config import EngineConfig
        config = EngineConfig.get_deepseek_config()
        return {
            "use_json_format": config.get('use_json_format', True),
            "json_batch_size": config.get('json_batch_size', 50),
            "batch_size": config.get('batch_size', 20),
            "max_workers": config.get('max_workers', 10),
            "timeout": config.get('timeout', 60)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get DeepSeek settings: {e}")

@router.post("/settings/deepseek")
async def update_deepseek_settings(settings: dict, current_user: models.User = Depends(get_current_admin_user)):
    """更新DeepSeek设置（仅影响当前进程环境变量）"""
    try:
        use_json_format = settings.get('use_json_format')
        json_batch_size = settings.get('json_batch_size')

        if use_json_format is not None and not isinstance(use_json_format, bool):
            raise HTTPException(status_code=400, detail="use_json_format must be boolean")
        if json_batch_size is not None:
            if not isinstance(json_batch_size, int) or json_batch_size <= 0:
                raise HTTPException(status_code=400, detail="json_batch_size must be positive integer")
            if json_batch_size > 100:
                raise HTTPException(status_code=400, detail="json_batch_size cannot exceed 100")

        if use_json_format is not None:
            os.environ['DEEPSEEK_USE_JSON_FORMAT'] = str(use_json_format).lower()
        if json_batch_size is not None:
            os.environ['DEEPSEEK_JSON_BATCH_SIZE'] = str(json_batch_size)

        return {"message": "DeepSeek settings updated successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update DeepSeek settings: {e}")

@router.get("/settings/engines")
async def get_all_engine_settings(current_user: models.User = Depends(get_current_admin_user)):
    """获取所有AI引擎设置（聚合只读视图）"""
    try:
        from app.services.engine_config import EngineConfig
        settings = {}
        # DeepSeek
        try:
            deepseek_config = EngineConfig.get_deepseek_config()
            settings['deepseek'] = {
                "use_json_format": deepseek_config.get('use_json_format', True),
                "json_batch_size": deepseek_config.get('json_batch_size', 50),
                "batch_size": deepseek_config.get('batch_size', 20),
                "max_workers": deepseek_config.get('max_workers', 10),
                "timeout": deepseek_config.get('timeout', 60)
            }
        except Exception:
            settings['deepseek'] = {"error": "Configuration unavailable"}
        # Kimi
        try:
            kimi_config = EngineConfig.get_kimi_config()
            settings['kimi'] = {
                "batch_size": kimi_config.get('batch_size', 8),
                "max_workers": kimi_config.get('max_workers', 2),
                "timeout": kimi_config.get('timeout', 60)
            }
        except Exception:
            settings['kimi'] = {"error": "Configuration unavailable"}
        # Youdao
        try:
            youdao_config = EngineConfig.get_youdao_config()
            settings['youdao'] = {
                "batch_size": youdao_config.get('batch_size', 10),
                "max_workers": youdao_config.get('max_workers', 3),
                "timeout": youdao_config.get('timeout', 60),
                "max_batch_size": youdao_config.get('max_batch_size', 5),
                "max_chars_per_batch": youdao_config.get('max_chars_per_batch', 1000)
            }
        except Exception:
            settings['youdao'] = {"error": "Configuration unavailable"}
        # Tencent
        try:
            tencent_config = EngineConfig.get_tencent_config()
            settings['tencent'] = {
                "batch_size": tencent_config.get('batch_size', 15),
                "max_workers": tencent_config.get('max_workers', 5),
                "timeout": tencent_config.get('timeout', 60)
            }
        except Exception:
            settings['tencent'] = {"error": "Configuration unavailable"}
        # Qwen3
        try:
            qwen_config = EngineConfig.get_qwen3_config()
            settings['qwen3'] = {
                "model": qwen_config.get('model', 'qwen-mt-turbo'),
                "batch_size": qwen_config.get('batch_size', 50),
                "max_workers": qwen_config.get('max_workers', 12),
                "timeout": qwen_config.get('timeout', 60)
            }
        except Exception:
            settings['qwen3'] = {"error": "Configuration unavailable"}
        # Qwen Plus
        try:
            qwenp = EngineConfig.get_qwen_plus_config()
            settings['qwen_plus'] = {
                "model": qwenp.get('model', 'qwen-plus'),
                "batch_size": qwenp.get('batch_size', 30),
                "max_workers": qwenp.get('max_workers', 10),
                "timeout": qwenp.get('timeout', 60),
                "retry_max": qwenp.get('retry_max', 3),
                "sleep_between_requests": qwenp.get('sleep_between_requests', 0.05)
            }
        except Exception:
            settings['qwen_plus'] = {"error": "Configuration unavailable"}
        return settings
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get engine settings: {e}")

 

# --- System Maintenance ---
@router.post("/maintenance/clear-logs")
async def clear_old_logs(
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_admin_user)
):
    """清理旧日志"""
    cutoff_date = datetime.utcnow() - timedelta(days=days)
    
    # 清理审计日志
    deleted_logs = db.query(models.AuditLog).filter(models.AuditLog.create_time < cutoff_date).delete()
    
    # 清理过期的API令牌
    deleted_tokens = db.query(models.ApiToken).filter(
        and_(
            models.ApiToken.expires_at < datetime.utcnow(),
            models.ApiToken.expires_at.isnot(None)
        )
    ).delete()
    
    db.commit()
    
    return {
        "message": "日志清理完成",
        "deleted_logs": deleted_logs,
        "deleted_tokens": deleted_tokens
    }

@router.post("/maintenance/reset-quotas")
async def reset_all_quotas(
    quota_type: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_admin_user)
):
    """重置所有用户配额"""
    query = db.query(models.UserQuota).filter(models.UserQuota.is_active == True)
    
    if quota_type:
        query = query.filter(models.UserQuota.quota_type == quota_type)
    
    quotas = query.all()
    
    for quota in quotas:
        quota.used_value = 0
        quota.reset_date = datetime.utcnow()
        quota.update_time = datetime.utcnow()
    
    db.commit()
    
    return {"message": f"已重置 {len(quotas)} 个配额"}

@router.get("/system/health")
async def get_system_health(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_admin_user)
):
    """获取系统健康状态"""
    stats = crud.get_dashboard_stats(db)
    
    # 检查数据库连接
    try:
        db.execute("SELECT 1")
        db_status = "healthy"
    except Exception as e:
        db_status = f"error: {str(e)}"
    
    # 检查Redis连接（如果有的话）
    redis_status = "unknown"
    
    return {
        "database": db_status,
        "redis": redis_status,
        "overall_health": stats.system_health,
        "last_check": datetime.utcnow().isoformat()
    }
