from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, and_, or_, desc, asc
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from . import models, schemas
from .auth import get_password_hash, verify_password
import json

# --- User Management CRUD ---
def get_user(db: Session, user_id: int) -> Optional[models.User]:
    return db.query(models.User).filter(models.User.id == user_id).first()

def get_user_by_username(db: Session, username: str) -> Optional[models.User]:
    return db.query(models.User).filter(models.User.username == username).first()

def get_user_by_email(db: Session, email: str) -> Optional[models.User]:
    return db.query(models.User).filter(models.User.email == email).first()

def get_users(db: Session, skip: int = 0, limit: int = 100, role: Optional[str] = None, status: Optional[bool] = None, search: Optional[str] = None):
    query = db.query(models.User)
    if role:
        query = query.filter(models.User.role == role)
    if status is not None:
        query = query.filter(models.User.status == status)
    if search:
        query = query.filter(or_(models.User.username.contains(search), models.User.email.contains(search)))
    
    total = query.count()
    users = query.offset(skip).limit(limit).all()
    return users, total

def create_user(db: Session, user: schemas.UserCreate) -> models.User:
    hashed_password = get_password_hash(user.password)
    db_user = models.User(username=user.username, email=user.email, password=hashed_password, role=user.role)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

def update_user(db: Session, user_id: int, user_update: schemas.UserUpdate) -> Optional[models.User]:
    db_user = get_user(db, user_id)
    if not db_user:
        return None
    update_data = user_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_user, field, value)
    db_user.update_time = datetime.utcnow()
    db.commit()
    db.refresh(db_user)
    return db_user

def delete_user(db: Session, user_id: int) -> bool:
    db_user = get_user(db, user_id)
    if not db_user:
        return False
    db.delete(db_user)
    db.commit()
    return True

# --- Quota Management CRUD ---
def get_user_quotas(db: Session, user_id: int) -> List[models.UserQuota]:
    return db.query(models.UserQuota).filter(models.UserQuota.user_id == user_id).all()

def get_user_quota_by_type(db: Session, user_id: int, quota_type: str) -> Optional[models.UserQuota]:
    return db.query(models.UserQuota).filter(and_(models.UserQuota.user_id == user_id, models.UserQuota.quota_type == quota_type, models.UserQuota.is_active == True)).first()

def create_user_quota(db: Session, quota: schemas.UserQuotaCreate) -> models.UserQuota:
    db_quota = models.UserQuota(**quota.dict())
    db.add(db_quota)
    db.commit()
    db.refresh(db_quota)
    return db_quota

def update_user_quota(db: Session, quota_id: int, quota_update: schemas.UserQuotaUpdate) -> Optional[models.UserQuota]:
    db_quota = db.query(models.UserQuota).filter(models.UserQuota.id == quota_id).first()
    if not db_quota:
        return None
    update_data = quota_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_quota, field, value)
    db_quota.update_time = datetime.utcnow()
    db.commit()
    db.refresh(db_quota)
    return db_quota

# --- API Token Management CRUD ---
def get_user_api_tokens(db: Session, user_id: int) -> List[models.ApiToken]:
    return db.query(models.ApiToken).filter(models.ApiToken.user_id == user_id).all()

def get_api_token_by_hash(db: Session, token_hash: str) -> Optional[models.ApiToken]:
    return db.query(models.ApiToken).filter(and_(models.ApiToken.token_hash == token_hash, models.ApiToken.is_active == True)).first()

def create_api_token(db: Session, token: schemas.ApiTokenCreate, token_hash: str) -> models.ApiToken:
    db_token = models.ApiToken(**token.dict(), token_hash=token_hash)
    db.add(db_token)
    db.commit()
    db.refresh(db_token)
    return db_token

# --- Translation Engine Management CRUD ---
def get_translation_engines(db: Session, skip: int = 0, limit: int = 100, status: Optional[str] = None, is_default: Optional[bool] = None) -> List[models.TranslationEngine]:
    query = db.query(models.TranslationEngine)
    if status:
        query = query.filter(models.TranslationEngine.status == status)
    if is_default is not None:
        query = query.filter(models.TranslationEngine.is_default == is_default)
    return query.order_by(models.TranslationEngine.priority).offset(skip).limit(limit).all()

def get_translation_engine(db: Session, engine_id: int) -> Optional[models.TranslationEngine]:
    return db.query(models.TranslationEngine).filter(models.TranslationEngine.id == engine_id).first()

