from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum

# --- Enums ---
class UserRole(str, Enum):
    admin = "admin"
    user = "user"
    moderator = "moderator"

class EngineStatus(str, Enum):
    active = "active"
    inactive = "inactive"
    maintenance = "maintenance"

class QuotaType(str, Enum):
    daily = "daily"
    monthly = "monthly"
    total = "total"

# --- User Management Schemas ---
class UserBase(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: Optional[str] = Field(None, max_length=100)

class UserCreate(UserBase):
    password: str = Field(..., min_length=6)
    role: UserRole = UserRole.user

class UserUpdate(BaseModel):
    username: Optional[str] = Field(None, min_length=3, max_length=50)
    email: Optional[str] = Field(None, max_length=100)
    role: Optional[UserRole] = None
    status: Optional[bool] = None
    is_verified: Optional[bool] = None

class User(UserBase):
    id: int
    role: UserRole
    status: bool
    is_verified: bool
    last_login: Optional[datetime] = None
    create_time: datetime
    update_time: datetime

    class Config:
        from_attributes = True

class UserDetail(User):
    quotas: List["UserQuota"] = []
    api_tokens: List["ApiToken"] = []
    translation_count: int = 0
    last_activity: Optional[datetime] = None

class UserPage(BaseModel):
    users: List[User]
    total: int

class PasswordChangeRequest(BaseModel):
    old_password: str
    new_password: str

class AdminPasswordResetRequest(BaseModel):
    new_password: str

class PasswordPolicy(BaseModel):
    min_length: int = 8
    require_uppercase: bool = True
    require_lowercase: bool = True
    require_digit: bool = True
    require_special: bool = False

# --- Quota Management Schemas ---
class UserQuotaBase(BaseModel):
    quota_type: QuotaType
    limit_value: int = Field(..., ge=0)  # 0表示无限制
    is_active: bool = True

class UserQuotaCreate(UserQuotaBase):
    user_id: int

class UserQuotaUpdate(BaseModel):
    limit_value: Optional[int] = Field(None, ge=0)
    is_active: Optional[bool] = None

class UserQuota(UserQuotaBase):
    id: int
    user_id: int
    used_value: int
    reset_date: Optional[datetime] = None
    create_time: datetime
    update_time: datetime

    class Config:
        from_attributes = True

# --- API Token Management Schemas ---
class ApiTokenBase(BaseModel):
    token_name: str = Field(..., min_length=1, max_length=100)
    permissions: Dict[str, Any] = {}
    rate_limit: int = Field(1000, ge=1)
    expires_at: Optional[datetime] = None

class ApiTokenCreate(ApiTokenBase):
    user_id: int

class ApiTokenUpdate(BaseModel):
    token_name: Optional[str] = Field(None, min_length=1, max_length=100)
    permissions: Optional[Dict[str, Any]] = None
    rate_limit: Optional[int] = Field(None, ge=1)
    is_active: Optional[bool] = None
    expires_at: Optional[datetime] = None

class ApiToken(ApiTokenBase):
    id: int
    user_id: int
    is_active: bool
    last_used: Optional[datetime] = None
    create_time: datetime

    class Config:
        from_attributes = True

# --- Translation Engine Management Schemas ---
class TranslationEngineBase(BaseModel):
    engine_name: str = Field(..., min_length=1, max_length=50)
    display_name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    api_config: Optional[Dict[str, Any]] = None
    status: EngineStatus = EngineStatus.active
    priority: int = Field(0, ge=0)
    rate_limit: int = Field(100, ge=1)
    cost_per_token: float = Field(0.0, ge=0.0)
    supported_languages: List[str] = []
    features: List[str] = []
    is_default: bool = False

class TranslationEngineCreate(TranslationEngineBase):
    pass

class TranslationEngineUpdate(BaseModel):
    display_name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    api_config: Optional[Dict[str, Any]] = None
    status: Optional[EngineStatus] = None
    priority: Optional[int] = Field(None, ge=0)
    rate_limit: Optional[int] = Field(None, ge=1)
    cost_per_token: Optional[float] = Field(None, ge=0.0)
    supported_languages: Optional[List[str]] = None
    features: Optional[List[str]] = None
    is_default: Optional[bool] = None

class TranslationEngine(TranslationEngineBase):
    id: int
    create_time: datetime
    update_time: datetime

    class Config:
        from_attributes = True

# --- Translation Strategy Management Schemas ---
class TranslationStrategyBase(BaseModel):
    strategy_name: str = Field(..., min_length=1, max_length=50)
    display_name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    engine_id: Optional[int] = None
    config: Optional[Dict[str, Any]] = None
    status: bool = True
    priority: int = Field(0, ge=0)
    supported_formats: List[str] = []

class TranslationStrategyCreate(TranslationStrategyBase):
    pass

class TranslationStrategyUpdate(BaseModel):
    display_name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    engine_id: Optional[int] = None
    config: Optional[Dict[str, Any]] = None
    status: Optional[bool] = None
    priority: Optional[int] = Field(None, ge=0)
    supported_formats: Optional[List[str]] = None

class TranslationStrategy(TranslationStrategyBase):
    id: int
    create_time: datetime
    update_time: datetime
    engine: Optional[TranslationEngine] = None

    class Config:
        from_attributes = True

# --- System Settings Management Schemas ---
class SystemSettingBase(BaseModel):
    category: str = Field(..., min_length=1, max_length=50)
    key: str = Field(..., min_length=1, max_length=100)
    value: Optional[str] = None
    value_type: str = "string"
    description: Optional[str] = None
    is_public: bool = False
    is_editable: bool = True

class SystemSettingCreate(SystemSettingBase):
    pass

class SystemSettingUpdate(BaseModel):
    value: Optional[str] = None
    description: Optional[str] = None
    is_public: Optional[bool] = None
    is_editable: Optional[bool] = None

class SystemSetting(SystemSettingBase):
    id: int
    create_time: datetime
    update_time: datetime

    class Config:
        from_attributes = True

# --- Audit Log Schemas ---
class AuditLogBase(BaseModel):
    action: str = Field(..., min_length=1, max_length=100)
    resource_type: str = Field(..., min_length=1, max_length=50)
    resource_id: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None

class AuditLogCreate(AuditLogBase):
    user_id: Optional[int] = None

class AuditLog(AuditLogBase):
    id: int
    user_id: Optional[int] = None
    create_time: datetime

    class Config:
        from_attributes = True

# --- Token Schema ---
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None

# --- Base Schemas ---
class TextTranslationBase(BaseModel):
    source_text: str
    translated_text: str
    source_lang: str
    target_lang: str
    engine: Optional[str] = None

class TextTranslationCreate(TextTranslationBase):
    pass

class TextTranslation(TextTranslationBase):
    id: int
    create_time: datetime
    username: Optional[str] = None  # 添加用户名字段
    term_category_ids: Optional[List[int]] = None
    engine_params: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True

class TranslationTaskBase(BaseModel):
    task_id: str
    user_id: Optional[int] = None
    username: Optional[str] = None  # 添加用户名字段
    file_name: Optional[str] = None
    file_type: Optional[str] = None
    source_lang: str
    target_lang: str
    status: str
    result_path: Optional[str] = None
    error_message: Optional[str] = None
    # Enhanced metadata fields
    source_file_size: Optional[int] = None
    target_file_size: Optional[int] = None
    character_count: Optional[int] = None
    token_count: Optional[int] = None
    duration: Optional[float] = None
    engine: Optional[str] = None
    strategy: Optional[str] = None
    engine_params: Optional[Dict[str, Any]] = None
    # Extended analytics (optional)
    total_texts: Optional[int] = None
    translated_texts: Optional[int] = None
    qwen3_total: Optional[int] = None
    qwen3_success: Optional[int] = None
    qwen3_429: Optional[int] = None

class TranslationTaskCreate(TranslationTaskBase):
    pass

class TranslationTask(TranslationTaskBase):
    create_time: datetime
    term_category_ids: Optional[List[int]] = None

    class Config:
        from_attributes = True

class TranslationTaskPage(BaseModel):
    items: List[TranslationTask]
    total: int

# --- Combined History Schema ---
class HistoryItem(BaseModel):
    type: str  # 'text' or 'document'
    id: str  # task_id for documents, id for text
    user_id: Optional[int] = None
    status: Optional[str] = None # Status for document tasks
    source_content: str  # file_name for documents, source_text for text
    source_url: Optional[str] = None # URL for source document
    target_content: Optional[str] = None # result_path for documents, translated_text for text
    target_url: Optional[str] = None # URL for translated document
    source_lang: str
    target_lang: str
    create_time: datetime
    error_message: Optional[str] = None
    # Enhanced metadata fields
    source_file_size: Optional[int] = None
    target_file_size: Optional[int] = None
    character_count: Optional[int] = None
    token_count: Optional[int] = None
    duration: Optional[float] = None
    engine: Optional[str] = None
    strategy: Optional[str] = None
    engine_params: Optional[Dict[str, Any]] = None

# --- Terminology Schemas ---
class TermCategoryBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    owner_type: str = Field(default="public", pattern="^(public|user|group)$")
    owner_id: Optional[int] = None
    is_active: bool = True
    sort_order: int = Field(default=0, ge=0)

class TermCategoryCreate(TermCategoryBase):
    pass

class TermCategoryUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    is_active: Optional[bool] = None
    sort_order: Optional[int] = Field(None, ge=0)

class TermCategory(TermCategoryBase):
    id: int
    create_time: datetime
    update_time: datetime
    term_count: Optional[int] = None  # 分类下的术语数量

    class Config:
        from_attributes = True

class TerminologyBase(BaseModel):
    source_text: str
    target_text: str
    source_lang: str
    target_lang: str
    category_id: Optional[int] = None
    is_active: bool = True

class TerminologyCreate(TerminologyBase):
    pass

class TerminologyUpdate(BaseModel):
    source_text: Optional[str] = None
    target_text: Optional[str] = None
    source_lang: Optional[str] = None
    target_lang: Optional[str] = None
    category_id: Optional[int] = None
    is_active: Optional[bool] = None

class Terminology(TerminologyBase):
    id: int
    user_id: int | None = None
    is_approved: bool | None = True
    owner_username: str | None = None
    category_name: Optional[str] = None
    category: Optional[TermCategory] = None

    class Config:
        from_attributes = True

class TranslationTermSetBase(BaseModel):
    translation_id: str
    translation_type: str = Field(..., pattern="^(text|document)$")
    category_ids: Optional[List[int]] = None

class TranslationTermSetCreate(TranslationTermSetBase):
    pass

class TranslationTermSet(TranslationTermSetBase):
    id: int
    create_time: datetime

    class Config:
        from_attributes = True

# --- Dashboard and Statistics Schemas ---
class DashboardStats(BaseModel):
    total_users: int
    active_users: int
    total_translations: int
    total_tasks: int
    pending_tasks: int
    completed_tasks: int
    failed_tasks: int
    system_health: str
    active_engines: int
    total_quotas: int

class UserStats(BaseModel):
    user_id: int
    username: str
    translation_count: int
    task_count: int
    quota_usage: Dict[str, int]
    last_activity: Optional[datetime] = None

# --- Pagination and Response Schemas ---
class PaginatedResponse(BaseModel):
    items: List[Any]
    total: int
    page: int
    size: int
    pages: int

class SuccessResponse(BaseModel):
    success: bool = True
    message: str
    data: Optional[Any] = None

class ErrorResponse(BaseModel):
    success: bool = False
    error: str
    details: Optional[Any] = None