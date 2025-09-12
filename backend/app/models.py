from sqlalchemy import Column, Integer, String, Text, DateTime, Enum, Boolean, Float, func, ForeignKey, JSON
from sqlalchemy.orm import relationship, declarative_base
import enum

Base = declarative_base()

class UserRole(str, enum.Enum):
    admin = "admin"
    user = "user"
    moderator = "moderator"  # 新增：版主角色

class TaskStatus(str, enum.Enum):
    pending = "pending"
    processing = "processing"
    completed = "completed"
    failed = "failed"

class RuleType(str, enum.Enum):
    keyword = "KEYWORD"
    regex = "REGEX"

class EngineStatus(str, enum.Enum):
    active = "active"
    inactive = "inactive"
    maintenance = "maintenance"

class QuotaType(str, enum.Enum):
    daily = "daily"
    monthly = "monthly"
    total = "total"

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=True)
    password = Column(String(100), nullable=False)
    role = Column(Enum(UserRole), default=UserRole.user, nullable=False)
    status = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    last_login = Column(DateTime(timezone=True), nullable=True)
    create_time = Column(DateTime(timezone=True), server_default=func.now())
    update_time = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # 关联关系
    quotas = relationship("UserQuota", back_populates="user")
    api_tokens = relationship("ApiToken", back_populates="user")
    translation_tasks = relationship("TranslationTask", back_populates="user")
    text_translations = relationship("TextTranslation", back_populates="user")
    # 多对多：用户-用户组
    groups = relationship("Group", secondary="user_groups", back_populates="users")

class Group(Base):
    __tablename__ = "groups"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)
    create_time = Column(DateTime(timezone=True), server_default=func.now())
    update_time = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    # 关系
    users = relationship("User", secondary="user_groups", back_populates="groups")

class UserGroup(Base):
    __tablename__ = "user_groups"
    user_id = Column(Integer, ForeignKey("users.id"), primary_key=True)
    group_id = Column(Integer, ForeignKey("groups.id"), primary_key=True)

class UserQuota(Base):
    __tablename__ = "user_quotas"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    quota_type = Column(Enum(QuotaType), nullable=False)
    limit_value = Column(Integer, default=0)  # 0表示无限制
    used_value = Column(Integer, default=0)
    reset_date = Column(DateTime(timezone=True), nullable=True)
    is_active = Column(Boolean, default=True)
    create_time = Column(DateTime(timezone=True), server_default=func.now())
    update_time = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # 关联关系
    user = relationship("User", back_populates="quotas")

class ApiToken(Base):
    __tablename__ = "api_tokens"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    token_name = Column(String(100), nullable=False)
    token_hash = Column(String(255), nullable=False)
    permissions = Column(JSON, default={})  # 权限配置
    rate_limit = Column(Integer, default=1000)  # 每分钟请求限制
    is_active = Column(Boolean, default=True)
    last_used = Column(DateTime(timezone=True), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    create_time = Column(DateTime(timezone=True), server_default=func.now())
    
    # 关联关系
    user = relationship("User", back_populates="api_tokens")

class TranslationEngine(Base):
    __tablename__ = "translation_engines"
    id = Column(Integer, primary_key=True, index=True)
    engine_name = Column(String(50), unique=True, nullable=False)
    display_name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    api_config = Column(JSON, nullable=True)  # API配置信息
    status = Column(Enum(EngineStatus), default=EngineStatus.active)
    priority = Column(Integer, default=0)  # 优先级，数字越小优先级越高
    rate_limit = Column(Integer, default=100)  # 每分钟请求限制
    cost_per_token = Column(Float, default=0.0)  # 每token的成本
    supported_languages = Column(JSON, default=[])  # 支持的语言列表
    features = Column(JSON, default=[])  # 支持的功能特性
    is_default = Column(Boolean, default=False)  # 是否为默认引擎
    create_time = Column(DateTime(timezone=True), server_default=func.now())
    update_time = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

class TranslationStrategy(Base):
    __tablename__ = "translation_strategies"
    id = Column(Integer, primary_key=True, index=True)
    strategy_name = Column(String(50), unique=True, nullable=False)
    display_name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    engine_id = Column(Integer, ForeignKey("translation_engines.id"), nullable=True)
    config = Column(JSON, nullable=True)  # 策略配置
    status = Column(Boolean, default=True)
    priority = Column(Integer, default=0)
    supported_formats = Column(JSON, default=[])  # 支持的文件格式
    create_time = Column(DateTime(timezone=True), server_default=func.now())
    update_time = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # 关联关系
    engine = relationship("TranslationEngine")

class SystemSetting(Base):
    __tablename__ = "system_settings"
    id = Column(Integer, primary_key=True, index=True)
    category = Column(String(50), nullable=False)  # 设置分类
    key = Column(String(100), nullable=False)
    value = Column(Text, nullable=True)
    value_type = Column(String(20), default="string")  # string, int, float, bool, json
    description = Column(Text, nullable=True)
    is_public = Column(Boolean, default=False)  # 是否公开可见
    is_editable = Column(Boolean, default=True)  # 是否可编辑
    create_time = Column(DateTime(timezone=True), server_default=func.now())
    update_time = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

class AuditLog(Base):
    __tablename__ = "audit_logs"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    action = Column(String(100), nullable=False)  # 操作类型
    resource_type = Column(String(50), nullable=False)  # 资源类型
    resource_id = Column(String(100), nullable=True)  # 资源ID
    details = Column(JSON, nullable=True)  # 操作详情
    ip_address = Column(String(45), nullable=True)  # IP地址
    user_agent = Column(Text, nullable=True)  # 用户代理
    create_time = Column(DateTime(timezone=True), server_default=func.now())

class Terminology(Base):
    __tablename__ = "terminologies"
    id = Column(Integer, primary_key=True, index=True)
    source_text = Column(String(200), nullable=False)
    target_text = Column(String(200), nullable=False)
    source_lang = Column(String(10), nullable=False)
    target_lang = Column(String(10), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, comment="NULL for public terminology")
    category_id = Column(Integer, ForeignKey("term_categories.id"), nullable=True, comment="术语分类ID")
    is_approved = Column(Boolean, default=True)
    approval_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    approval_time = Column(DateTime(timezone=True), nullable=True)
    is_active = Column(Boolean, default=True, comment="术语是否启用")
    create_time = Column(DateTime(timezone=True), server_default=func.now())
    update_time = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # 关联关系
    category = relationship("TermCategory", back_populates="terms")

class TermCategory(Base):
    __tablename__ = "term_categories"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, comment="分类名称")
    description = Column(Text, nullable=True, comment="分类描述")
    owner_type = Column(String(20), default="public", comment="public/user/group")
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=True, comment="所有者ID")
    is_active = Column(Boolean, default=True, comment="是否启用")
    sort_order = Column(Integer, default=0, comment="排序")
    create_time = Column(DateTime(timezone=True), server_default=func.now())
    update_time = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # 关联关系
    owner = relationship("User")
    terms = relationship("Terminology", back_populates="category")