def create_translation_engine(db: Session, engine: schemas.TranslationEngineCreate) -> models.TranslationEngine:
    db_engine = models.TranslationEngine(**engine.dict())
    db.add(db_engine)
    db.commit()
    db.refresh(db_engine)
    return db_engine

def update_translation_engine(db: Session, engine_id: int, engine_update: schemas.TranslationEngineUpdate) -> Optional[models.TranslationEngine]:
    db_engine = get_translation_engine(db, engine_id)
    if not db_engine:
        return None
    update_data = engine_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_engine, field, value)
    db_engine.update_time = datetime.utcnow()
    db.commit()
    db.refresh(db_engine)
    return db_engine

# --- System Settings Management CRUD ---
def get_system_settings(db: Session, category: Optional[str] = None, is_public: Optional[bool] = None) -> List[models.SystemSetting]:
    query = db.query(models.SystemSetting)
    if category:
        query = query.filter(models.SystemSetting.category == category)
    if is_public is not None:
        query = query.filter(models.SystemSetting.is_public == is_public)
    return query.all()

def get_system_setting_by_key(db: Session, key: str) -> Optional[models.SystemSetting]:
    return db.query(models.SystemSetting).filter(models.SystemSetting.key == key).first()

def create_system_setting(db: Session, setting: schemas.SystemSettingCreate) -> models.SystemSetting:
    db_setting = models.SystemSetting(**setting.dict())
    db.add(db_setting)
    db.commit()
    db.refresh(db_setting)
    return db_setting

def update_system_setting(db: Session, setting_id: int, setting_update: schemas.SystemSettingUpdate) -> Optional[models.SystemSetting]:
    db_setting = db.query(models.SystemSetting).filter(models.SystemSetting.id == setting_id).first()
    if not db_setting:
        return None
    update_data = setting_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_setting, field, value)
    db_setting.update_time = datetime.utcnow()
    db.commit()
    db.refresh(db_setting)
    return db_setting

# --- Dashboard and Statistics CRUD ---
def get_dashboard_stats(db: Session) -> schemas.DashboardStats:
    total_users = db.query(models.User).count()
    active_users = db.query(models.User).filter(models.User.status == True).count()
    total_translations = db.query(models.TextTranslation).count()
    total_tasks = db.query(models.TranslationTask).count()
    pending_tasks = db.query(models.TranslationTask).filter(models.TranslationTask.status == models.TaskStatus.pending).count()
    completed_tasks = db.query(models.TranslationTask).filter(models.TranslationTask.status == models.TaskStatus.completed).count()
    failed_tasks = db.query(models.TranslationTask).filter(models.TranslationTask.status == models.TaskStatus.failed).count()
    active_engines = db.query(models.TranslationEngine).filter(models.TranslationEngine.status == models.EngineStatus.active).count()
    total_quotas = db.query(models.UserQuota).filter(models.UserQuota.is_active == True).count()
    
    system_health = "healthy"
    if failed_tasks > completed_tasks * 0.1:
        system_health = "warning"
    if failed_tasks > completed_tasks * 0.3:
        system_health = "critical"
    
    return schemas.DashboardStats(
        total_users=total_users,
        active_users=active_users,
        total_translations=total_translations,
        total_tasks=total_tasks,
        pending_tasks=pending_tasks,
        completed_tasks=completed_tasks,
        failed_tasks=failed_tasks,
        system_health=system_health,
        active_engines=active_engines,
        total_quotas=total_quotas
    )

# --- Existing CRUD functions ---
def create_text_translation(db: Session, translation: schemas.TextTranslationCreate, user_id: int) -> models.TextTranslation:
    db_translation = models.TextTranslation(**translation.dict(), user_id=user_id)
    db.add(db_translation)
    db.commit()
    db.refresh(db_translation)
    return db_translation

def get_text_translations(db: Session, skip: int = 0, limit: int = 100, user_id: Optional[int] = None):
    query = db.query(models.TextTranslation)
    if user_id:
        query = query.filter(models.TextTranslation.user_id == user_id)
    return query.offset(skip).limit(limit).all()

def get_translation_tasks(db: Session, skip: int = 0, limit: int = 100, user_id: Optional[int] = None):
    query = db.query(models.TranslationTask)
    if user_id:
        query = query.filter(models.TranslationTask.user_id == user_id)
    return query.offset(skip).limit(limit).all()

