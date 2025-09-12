from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from sqlalchemy import or_

from .. import crud, models, schemas
from ..services.terminology_service import get_terminology_options as svc_get_terminology_options
from ..database import get_db
from ..auth import get_current_active_user

router = APIRouter()

@router.get("/options")
def get_terminology_options_endpoint(db: Session = Depends(get_db)):
    """获取术语配置选项（前端用于渲染分类开关、最大分类数等）。"""
    return svc_get_terminology_options(db)

# --- 术语分类管理 ---
@router.post("/categories", response_model=schemas.TermCategory)
def create_term_category(
    category: schemas.TermCategoryCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """创建术语分类"""
    # 检查权限：只有管理员可以创建公共分类
    if category.owner_type == "public" and current_user.role != models.UserRole.admin:
        raise HTTPException(status_code=403, detail="Only admins can create public categories")
    
    return crud.create_term_category(db=db, category=category, user_id=current_user.id)

@router.get("/categories", response_model=List[schemas.TermCategory])
def read_term_categories(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    owner_type: Optional[str] = Query(None, description="分类所有者类型：public/user/group"),
    owner_id: Optional[int] = Query(None, description="分类所有者ID"),
    is_active: Optional[bool] = Query(None, description="是否启用"),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """获取术语分类列表"""
    # 普通用户只能看到公共分类和自己的分类
    if current_user.role != models.UserRole.admin:
        if owner_type == "public":
            pass  # 允许查看公共分类
        elif owner_type == "user" and owner_id == current_user.id:
            pass  # 允许查看自己的分类
        else:
            # 默认只显示公共分类和用户自己的分类
            categories = crud.get_term_categories(
                db=db, 
                skip=skip, 
                limit=limit,
                owner_type="public",
                include_term_count=True
            )
            # 添加用户自己的分类
            user_categories = crud.get_term_categories(
                db=db,
                skip=0,
                limit=1000,
                owner_type="user",
                owner_id=current_user.id,
                include_term_count=True
            )
            return categories + user_categories
    
    return crud.get_term_categories(
        db=db, 
        skip=skip, 
        limit=limit,
        owner_type=owner_type,
        owner_id=owner_id,
        is_active=is_active,
        include_term_count=True
    )

@router.get("/categories/{category_id}", response_model=schemas.TermCategory)
def read_term_category(
    category_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """获取特定术语分类"""
    category = crud.get_term_category(db, category_id)
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    
    # 权限检查
    if category.owner_type != "public" and category.owner_id != current_user.id and current_user.role != models.UserRole.admin:
        raise HTTPException(status_code=403, detail="Access denied")
    
    return category

@router.put("/categories/{category_id}", response_model=schemas.TermCategory)
def update_term_category(
    category_id: int,
    category_update: schemas.TermCategoryUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """更新术语分类"""
    category = crud.get_term_category(db, category_id)
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    
    # 权限检查
    if category.owner_type != "public" and category.owner_id != current_user.id and current_user.role != models.UserRole.admin:
        raise HTTPException(status_code=403, detail="Access denied")
    
    return crud.update_term_category(db=db, category_id=category_id, category_update=category_update)

@router.delete("/categories/{category_id}", response_model=schemas.TermCategory)
def delete_term_category(
    category_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """删除术语分类"""
    category = crud.get_term_category(db, category_id)
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    
    # 权限检查
    if category.owner_type != "public" and category.owner_id != current_user.id and current_user.role != models.UserRole.admin:
        raise HTTPException(status_code=403, detail="Access denied")
    
    try:
        return crud.delete_term_category(db=db, category_id=category_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/categories/{category_id}/terms", response_model=List[schemas.Terminology])
def read_category_terms(
    category_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """获取分类下的术语列表"""
    category = crud.get_term_category(db, category_id)
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    
    # 权限检查
    if category.owner_type != "public" and category.owner_id != current_user.id and current_user.role != models.UserRole.admin:
        raise HTTPException(status_code=403, detail="Access denied")
    
    terms = crud.get_terms(db=db, skip=skip, limit=limit, category_id=category_id, include_public=True, user_id=current_user.id)
    
    # 附带用户名（仅用于展示）
    users_map = {u.id: u.username for u in db.query(models.User).all()}
    for term in terms:
        term.owner_username = users_map.get(term.user_id, 'public' if term.user_id == 0 else None)
    
    # 附带用户名和分类名
    users_map = {u.id: u.username for u in db.query(models.User).all()}
    categories_map = {c.id: c.name for c in db.query(models.TermCategory).all()}
    for t in terms:
        t.owner_username = users_map.get(t.user_id, 'public' if t.user_id is None else None)
        if t.category_id:
            t.category_name = categories_map.get(t.category_id)
    return terms

# --- 术语管理（扩展支持分类） ---
@router.post("/", response_model=schemas.Terminology)
def create_terminology(
    term: schemas.TerminologyCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """创建术语（支持分类）"""
    # 如果指定了分类，检查分类权限，并决定术语归属（公共/私有）
    if term.category_id:
        category = crud.get_term_category(db, term.category_id)
        if not category:
            raise HTTPException(status_code=404, detail="Category not found")
        if category.owner_type != "public" and category.owner_id != current_user.id and current_user.role != models.UserRole.admin:
            raise HTTPException(status_code=403, detail="Access denied to specified category")
    # 创建术语（当分类为公共分类时，术语将保存为公共术语 user_id=0）
    return crud.create_term(db=db, term=term, user_id=current_user.id)

@router.get("/", response_model=List[schemas.Terminology])
def read_terminologies(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    mine: bool = Query(False, description="是否只显示我的术语"),
    include_public: bool = Query(True, description="是否包含公共术语"),
    category_id: Optional[int] = Query(None, description="按分类过滤"),
    is_active: Optional[bool] = Query(None, description="是否启用"),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """获取术语列表（支持分类过滤）"""
    # 管理员：查看所有术语
    q = db.query(models.Terminology)
    if current_user.role == models.UserRole.admin:
        pass
    else:
        if mine:
            if include_public:
                q = q.filter(or_(models.Terminology.user_id == current_user.id,
                                 models.Terminology.user_id.is_(None)))
            else:
                q = q.filter(models.Terminology.user_id == current_user.id)
        else:
            # 默认返回公共术语 + 当前用户私有术语
            q = q.filter(or_(models.Terminology.user_id.is_(None),
                             models.Terminology.user_id == current_user.id))
    
    # 分类过滤
    if category_id is not None:
        q = q.filter(models.Terminology.category_id == category_id)
    
    # 启用状态过滤
    if is_active is not None:
        q = q.filter(models.Terminology.is_active == is_active)
    
    items = q.offset(skip).limit(limit).all()
    
    # 附带用户名和分类信息（仅用于展示）
    users_map = {u.id: u.username for u in db.query(models.User).all()}
    categories_map = {c.id: c.name for c in db.query(models.TermCategory).all()}
    
    for item in items:
        item.owner_username = users_map.get(item.user_id, 'public' if item.user_id is None else None)
        if item.category_id:
            item.category_name = categories_map.get(item.category_id, 'Unknown')
    
    return items

@router.put("/{term_id}", response_model=schemas.Terminology)
def update_terminology(
    term_id: int,
    term_update: schemas.TerminologyUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """更新术语"""
    # 检查术语是否存在和权限
    existing_term = db.query(models.Terminology).filter(models.Terminology.id == term_id).first()
    if not existing_term:
        raise HTTPException(status_code=404, detail="Term not found")
    
    if existing_term.user_id != current_user.id and current_user.role != models.UserRole.admin:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # 如果更新分类，检查分类权限并根据分类调整术语归属（公共/私有）
    if term_update.category_id and term_update.category_id != existing_term.category_id:
        category = crud.get_term_category(db, term_update.category_id)
        if not category:
            raise HTTPException(status_code=404, detail="Category not found")
        if category.owner_type != "public" and category.owner_id != current_user.id and current_user.role != models.UserRole.admin:
            raise HTTPException(status_code=403, detail="Access denied to specified category")
        # 分类为公共时，强制归属公共术语
        if category.owner_type == "public":
            # 公共术语使用 NULL 表示
            existing_term.user_id = None
            db.commit()
        else:
            # 非公共分类：归属当前用户
            existing_term.user_id = current_user.id
            db.commit()

    return crud.update_term(db=db, term_id=term_id, term_update=term_update)

@router.delete("/{term_id}", response_model=schemas.Terminology)
def delete_terminology(
    term_id: int, 
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """删除术语"""
    # 检查术语是否存在和权限
    existing_term = db.query(models.Terminology).filter(models.Terminology.id == term_id).first()
    if not existing_term:
        raise HTTPException(status_code=404, detail="Term not found")
    
    if existing_term.user_id != current_user.id and current_user.role != models.UserRole.admin:
        raise HTTPException(status_code=403, detail="Access denied")
    
    db_term = crud.delete_term(db, term_id=term_id)
    if db_term is None:
        raise HTTPException(status_code=404, detail="Term not found")
    return db_term