class TranslationTermSet(Base):
    __tablename__ = "translation_term_sets"
    id = Column(Integer, primary_key=True, index=True)
    translation_id = Column(String(100), nullable=False, comment="翻译记录ID")
    translation_type = Column(String(20), nullable=False, comment="翻译类型：text/document")
    category_ids = Column(JSON, nullable=True, comment="使用的分类ID数组")
    create_time = Column(DateTime(timezone=True), server_default=func.now())

class TranslationTask(Base):
    __tablename__ = "translation_tasks"
    task_id = Column(String(36), primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True)
    file_name = Column(String(255))
    file_type = Column(String(10))
    source_lang = Column(String(10))
    target_lang = Column(String(10))
    status = Column(Enum(TaskStatus), default=TaskStatus.pending)
    progress = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)
    result_path = Column(String(255), nullable=True)
    create_time = Column(DateTime(timezone=True), server_default=func.now())
    expire_time = Column(DateTime, nullable=True)
    # Enhanced metadata fields
    source_file_size = Column(Integer, nullable=True)
    target_file_size = Column(Integer, nullable=True)
    character_count = Column(Integer, nullable=True)
    token_count = Column(Integer, nullable=True)
    duration = Column(Float, nullable=True)  # Store duration in seconds
    engine = Column(String(50), nullable=True)  # e.g., 'deepseek'
    strategy = Column(String(50), nullable=True)  # e.g., 'ooxml_direct'
    engine_params = Column(JSON, nullable=True)  # 运行参数审计（model/max_workers/batch_size/retry/sleep/timeout/style等）
    
    # 关联关系
    user = relationship("User", back_populates="translation_tasks")

class TextTranslation(Base):
    __tablename__ = "text_translations"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True)
    source_text = Column(Text, nullable=False)
    translated_text = Column(Text, nullable=False)
    source_lang = Column(String(10))
    target_lang = Column(String(10))
    engine = Column(String(50), nullable=True)  # 添加engine字段
    create_time = Column(DateTime(timezone=True), server_default=func.now())
    
    # 关联关系
    user = relationship("User", back_populates="text_translations")

class TextTranslationMeta(Base):
    __tablename__ = "text_translation_meta"
    id = Column(Integer, primary_key=True, index=True)
    text_id = Column(Integer, ForeignKey("text_translations.id"), index=True, nullable=False)
    token_count = Column(Integer, nullable=True)
    character_count = Column(Integer, nullable=True)
    byte_count = Column(Integer, nullable=True)
    duration = Column(Float, nullable=True)
    engine_params = Column(JSON, nullable=True)
    create_time = Column(DateTime(timezone=True), server_default=func.now())

# --- Batch Translation ---
class BatchJob(Base):
    __tablename__ = "batch_jobs"
    batch_id = Column(String(36), primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=True)
    create_time = Column(DateTime(timezone=True), server_default=func.now())

class BatchItem(Base):
    __tablename__ = "batch_items"
    id = Column(Integer, primary_key=True, index=True)
    batch_id = Column(String(36), ForeignKey("batch_jobs.batch_id"), index=True, nullable=False)
    task_id = Column(String(36), ForeignKey("translation_tasks.task_id"), index=True, nullable=False)
    create_time = Column(DateTime(timezone=True), server_default=func.now())

class BatchMetrics(Base):
    __tablename__ = "batch_metrics"
    batch_id = Column(String(36), primary_key=True, index=True)
    total = Column(Integer, default=0)
    completed = Column(Integer, default=0)
    failed = Column(Integer, default=0)
    tokens = Column(Integer, default=0)
    update_time = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

class SensitiveRule(Base):
    __tablename__ = "sensitive_rules"
    id = Column(Integer, primary_key=True, index=True)
    rule_name = Column(String(100), nullable=False)
    rule_type = Column(Enum(RuleType), nullable=False)
    pattern = Column(Text, nullable=False)
    is_predefined = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    created_by = Column(String(50))
    create_time = Column(DateTime(timezone=True), server_default=func.now())
    update_time = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

class Setting(Base):
    __tablename__ = "settings"
    key = Column(String(50), primary_key=True, index=True)
    value = Column(String(255), nullable=False)