def get_translation_task(db: Session, task_id: str):
    return db.query(models.TranslationTask).filter(models.TranslationTask.task_id == task_id).first()

def create_translation_task(db: Session, task: schemas.TranslationTaskCreate) -> models.TranslationTask:
    db_task = models.TranslationTask(**task.dict())
    db.add(db_task)
    db.commit()
    db.refresh(db_task)
    return db_task

def update_translation_task(db: Session, task_id: str, task_update: dict) -> Optional[models.TranslationTask]:
    db_task = get_translation_task(db, task_id)
    if not db_task:
        return None
    for field, value in task_update.items():
        if hasattr(db_task, field):
            setattr(db_task, field, value)
    db.commit()
    db.refresh(db_task)
    return db_task

def get_terminologies(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.Terminology).offset(skip).limit(limit).all()

def create_terminology(db: Session, terminology: schemas.TerminologyCreate) -> models.Terminology:
    db_terminology = models.Terminology(**terminology.dict())
    db.add(db_terminology)
    db.commit()
    db.refresh(db_terminology)
    return db_terminology

# --- Terminology CRUD used by terminology router ---
def get_terms(db: Session, skip: int = 0, limit: int = 100, category_id: Optional[int] = None, include_public: bool = True, user_id: Optional[int] = None):
    q = db.query(models.Terminology)
    if category_id is not None:
        q = q.filter(models.Terminology.category_id == category_id)
    if user_id is not None:
        if include_public:
            q = q.filter(or_(models.Terminology.user_id == user_id, models.Terminology.user_id.is_(None)))
        else:
            q = q.filter(models.Terminology.user_id == user_id)
    return q.offset(skip).limit(limit).all()

from typing import Optional
from sqlalchemy import or_, and_, func

def create_term(db: Session, term: schemas.TerminologyCreate, user_id: Optional[int] = None):
    payload = term.dict()
    # 公共术语：user_id=0；否则为当前用户
    if user_id is not None:
        if 'category_id' in payload and payload['category_id']:
            # 如果分类是公共分类，则标记为公共术语
            cat = db.query(models.TermCategory).filter(models.TermCategory.id == payload['category_id']).first()
            if cat and cat.owner_type == 'public':
                # 使用 NULL 表示公共，避免违反外键约束
                payload['user_id'] = None
            else:
                payload['user_id'] = user_id
        else:
            payload['user_id'] = user_id
    db_term = models.Terminology(**payload)
    db.add(db_term)
    db.commit()
    db.refresh(db_term)
    return db_term

def delete_term(db: Session, term_id: int):
    db_term = db.query(models.Terminology).filter(models.Terminology.id == term_id).first()
    if not db_term:
        return None
    db.delete(db_term)
    db.commit()
    return db_term

# --- TermCategory CRUD ---
def get_term_categories(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    owner_type: Optional[str] = None,
    owner_id: Optional[int] = None,
    is_active: Optional[bool] = None,
    include_term_count: bool = True,
):
    query = db.query(models.TermCategory)
    if owner_type is not None:
        query = query.filter(models.TermCategory.owner_type == owner_type)
    if owner_id is not None:
        query = query.filter(models.TermCategory.owner_id == owner_id)
    if is_active is not None:
        query = query.filter(models.TermCategory.is_active == is_active)
    query = query.order_by(models.TermCategory.sort_order.asc(), models.TermCategory.name.asc())
    categories = query.offset(skip).limit(limit).all()
    if include_term_count:
        for cat in categories:
            cat.term_count = db.query(models.Terminology).filter(
                models.Terminology.category_id == cat.id,
                models.Terminology.is_active == True,
            ).count()
    return categories

def get_term_category(db: Session, category_id: int) -> Optional[models.TermCategory]:
    return db.query(models.TermCategory).filter(models.TermCategory.id == category_id).first()

def create_term_category(db: Session, category: schemas.TermCategoryCreate, user_id: Optional[int] = None) -> models.TermCategory:
    payload = category.dict()
    if payload.get("owner_type") == "user" and user_id is not None:
        payload["owner_id"] = user_id
    db_category = models.TermCategory(**payload)
    db.add(db_category)
    db.commit()
    db.refresh(db_category)
    return db_category

def update_term_category(db: Session, category_id: int, category_update: schemas.TermCategoryUpdate) -> Optional[models.TermCategory]:
    db_category = get_term_category(db, category_id)
    if not db_category:
        return None
    update_data = category_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_category, field, value)
    db.commit()
    db.refresh(db_category)
    return db_category

def delete_term_category(db: Session, category_id: int) -> Optional[models.TermCategory]:
    db_category = get_term_category(db, category_id)
    if not db_category:
        return None
    # 确保没有术语关联
    count = db.query(models.Terminology).filter(models.Terminology.category_id == category_id).count()
    if count > 0:
        raise ValueError("Category has associated terms")
    db.delete(db_category)
    db.commit()
    return db_category

def update_term(db: Session, term_id: int, term_update: schemas.TerminologyUpdate) -> Optional[models.Terminology]:
    db_term = db.query(models.Terminology).filter(models.Terminology.id == term_id).first()
    if not db_term:
        return None
    update_data = term_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_term, field, value)
    db.commit()
    db.refresh(db_term)
    return db_term

def get_terms_by_categories(
    db: Session,
    category_ids: List[int],
    src_lang: str,
    tgt_lang: str,
    user_id: Optional[int] = None,
):
    if not category_ids:
        return []
    query = db.query(models.Terminology).filter(
        models.Terminology.category_id.in_(category_ids),
        models.Terminology.is_active == True,
        models.Terminology.is_approved == True,
    )
    if src_lang and str(src_lang).strip().lower() not in ("auto", "any", "*"):
        query = query.filter(func.lower(models.Terminology.source_lang) == func.lower(src_lang))
    if tgt_lang:
        query = query.filter(func.lower(models.Terminology.target_lang) == func.lower(tgt_lang))
    if user_id is not None:
        # 公共术语使用 NULL 表示
        query = query.filter(or_(models.Terminology.user_id.is_(None), models.Terminology.user_id == user_id))
    else:
        query = query.filter(models.Terminology.user_id.is_(None))
    return query.all()

def create_translation_term_set(db: Session, term_set: schemas.TranslationTermSetCreate) -> models.TranslationTermSet:
    db_ts = models.TranslationTermSet(**term_set.dict())
    db.add(db_ts)
    db.commit()
    db.refresh(db_ts)
    return db_ts

def get_translation_term_set(db: Session, translation_id: str, translation_type: str) -> Optional[models.TranslationTermSet]:
    return db.query(models.TranslationTermSet).filter(
        models.TranslationTermSet.translation_id == translation_id,
        models.TranslationTermSet.translation_type == translation_type,
    ).first()

# --- Terminology retrieval for runtime processing ---
def get_terms_by_lang_pair(db: Session, src_lang: str, tgt_lang: str, only_public: bool = True, user_id: Optional[int] = None):
    def lang_aliases(lang: str):
        if not lang:
            return []
        l = lang.strip().lower()
        # Basic aliases for common languages used in UI
        table = {
            'zh': ['zh', 'zh-cn', '中文', 'chinese', 'cn'],
            'en': ['en', 'en-us', '英文', 'english'],
            'ja': ['ja', 'jp', '日本語', '日文', '日语'],
            'ko': ['ko', 'kr', '한국어', '韩文', '韩语'],
        }
        # map localized labels back to canonical
        reverse = {
            '中文': 'zh', 'chinese': 'zh', 'cn': 'zh', 'zh-cn': 'zh',
            '英文': 'en', 'english': 'en', 'en-us': 'en',
            '日本語': 'ja', '日文': 'ja', '日语': 'ja', 'jp': 'ja',
            '韩国语': 'ko', '韩语': 'ko', '韩文': 'ko', 'kr': 'ko', '한국어': 'ko',
        }
        base = reverse.get(l, l)
        return table.get(base, [base])

    src_alias = lang_aliases(src_lang)
    tgt_alias = lang_aliases(tgt_lang)
    if not src_alias:
        src_alias = [src_lang]
    if not tgt_alias:
        tgt_alias = [tgt_lang]

    base = db.query(models.Terminology).filter(
        models.Terminology.is_approved == True,
    )
    # target language is required
    base = base.filter(func.lower(models.Terminology.target_lang).in_(tgt_alias))
    # source language filter if not auto/wildcard
    if src_lang and str(src_lang).strip().lower() not in ("auto", "any", "*"):
        base = base.filter(func.lower(models.Terminology.source_lang).in_(src_alias))
    if only_public:
        # 公共术语：user_id IS NULL
        return base.filter(models.Terminology.user_id.is_(None)).all()
    # include public and specified user's private terms
    if user_id is not None:
        return base.filter(
            or_(
                models.Terminology.user_id.is_(None),
                models.Terminology.user_id == user_id,
            )
        ).all()
    return base.all()

# --- TranslationTask upsert used by main.translate_document ---
def create_or_update_translation_task(db: Session, task: schemas.TranslationTaskCreate) -> models.TranslationTask:
    existing = db.query(models.TranslationTask).filter(models.TranslationTask.task_id == task.task_id).first()
    # 仅保留与模型匹配的字段，并排除 None
    data = task.dict(exclude_none=True)
    # 移除模型不存在的字段
    data.pop('username', None)
    if existing:
        for field, value in data.items():
            if hasattr(existing, field):
                setattr(existing, field, value)
        db.commit()
        db.refresh(existing)
        return existing
    db_task = models.TranslationTask(**data)
    db.add(db_task)
    db.commit()
    db.refresh(db_task)
    return db_task

def get_document_history_paginated(
    db: Session,
    user_id: Optional[int] = None,
    skip: int = 0,
    limit: int = 10,
    include_all: bool = False,
    batch_only: bool = False,
    normal_only: bool = False,
    status: Optional[str] = None,
    engine: Optional[str] = None,
    username: Optional[str] = None,
    sort_by: Optional[str] = None,
    sort_order: Optional[str] = None,
):
    """获取分页的文档翻译历史记录，支持过滤与排序"""
    query = db.query(models.TranslationTask)

    # 用户范围
    if user_id:
        query = query.filter(models.TranslationTask.user_id == user_id)

    # 模式过滤
    if batch_only:
        query = query.filter(models.TranslationTask.strategy == 'batch_api')
    if normal_only:
        query = query.filter(or_(models.TranslationTask.strategy.is_(None), models.TranslationTask.strategy != 'batch_api'))
    if not include_all:
        query = query.filter(or_(models.TranslationTask.file_name.isnot(None), models.TranslationTask.result_path.isnot(None)))

    # 字段过滤
    if status:
        # 使用枚举比较，避免数据库枚举与字符串比较导致的错误
        try:
            status_enum = models.TaskStatus(status.lower())
            query = query.filter(models.TranslationTask.status == status_enum)
        except Exception:
            # 无效的状态值则忽略过滤
            pass
    if engine:
        query = query.filter(models.TranslationTask.engine == engine)

    # 管理员按用户名模糊过滤（仅当未限制到 user_id 时才有意义）
    if username and not user_id:
        query = query.join(models.User, models.User.id == models.TranslationTask.user_id).filter(models.User.username.ilike(f"%{username}%"))

    total = query.count()

    # 排序安全映射
    sort_columns = {
        'create_time': models.TranslationTask.create_time,
        'token_count': models.TranslationTask.token_count,
        'duration': models.TranslationTask.duration,
        'source_file_size': models.TranslationTask.source_file_size,
        'target_file_size': models.TranslationTask.target_file_size,
    }
    order_col = sort_columns.get((sort_by or 'create_time'), models.TranslationTask.create_time)
    order_dir = desc if (sort_order or 'desc').lower() == 'desc' else asc

    items = query.order_by(order_dir(order_col)).offset(skip).limit(limit).all()

    return items, total

# --- Batch metrics ---
def upsert_batch_metrics(db: Session, batch_id: str, total: int, completed: int, failed: int, tokens: int) -> models.BatchMetrics:
    m = db.query(models.BatchMetrics).filter(models.BatchMetrics.batch_id == batch_id).first()
    if not m:
        m = models.BatchMetrics(batch_id=batch_id, total=total, completed=completed, failed=failed, tokens=tokens)
        db.add(m)
    else:
        m.total = total
        m.completed = completed
        m.failed = failed
        m.tokens = tokens
    db.commit()
    db.refresh(m)
    return m

def get_batch_metrics(db: Session, batch_id: str) -> Optional[models.BatchMetrics]:
    return db.query(models.BatchMetrics).filter(models.BatchMetrics.batch_id == batch_id).first()

def prune_old_batch_metrics(db: Session, days: int = 30) -> int:
    threshold = datetime.utcnow() - timedelta(days=days)
    deleted = db.query(models.BatchMetrics).filter(models.BatchMetrics.update_time < threshold).delete()
    db.commit()
    return deleted

