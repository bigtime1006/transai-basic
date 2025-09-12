from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Body, APIRouter, Depends, BackgroundTasks, Query
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import or_
from celery.result import AsyncResult
import os
import requests
import re
import traceback
from urllib.parse import quote
from dotenv import load_dotenv
from typing import Dict, List, Optional
import logging
import time
from datetime import timedelta
import uuid
import shutil
from datetime import datetime
import threading
import json

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables from .env file
load_dotenv()

# --- Database Imports and Initialization ---
from . import models, schemas, crud
from .database import engine, get_db, SessionLocal
from .routers import terminology, users, auth, admin
from .services.engine_config import EngineConfig
from .worker import translate_document_task, process_translation_task, process_batch_translation_task, celery_app
from .auth import get_current_active_user, get_password_hash
from .services.terminology_service import (
    get_terminology_options,
    preprocess_texts,
    postprocess_texts,
    record_translation_term_set,
)

# --- Database Initialization Functions ---
def create_default_admin():
    """创建默认管理员用户"""
    db = SessionLocal()
    try:
        existing_admin = db.query(models.User).filter(models.User.username == "admin").first()
        if not existing_admin:
            admin_user = models.User(
                username="admin",
                email="admin@transai.com",
                password=get_password_hash("admin123"),
                role=models.UserRole.admin,
                status=True,
                is_verified=True
            )
            db.add(admin_user)
            db.commit()
            print("默认管理员用户创建成功: admin/admin123")
        else:
            print("管理员用户已存在")
    finally:
        db.close()

def create_default_settings():
    """创建默认系统设置"""
    db = SessionLocal()
    try:
        existing_settings = db.query(models.SystemSetting).count()
        if existing_settings == 0:
            default_settings = [
                models.SystemSetting(category="security", key="allow_registration", value="true", value_type="bool", description="是否允许用户注册"),
                # Terminology minimal switches
                models.SystemSetting(category="terminology", key="terminology_enabled", value="true", value_type="bool", description="是否启用术语前/后处理"),
                models.SystemSetting(category="terminology", key="terminology_case_sensitive", value="false", value_type="bool", description="术语匹配大小写敏感"),
                # History limits per user (separate)
                models.SystemSetting(category="history", key="max_text_items_per_user", value="1000", value_type="int", description="每个用户文本历史记录上限"),
                models.SystemSetting(category="history", key="max_doc_items_per_user", value="1000", value_type="int", description="每个用户文档历史记录上限"),
                models.SystemSetting(category="history", key="frontend_delete_permanent", value="true", value_type="bool", description="小历史删除是否等同后台删除"),
                models.SystemSetting(category="history", key="text_retention_days", value="30", value_type="int", description="文本历史保留天数"),
                models.SystemSetting(category="history", key="doc_retention_days", value="30", value_type="int", description="文档历史保留天数（含文件）"),
                # OOXML processing toggles
                models.SystemSetting(category="ooxml", key="pptx_use_ooxml", value="true", value_type="bool", description="PPTX 使用 OOXML 级替换（推荐）"),
                models.SystemSetting(category="ooxml", key="xlsx_use_ooxml", value="true", value_type="bool", description="XLSX 使用 OOXML 级替换（推荐）"),
                models.SystemSetting(category="ooxml", key="docx_parallel_workers", value="6", value_type="int", description="DOCX 解析并行工作线程数"),
                models.SystemSetting(category="ooxml", key="docx_collect_tokens", value="false", value_type="bool", description="DOCX 启用顺序模式以精确统计 tokens"),
            ]
            db.add_all(default_settings)
            db.commit()
            print("默认系统设置创建成功")
        else:
            # ensure terminology keys exist
            keys = {
                "terminology_enabled": ("terminology", "true", "bool", "是否启用术语前/后处理"),
                "terminology_case_sensitive": ("terminology", "false", "bool", "术语匹配大小写敏感"),
                "max_text_items_per_user": ("history", "1000", "int", "每个用户文本历史记录上限"),
                "max_doc_items_per_user": ("history", "1000", "int", "每个用户文档历史记录上限"),
                "frontend_delete_permanent": ("history", "true", "bool", "小历史删除是否等同后台删除"),
                "text_retention_days": ("history", "30", "int", "文本历史保留天数"),
                "doc_retention_days": ("history", "30", "int", "文档历史保留天数（含文件）"),
                # OOXML toggles
                "pptx_use_ooxml": ("ooxml", "true", "bool", "PPTX 使用 OOXML 级替换（推荐）"),
                "xlsx_use_ooxml": ("ooxml", "true", "bool", "XLSX 使用 OOXML 级替换（推荐）"),
                "docx_parallel_workers": ("ooxml", "6", "int", "DOCX 解析并行工作线程数"),
                "docx_collect_tokens": ("ooxml", "false", "bool", "DOCX 启用顺序模式以精确统计 tokens"),
            }
            created = 0
            for k, (cat, val, vtype, desc) in keys.items():
                if not crud.get_system_setting_by_key(db, k):
                    db.add(models.SystemSetting(category=cat, key=k, value=val, value_type=vtype, description=desc))
                    created += 1
            if created:
                db.commit()
                print(f"补充创建术语相关系统设置 {created} 项")
            else:
                print("系统设置已存在")
    finally:
        db.close()

def create_default_engines():
    """根据当前环境配置创建默认翻译引擎（deepseek/kimi/youdao），如不存在则插入"""
    db = SessionLocal()
    try:
        engines_to_seed = [
            {
                "engine_name": "deepseek",
                "display_name": "DeepSeek",
                "description": "DeepSeek Chat Completions",
                "config_getter": EngineConfig.get_deepseek_config,
                "features": ["text_translation", "document_translation", "json_format", "batch_translation"],
                "priority": 0,
                "rate_limit": 60,
                "cost_per_token": 0.0,
                "supported_languages": ["zh", "en", "ja", "ko", "fr", "de", "es", "ru"],
            },
            {
                "engine_name": "qwen3",
                "display_name": "Qwen3",
                "description": "Alibaba Qwen3 Compatible Completions",
                "config_getter": EngineConfig.get_qwen3_config,
                "features": ["text_translation", "document_translation", "batch_translation"],
                "priority": 3,
                "rate_limit": 90,
                "cost_per_token": 0.0,
                "supported_languages": ["zh", "en", "ja", "ko"],
            },
            {
                "engine_name": "qwen_plus",
                "display_name": "Qwen Plus",
                "description": "Alibaba Qwen Plus Chat Completions",
                "config_getter": EngineConfig.get_qwen_plus_config,
                "features": ["text_translation", "document_translation", "batch_translation"],
                "priority": 2,
                "rate_limit": 1000,
                "cost_per_token": 0.0,
                "supported_languages": ["zh", "en", "ja", "ko", "fr", "de", "es"],
            },
            {
                "engine_name": "tencent",
                "display_name": "Tencent TMT",
                "description": "Tencent Machine Translation",
                "config_getter": EngineConfig.get_tencent_config,
                "features": ["text_translation", "batch_translation"],
                "priority": 5,
                "rate_limit": 60,
                "cost_per_token": 0.0,
                "supported_languages": ["zh", "en", "ja", "ko"],
            },
            {
                "engine_name": "kimi",
                "display_name": "Kimi (Moonshot)",
                "description": "Kimi API",
                "config_getter": EngineConfig.get_kimi_config,
                "features": ["text_translation", "batch_translation"],
                "priority": 10,
                "rate_limit": 30,
                "cost_per_token": 0.0,
                "supported_languages": ["zh", "en", "ja", "ko"],
            },
            {
                "engine_name": "youdao",
                "display_name": "Youdao",
                "description": "Youdao OpenAPI",
                "config_getter": EngineConfig.get_youdao_config,
                "features": ["text_translation"],
                "priority": 20,
                "rate_limit": 60,
                "cost_per_token": 0.0,
                "supported_languages": ["zh", "en", "ja", "ko"],
            },
        ]

        for info in engines_to_seed:
            existing = db.query(models.TranslationEngine).filter(
                models.TranslationEngine.engine_name == info["engine_name"]
            ).first()
            if existing:
                continue

            api_config = info["config_getter"]()
            is_available = EngineConfig.is_engine_available(info["engine_name"])

            engine = models.TranslationEngine(
                engine_name=info["engine_name"],
                display_name=info["display_name"],
                description=info["description"],
                api_config=api_config,
                status=models.EngineStatus.active if is_available else models.EngineStatus.inactive,
                priority=info["priority"],
                rate_limit=info["rate_limit"],
                cost_per_token=info["cost_per_token"],
                supported_languages=info["supported_languages"],
                features=info["features"],
                is_default=False,
            )
            db.add(engine)

        # 提交插入
        db.commit()

        # 设置默认引擎（可用优先 deepseek）
        default_name = EngineConfig.get_default_engine()
        default_engine = db.query(models.TranslationEngine).filter(
            models.TranslationEngine.engine_name == default_name
        ).first()
        if default_engine and not default_engine.is_default:
            default_engine.is_default = True
            db.commit()
    except Exception as e:
        print(f"默认引擎创建失败: {e}")
        db.rollback()
    finally:
        db.close()

def create_default_strategies():
    """创建默认翻译策略：text_direct, ooxml_direct, aspose(禁用)"""
    db = SessionLocal()
    try:
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
            existing = db.query(models.TranslationStrategy).filter(
                models.TranslationStrategy.strategy_name == s["strategy_name"],
            ).first()
            if existing:
                continue
            strategy = models.TranslationStrategy(
                strategy_name=s["strategy_name"],
                display_name=s["display_name"],
                description=s.get("description"),
                engine_id=None,
                config=None,
                status=s["status"],
                priority=s["priority"],
                supported_formats=s["supported_formats"],
            )
            db.add(strategy)
        db.commit()
    except Exception as e:
        print(f"默认策略创建失败: {e}")
        db.rollback()
    finally:
        db.close()

def init_db():
    """初始化数据库"""
    try:
        models.Base.metadata.create_all(bind=engine)
        print("数据库表创建成功")
        create_default_admin()
        create_default_settings()
        create_default_engines()
        create_default_strategies()
        print("数据库初始化完成")
    except Exception as e:
        print(f"数据库初始化失败: {e}")
        raise e

# --- FastAPI App and CORS Middleware Setup ---
app = FastAPI(title="TransAI API", version="1.0.0")

origins = ["http://localhost", "http://localhost:5173", "http://127.0.0.1:5173"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 挂载静态文件目录
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")
app.mount("/downloads", StaticFiles(directory="downloads"), name="downloads")

# 启动事件
@app.on_event("startup")
async def startup_event():
    """应用启动时执行"""
    print("正在初始化数据库...")
    init_db()
    print("数据库初始化完成")

# --- Test endpoints ---
@app.get("/")
def read_root():
    return {"message": "Translator API is running."}

@app.get("/test")
def test_endpoint():
    return {"message": "Test endpoint is working"}

@app.post("/test-post")
async def test_post_endpoint(payload: Dict = Body(...)):
    return {"message": "POST endpoint is working", "data": payload}

# 测试端点已移除，避免生成无用的历史记录
# @app.get("/test-deepseek")
# async def test_deepseek():
#     """测试DeepSeek API连接"""
#     # 此端点会生成历史记录，已移除

api_router = APIRouter(prefix="/api")

# --- Constants and Directories ---
UPLOAD_DIR = "uploads"
DOWNLOAD_DIR = "downloads"
MAX_TEXT_BYTES = int(os.getenv("MAX_TEXT_TRANSLATION_BYTES", 5000))

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# --- Helper Function for Sanitizing Filenames ---
def sanitize_filename(filename: str) -> str:
    """保留常见字符与中文，去掉不安全字符。"""
    filename = filename.replace(" ", "_")
    # 允许中文范围 \u4e00-\u9fa5 及常见全角数字字母（可按需扩展）
    return re.sub(r'[^\w\-\.\u4e00-\u9fa5]', '', filename)

# --- API Endpoints ---

@api_router.post("/translate/document")
async def translate_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    source_lang: str = Form(...),
    target_lang: str = Form(...),
    engine: str = Form("deepseek"),
    strategy: str = Form("ooxml_direct"),
    category_ids: Optional[str] = Form(None),
    style_instruction: Optional[str] = Form(None),
    style_preset: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    logger.info(f"Document translation request received: {file.filename}, {source_lang} -> {target_lang}")
    logger.info(f"Translation params: strategy={strategy}, engine={engine}")
    
    try:
        filename = os.path.basename(file.filename)
        file_path = os.path.join(UPLOAD_DIR, filename)
        
        logger.info(f"Saving uploaded file to: {file_path}")
        with open(file_path, "wb") as buffer:
            buffer.write(await file.read())

        file_name_without_ext, file_ext = os.path.splitext(filename)
        sanitized_base_name = sanitize_filename(file_name_without_ext)
        output_filename = f"{sanitized_base_name}_translated{file_ext}"
        output_path = os.path.join(DOWNLOAD_DIR, output_filename)
        
        logger.info(f"Output file path: {output_path}")

        # Calculate source file size
        source_file_size = os.path.getsize(file_path) if os.path.exists(file_path) else None
        logger.info(f"Source file size: {source_file_size} bytes")
        
        logger.info("Creating Celery translation task...")

        # 解析术语分类ID
        parsed_category_ids: Optional[List[int]] = None
        try:
            if category_ids:
                import json as _json
                val = _json.loads(category_ids)
                if isinstance(val, list):
                    parsed_category_ids = [int(x) for x in val if str(x).isdigit()]
        except Exception:
            parsed_category_ids = None

        # 历史上限校验（文档）
        try:
            max_doc = crud.get_system_setting_by_key(db, "max_doc_items_per_user")
            max_doc_val = int(max_doc.value) if max_doc and str(max_doc.value).isdigit() else 1000
            # 仅统计仍有文件的记录，已清理(file_name/result_path 均为空)的不计入
            current_doc = db.query(models.TranslationTask).filter(
                models.TranslationTask.user_id == current_user.id,
                or_(models.TranslationTask.file_name.isnot(None), models.TranslationTask.result_path.isnot(None))
            ).count()
            if current_doc >= max_doc_val:
                raise HTTPException(status_code=409, detail=f"文档历史已达上限({max_doc_val})，请先删除部分记录后再提交")
        except HTTPException:
            raise
        except Exception:
            pass
        task_id_str = str(uuid.uuid4())
        translate_document_task.apply_async(
            kwargs=dict(
                task_id=task_id_str,
                file_path=file_path,
                output_path=output_path,
                source_lang=source_lang,
                target_lang=target_lang,
                engine=engine,
                strategy=strategy,
                category_ids=parsed_category_ids,
                style_instruction=style_instruction,
                style_preset=style_preset,
            ),
            task_id=task_id_str,
        )

        # 记录初始 engine_params （基础配置，便于审计）
        try:
            from .services.engine_config import EngineConfig
            base_cfg = {}
            if engine in ("qwen_plus","qwen-plus"):
                base_cfg = EngineConfig.get_qwen_plus_config()
            elif engine == "qwen3":
                base_cfg = EngineConfig.get_qwen3_config()
            elif engine == "deepseek":
                base_cfg = EngineConfig.get_deepseek_config()
            elif engine == "kimi":
                base_cfg = EngineConfig.get_kimi_config()
            elif engine == "tencent":
                base_cfg = EngineConfig.get_tencent_config()
            elif engine == "youdao":
                base_cfg = EngineConfig.get_youdao_config()
        except Exception:
            base_cfg = {}

        task_data = schemas.TranslationTaskCreate(
            task_id=task_id_str,
            user_id=current_user.id,  # 添加用户ID
            file_name=filename,
            file_type=file_ext,
            source_lang=source_lang,
            target_lang=target_lang,
            status='pending',
            result_path=output_path,
            source_file_size=source_file_size,
            engine=engine,
            strategy=strategy
        )
        crud.create_or_update_translation_task(db=db, task=task_data)
        logger.info(f"Translation task created successfully: {task_id_str}")

        # 将 engine_params 写入列，同时保留在 error_message(JSON) 中以向后兼容
        try:
            import json as _json
            engine_params = {
                "engine": engine,
                "model": base_cfg.get('model'),
                "max_workers": base_cfg.get('max_workers'),
                "batch_size": base_cfg.get('batch_size'),
                "retry_max": base_cfg.get('retry_max'),
                "sleep_between_requests": base_cfg.get('sleep_between_requests'),
                "timeout": base_cfg.get('timeout'),
            }
            if style_preset:
                engine_params["style_preset"] = style_preset
            if style_instruction:
                engine_params["style_instruction"] = style_instruction[:300]
            task = crud.get_translation_task(db, task_id_str)
            prev = {}
            try:
                if task and task.error_message and task.error_message.strip().startswith('{'):
                    prev = _json.loads(task.error_message)
            except Exception:
                prev = {}
            prev.update({"engine_params": engine_params})
            crud.update_translation_task(db, task_id_str, {"error_message": _json.dumps(prev, ensure_ascii=False), "engine_params": engine_params})
        except Exception:
            pass

        # 记录本次任务使用的术语分类（如有）
        try:
            if parsed_category_ids:
                record_translation_term_set(db, task_id_str, "document", parsed_category_ids)
        except Exception as _e:
            logger.warning(f"record_translation_term_set failed: {_e}")

        # 在后台处理翻译任务
        background_tasks.add_task(
            process_translation_task,
            task_id=task_id_str,
            file_path=file_path,
            output_path=output_path,
            source_lang=source_lang,
            target_lang=target_lang,
            engine=engine,
            strategy=strategy,
            category_ids=parsed_category_ids,
            style_instruction=style_instruction,
            style_preset=style_preset,
        )

        return JSONResponse(content={"task_id": task_id_str})
    except Exception as e:
        logger.error(f"Document translation failed: {str(e)}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/translate/text")
async def translate_text(payload: Dict = Body(...), db: Session = Depends(get_db), current_user: models.User = Depends(get_current_active_user)):
    logger.info(f"Text translation request received: {payload.get('source_lang', 'auto')} -> {payload.get('target_lang', 'en')}")
    
    text = payload.get("text", "")
    source_lang = payload.get("source_lang", "auto")
    target_lang = payload.get("target_lang", "en")
    engine = payload.get("engine", "deepseek")
    category_ids = payload.get("category_ids", None)
    # 风格与启发式（文本可用）
    style_instruction = payload.get("style_instruction")
    style_preset = payload.get("style_preset")
    enable_thinking = bool(payload.get("enable_thinking", False))

    logger.info(f"Processing text translation: length={len(text)}, engine={engine}")

    if not text.strip():
        logger.warning("Empty text received")
        return JSONResponse(content={"translated_text": ""})

    if len(text.encode('utf-8')) > MAX_TEXT_BYTES:
        logger.error(f"Text exceeds size limit: {len(text.encode('utf-8'))} > {MAX_TEXT_BYTES}")
        raise HTTPException(status_code=413, detail=f"Text exceeds the maximum allowed size of {MAX_TEXT_BYTES} bytes.")

    try:
        logger.info("Starting translation process...")
        start_time = time.time()
        
        # 历史上限校验（文本）
        try:
            max_text = crud.get_system_setting_by_key(db, "max_text_items_per_user")
            max_text_val = int(max_text.value) if max_text and str(max_text.value).isdigit() else 1000
            # 仅统计“有效”文本历史：源/译文本至少一个非空
            current_text = (
                db.query(models.TextTranslation)
                .filter(models.TextTranslation.user_id == current_user.id)
                .filter(
                    or_(
                        models.TextTranslation.source_text.isnot(None) & (models.TextTranslation.source_text != ""),
                        models.TextTranslation.translated_text.isnot(None) & (models.TextTranslation.translated_text != ""),
                    )
                )
                .count()
            )
            if current_text >= max_text_val:
                raise HTTPException(status_code=409, detail=f"文本历史已达上限({max_text_val})，请先删除部分记录后再提交")
        except HTTPException:
            raise
        except Exception:
            pass

        # 使用新的多引擎翻译器
        from .services.multi_engine_translator import translate_batch

        # 术语前处理（支持术语分类）
        options = get_terminology_options(db)
        texts = [text]
        if options.get("terminology_enabled", True):
            # 当 categories_enabled=true 且明确传入 category_ids 时：
            # - 非空数组 -> 按分类处理
            # - 空数组   -> 禁用术语处理
            # 未传入时，保持旧逻辑（全量术语）
            use_categories_param = (category_ids is not None)
            if use_categories_param:
                if isinstance(category_ids, list) and len(category_ids) > 0:
                    from .services.terminology_service import preprocess_texts_with_categories
                    processed_texts, mappings = preprocess_texts_with_categories(
                        db,
                        texts,
                        source_lang,
                        target_lang,
                        category_ids,
                        case_sensitive=bool(options.get("case_sensitive", False)),
                        user_id=current_user.id if current_user and hasattr(current_user, 'id') else None,
                    )
                else:
                    processed_texts, mappings = texts, [{}]
            else:
                processed_texts, mappings = preprocess_texts(
                    db,
                    texts,
                    source_lang,
                    target_lang,
                    case_sensitive=bool(options.get("case_sensitive", False)),
                    user_id=current_user.id if current_user and hasattr(current_user, 'id') else None,
                )
        else:
            processed_texts, mappings = texts, [{}]

        # 调用引擎翻译（透传风格/指令/启发式）
        extra_kwargs = {}
        if style_instruction:
            extra_kwargs['style_instruction'] = style_instruction
        if style_preset:
            extra_kwargs['style_preset'] = style_preset
        if engine in ("qwen_plus","qwen-plus","deepseek"):
            extra_kwargs['enable_thinking'] = enable_thinking
        translation_results, tokens = translate_batch(processed_texts, source_lang, target_lang, engine=engine, **extra_kwargs)

        # 术语后处理
        if options.get("terminology_enabled", True):
            translation_results = postprocess_texts(translation_results, mappings)
        
        # 提取翻译结果
        if translation_results and len(translation_results) > 0:
            translation = translation_results[0][0] if isinstance(translation_results[0], list) else translation_results[0]
        else:
            translation = text  # 如果翻译失败，使用原文
        
        elapsed_time = time.time() - start_time
        logger.info(f"Translation completed in {elapsed_time:.2f}s, tokens: {tokens}, engine: {engine}")
        
        # Save to history with user ID
        history_entry = schemas.TextTranslationCreate(
            source_text=text,
            translated_text=translation,
            source_lang=source_lang,
            target_lang=target_lang,
            engine=engine
        )
        text_translation = crud.create_text_translation(db=db, translation=history_entry, user_id=current_user.id)
        try:
            # 保存元数据（tokens、字符数、字节数、耗时、engine_params）
            char_count = len(text)
            byte_count = len(text.encode('utf-8'))
            engine_params = {
                "engine": engine,
                "model": None,
                "max_workers": None,
                "batch_size": None,
                "retry_max": None,
                "sleep_between_requests": None,
                "timeout": None,
            }
            try:
                from .services.engine_config import EngineConfig
                if engine in ("qwen_plus","qwen-plus"):
                    cfg = EngineConfig.get_qwen_plus_config()
                elif engine == "qwen3":
                    cfg = EngineConfig.get_qwen3_config()
                elif engine == "deepseek":
                    cfg = EngineConfig.get_deepseek_config()
                elif engine == "kimi":
                    cfg = EngineConfig.get_kimi_config()
                elif engine == "tencent":
                    cfg = EngineConfig.get_tencent_config()
                elif engine == "youdao":
                    cfg = EngineConfig.get_youdao_config()
                else:
                    cfg = {}
                engine_params.update({
                    "model": cfg.get('model'),
                    "max_workers": cfg.get('max_workers'),
                    "batch_size": cfg.get('batch_size'),
                    "retry_max": cfg.get('retry_max'),
                    "sleep_between_requests": cfg.get('sleep_between_requests'),
                    "timeout": cfg.get('timeout'),
                })
                # 文本翻译：记录风格/启发式
                if style_preset:
                    engine_params["style_preset"] = style_preset
                if style_instruction:
                    engine_params["style_instruction"] = style_instruction[:300]
                if engine in ("qwen_plus","qwen-plus","deepseek"):
                    engine_params["enable_thinking"] = enable_thinking
            except Exception:
                pass
            
            # 使用返回的文本翻译ID直接插入元数据
            if text_translation and hasattr(text_translation, 'id'):
                logger.info(f"Saving text translation meta for text_id: {text_translation.id}")
                try:
                    from sqlalchemy import text
                    db.execute(text("""
                        INSERT INTO text_translation_meta (text_id, token_count, character_count, byte_count, duration, engine_params)
                        VALUES (:text_id, :tok, :ch, :bt, :dur, :ep)
                    """), {"text_id": text_translation.id, "tok": int(tokens or 0), "ch": char_count, "bt": byte_count, "dur": elapsed_time, "ep": json.dumps(engine_params, ensure_ascii=False)})
                    db.commit()
                    logger.info(f"Successfully saved text translation meta for text_id: {text_translation.id}")
                except Exception as e:
                    logger.error(f"Failed to execute meta insert: {e}")
                    db.rollback()
            else:
                logger.error(f"text_translation object is invalid: {text_translation}")
        except Exception as e:
            logger.error(f"Failed to save text translation meta: {e}")
            pass
        logger.info("Translation history saved to database")

        return JSONResponse(content={"translated_text": translation, "tokens": tokens, "engine": engine, "duration": round(elapsed_time, 2)})
    except Exception as e:
        logger.error(f"Translation failed: {str(e)}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")


@api_router.get("/history", response_model=List[schemas.HistoryItem])
async def get_history_list(skip: int = 0, limit: int = 20, db: Session = Depends(get_db)):
    """获取所有历史记录（文本+文档）"""
    # 直接分别查询，避免额外依赖
    text_records = db.query(models.TextTranslation).order_by(
        models.TextTranslation.create_time.desc()
    ).offset(skip).limit(limit).all()
    doc_records = db.query(models.TranslationTask).order_by(
        models.TranslationTask.create_time.desc()
    ).offset(skip).limit(limit).all()
    # 查询文本元数据（tokens/字符/字节/engine_params）
    try:
        text_ids = [t.id for t in text_records]
        meta_rows = {}
        if text_ids:
            metas = (
                db.query(models.TextTranslationMeta)
                .filter(models.TextTranslationMeta.text_id.in_(text_ids))
                .all()
            )
            for m in metas:
                meta_rows[int(m.text_id)] = {
                    "token_count": m.token_count,
                    "character_count": m.character_count,
                    "byte_count": m.byte_count,
                    "engine_params": m.engine_params,
                }
    except Exception:
        meta_rows = {}
    response_items = []
    # 文本
    for record in text_records:
        meta = meta_rows.get(record.id, {})
        response_items.append(schemas.HistoryItem(
            id=str(record.id),
            type="text",
            user_id=record.user_id,
            source_content=record.source_text,
            target_content=record.translated_text,
            source_lang=record.source_lang,
            target_lang=record.target_lang,
            create_time=record.create_time,
            engine=record.engine,
            character_count=meta.get("character_count"),
            token_count=meta.get("token_count"),
            engine_params=meta.get("engine_params")
        ))
    # 文档
    for record in doc_records:
        source_url = f"/uploads/{quote(record.file_name)}" if record.file_name else None
        target_url = f"/downloads/{quote(os.path.basename(record.result_path))}" if record.result_path else None
        # 解析文档的 error_message JSON 中的 engine_params（若存在）
        try:
            import json as _json
            doc_engine_params = None
            if record.error_message and str(record.error_message).strip().startswith('{'):
                em = _json.loads(record.error_message)
                doc_engine_params = em.get('engine_params')
        except Exception:
            doc_engine_params = None

        response_items.append(schemas.HistoryItem(
            id=record.task_id,
            type="document",
            user_id=record.user_id,
            status=record.status,
            source_content=record.file_name,
            source_url=source_url,
            target_content=os.path.basename(record.result_path) if record.result_path else None,
            target_url=target_url,
            source_lang=record.source_lang,
            target_lang=record.target_lang,
            create_time=record.create_time,
            error_message=record.error_message,
            source_file_size=record.source_file_size,
            target_file_size=record.target_file_size,
            character_count=record.character_count,
            token_count=record.token_count,
            duration=record.duration,
            engine=record.engine,
            strategy=record.strategy,
            engine_params=doc_engine_params
        ))
    
    return response_items

@api_router.get("/history/text", response_model=List[schemas.TextTranslation])
async def get_text_history(
    skip: int = 0,
    limit: int = 50,
    include_all: bool = False,
    mine_only: bool = Query(False, description="当为 true 时，即使是管理员也只返回自己的记录"),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """获取文本翻译历史记录"""
    if current_user.role == "admin" and not mine_only:
        # 管理员查看全量
        base_q = db.query(models.TextTranslation)
        if not include_all:
            base_q = base_q.filter(or_(models.TextTranslation.source_text != "", models.TextTranslation.translated_text != ""))
        text_history = base_q.order_by(models.TextTranslation.create_time.desc()).offset(skip).limit(limit).all()
        # 附加用户名
        for record in text_history:
            if record.user_id:
                user = db.query(models.User).filter(models.User.id == record.user_id).first()
                record.username = user.username if user else "未知用户"
    else:
        # 普通用户或管理员指定 mine_only=True 时，只看自己的
        base_q = db.query(models.TextTranslation).filter(models.TextTranslation.user_id == current_user.id)
        if not include_all:
            base_q = base_q.filter(or_(models.TextTranslation.source_text != "", models.TextTranslation.translated_text != ""))
        text_history = base_q.order_by(models.TextTranslation.create_time.desc()).offset(skip).limit(limit).all()
        # 设置当前用户名
        for record in text_history:
            record.username = current_user.username
    
    # 附加术语分类使用信息（如有）
    try:
        for rec in text_history:
            ts = crud.get_translation_term_set(db, translation_id=str(rec.id), translation_type="text")
            if ts:
                setattr(rec, 'term_category_ids', ts.category_ids)
    except Exception:
        pass
    return text_history

@api_router.get("/history/document", response_model=schemas.TranslationTaskPage)
async def get_document_history(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    include_all: bool = False,
    batch_only: bool = False,
    normal_only: bool = False,
    # 新增筛选与排序
    status: Optional[str] = Query(None, description="Filter by status: pending/processing/completed/failed"),
    engine: Optional[str] = Query(None, description="Filter by engine"),
    username: Optional[str] = Query(None, description="Admin only: fuzzy search by username"),
    sortBy: Optional[str] = Query(None, description="Sort by field: create_time/token_count/duration/source_file_size/target_file_size"),
    sortOrder: Optional[str] = Query(None, description="asc or desc"),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """获取文档翻译历史记录（分页）"""
    skip = (page - 1) * limit
    
    doc_history, total_count = crud.get_document_history_paginated(
        db, 
        user_id=current_user.id if current_user.role != "admin" else None,
        skip=skip, 
        limit=limit, 
        include_all=include_all,
        batch_only=batch_only,
        normal_only=normal_only,
        status=status,
        engine=engine,
        username=username if current_user.role == "admin" else None,
        sort_by=sortBy,
        sort_order=sortOrder,
    )
    
    # 为每条记录添加用户名信息
    for record in doc_history:
        if record.user_id:
            if current_user.role == "admin":
                user = db.query(models.User).filter(models.User.id == record.user_id).first()
                record.username = user.username if user else "未知用户"
            else:
                record.username = current_user.username

    # 附加术语分类使用信息
    try:
        for rec in doc_history:
            ts = crud.get_translation_term_set(db, translation_id=rec.task_id, translation_type="document")
            if ts:
                setattr(rec, 'term_category_ids', ts.category_ids)
    except Exception:
        pass

    # 展开 error_message 中的 JSON 统计
    try:
        import json as _json
        for rec in doc_history:
            try:
                if rec.error_message and str(rec.error_message).strip().startswith('{'):
                    extra = _json.loads(rec.error_message)
                    for k in ("total_texts", "translated_texts", "qwen3_total", "qwen3_success", "qwen3_429"):
                        if k in extra:
                            setattr(rec, k, extra[k])
            except Exception:
                continue
    except Exception:
        pass
        
    return {"items": doc_history, "total": total_count}

@api_router.get("/history/batch", response_model=schemas.TranslationTaskPage)
async def get_batch_history(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    include_all: bool = False,
    status: Optional[str] = Query(None),
    engine: Optional[str] = Query(None),
    username: Optional[str] = Query(None),
    sortBy: Optional[str] = Query(None),
    sortOrder: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """获取批量翻译历史记录（仅 batch_api），分页返回 {items,total} 与 /history/document 对齐"""
    skip = (page - 1) * limit
    items, total = crud.get_document_history_paginated(
        db,
        user_id=current_user.id if current_user.role != "admin" else None,
        skip=skip,
        limit=limit,
        include_all=include_all,
        batch_only=True,
        normal_only=False,
        status=status,
        engine=engine,
        username=username if current_user.role == "admin" else None,
        sort_by=sortBy,
        sort_order=sortOrder,
    )
    # 附加术语分类使用信息（保持与 /history/document 一致）
    try:
        for rec in items:
            ts = crud.get_translation_term_set(db, translation_id=rec.task_id, translation_type="document")
            if ts:
                setattr(rec, 'term_category_ids', ts.category_ids)
    except Exception:
        pass
    return {"items": items, "total": total}

@api_router.delete("/history/{item_id}")
async def delete_history(item_id: str, type: str, db: Session = Depends(get_db)):
    # 删除策略：
    # - 文本：彻底删除记录及其元数据
    # - 文档：仅删除文件，保留数据库记录与统计信息（将 result_path 置空）
    try:
        if type == 'text':
            rec = db.query(models.TextTranslation).filter(models.TextTranslation.id == int(item_id)).first()
            if not rec:
                raise HTTPException(status_code=404, detail="History item not found")
            # 清空内容，保留语言、引擎、时间与统计元数据
            rec.source_text = ""
            rec.translated_text = ""
            db.commit()
            return {"message": "Text content cleared, record retained"}
        elif type == 'document':
            rec = db.query(models.TranslationTask).filter(models.TranslationTask.task_id == item_id).first()
            if not rec:
                raise HTTPException(status_code=404, detail="History item not found")
            # 删除生成文件与源文件（如存在），保留统计记录
            try:
                if rec.result_path and os.path.exists(rec.result_path):
                    os.remove(rec.result_path)
                if rec.file_name:
                    src_path = os.path.join(UPLOAD_DIR, rec.file_name)
                    if os.path.exists(src_path):
                        os.remove(src_path)
            except Exception:
                pass
            rec.result_path = None
            rec.file_name = None
            db.commit()
            return {"message": "Document files deleted, record retained"}
        else:
            raise HTTPException(status_code=400, detail="Invalid type")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@api_router.get("/translate/result/{task_id}")
async def get_translation_result(task_id: str):
    # 以数据库状态为准，兼容 Celery 状态
    try:
        from .database import SessionLocal
        db = SessionLocal()
        record = db.query(models.TranslationTask).filter(models.TranslationTask.task_id == task_id).first()
        if record:
            resp = {
                "status": str(record.status).split('.')[-1] if record.status else "pending",
                "result": {"translated_file_path": f"/{record.result_path}"} if record.result_path else None,
                "error": record.error_message,
            }
            return JSONResponse(content=resp)
    except Exception as e:
        logger.error(f"Result lookup failed: {e}")
    finally:
        try:
            db.close()
        except Exception:
            pass

    # 回退到 Celery 状态
    task_result = AsyncResult(task_id, app=celery_app)
    response = {"status": task_result.status.lower()}
    if task_result.ready():
        if task_result.successful():
            response["result"] = task_result.get()
        else:
            response["error"] = str(task_result.info)
    return JSONResponse(content=response)

@api_router.get("/health/deepseek")
async def check_deepseek_health():
    logger.info("DeepSeek health check requested")
    
    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key or api_key == "YOUR_DEEPSEEK_API_KEY":
        logger.error("DEEPSEEK_API_KEY not configured")
        raise HTTPException(status_code=401, detail="DEEPSEEK_API_KEY not configured.")
    
    try:
        # 测试DeepSeek API连接，但不保存历史记录
        from .services.utils_translator import DeepSeekTranslator
        logger.info("Testing DeepSeek API connection...")
        
        # 创建临时翻译器实例，不保存历史
        translator = DeepSeekTranslator()
        
        start_time = time.time()
        # 直接调用API，不通过simple_translate（避免保存历史）
        result = await translator._test_connection()
        elapsed_time = time.time() - start_time
        
        if result and result.get('success'):
            logger.info(f"DeepSeek API test successful in {elapsed_time:.2f}s")
            return {
                "status": "healthy", 
                "message": "DeepSeek API is working properly",
                "response_time": round(elapsed_time, 2)
            }
        else:
            logger.warning("DeepSeek API test failed")
            return {
                "status": "warning",
                "message": "DeepSeek API test failed",
                "response_time": round(elapsed_time, 2)
            }
            
    except Exception as e:
        logger.error(f"DeepSeek API health check failed: {str(e)}")
        return {
            "status": "unhealthy",
            "message": f"DeepSeek API connection failed: {str(e)}"
        }

@api_router.get("/engines/status")
async def get_engines_status():
    """获取所有AI引擎的状态"""
    from .services.engine_config import EngineConfig
    
    engines = ['deepseek', 'tencent', 'kimi', 'youdao', 'qwen3']
    status = {}
    
    for engine in engines:
        try:
            status[engine] = EngineConfig.is_engine_available(engine)
        except Exception as e:
            logger.error(f"Error checking {engine} engine status: {e}")
            status[engine] = False
    
    return {
        "engines": status,
        "default_engine": EngineConfig.get_default_engine(),
        "available_engines": EngineConfig.get_available_engines()
    }

@api_router.get("/engines/available")
async def get_available_engines(db: Session = Depends(get_db)):
    """公开接口：返回数据库中处于 active 状态的引擎，用于前端下拉联动"""
    engines = db.query(models.TranslationEngine).filter(
        models.TranslationEngine.status == models.EngineStatus.active
    ).order_by(models.TranslationEngine.priority.asc()).all()
    return [
        {
            "engine_name": e.engine_name,
            "display_name": e.display_name,
            "is_default": e.is_default
        }
        for e in engines
    ]

@api_router.get("/strategies/available")
async def get_available_strategies(db: Session = Depends(get_db)):
    """公开接口：返回数据库中启用的策略；如无数据，返回内置默认策略"""
    strategies = db.query(models.TranslationStrategy).filter(
        models.TranslationStrategy.status == True
    ).order_by(models.TranslationStrategy.priority.asc()).all()
    if strategies:
        return [
            {
                "strategy_name": s.strategy_name,
                "display_name": s.display_name,
            }
            for s in strategies
        ]
    # 无配置时提供默认策略
    return [
        {"strategy_name": "ooxml_direct", "display_name": "OOXML直接处理"},
        {"strategy_name": "text_direct", "display_name": "文本直接处理"},
    ]

@api_router.post("/batch/start")
async def batch_start(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_active_user)):
    """创建批量任务批次，返回 batch_id"""
    batch_id = str(uuid.uuid4())
    try:
        job = models.BatchJob(batch_id=batch_id, user_id=current_user.id)
        db.add(job)
        db.commit()
        return {"batch_id": batch_id}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/batch/submit")
async def batch_submit(
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(...),
    source_lang: str = Form(...),
    target_lang: str = Form(...),
    engine: str = Form("qwen_plus"),  # 批量翻译默认使用 qwen-plus
    batch_id: Optional[str] = Form(None),
    category_ids: Optional[str] = Form(None),
    style_instruction: Optional[str] = Form(None),
    style_preset: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """提交多个文件使用 qwen-plus Batch API 进行批量翻译"""
    if not files:
        raise HTTPException(status_code=400, detail="No files provided")
    
    # 批量翻译强制使用 qwen-plus
    if engine not in ["qwen_plus", "qwen-plus"]:
        engine = "qwen_plus"
    logger.info(f"[batch_submit] engine={engine}, src={source_lang}, tgt={target_lang}, files={len(files)}")
    
    if not batch_id:
        batch_id = str(uuid.uuid4())
        db.add(models.BatchJob(batch_id=batch_id, user_id=current_user.id))
        db.commit()

    created: List[Dict[str, str]] = []
    
    # 解析术语分类
    parsed_category_ids: Optional[List[int]] = None
    try:
        if category_ids:
            import json as _json
            val = _json.loads(category_ids)
            if isinstance(val, list):
                parsed_category_ids = [int(x) for x in val if str(x).isdigit()]
    except Exception:
        parsed_category_ids = None

    for f in files:
        try:
            filename = os.path.basename(f.filename)
            file_path = os.path.join(UPLOAD_DIR, filename)
            with open(file_path, "wb") as buffer:
                buffer.write(await f.read())
            
            file_name_without_ext, file_ext = os.path.splitext(filename)
            sanitized_base_name = sanitize_filename(file_name_without_ext)
            output_filename = f"{sanitized_base_name}_translated{file_ext}"
            output_path = os.path.join(DOWNLOAD_DIR, output_filename)
            
            source_file_size = os.path.exists(file_path) and os.path.getsize(file_path) or None
            task_id_str = str(uuid.uuid4())
            
            # 创建任务记录
            task_data = schemas.TranslationTaskCreate(
                task_id=task_id_str,
                user_id=current_user.id,
                file_name=filename,
                file_type=file_ext,
                source_lang=source_lang,
                target_lang=target_lang,
                status='pending',
                result_path=output_path,
                source_file_size=source_file_size,
                engine=engine,
                strategy='batch_api'  # 标记为 Batch API 模式
            )
            crud.create_or_update_translation_task(db=db, task=task_data)
            logger.info(f"[batch_submit] created task: file={filename}, task_id={task_id_str}, src={source_lang}, tgt={target_lang}")
            
            # 记录 engine_params
            try:
                from .services.engine_config import EngineConfig as _EC
                base_cfg = _EC.get_qwen_plus_config()
                ep = {
                    "engine": engine,
                    "model": base_cfg.get('model'),
                    "max_workers": base_cfg.get('max_workers'),
                    "batch_size": base_cfg.get('batch_size'),
                    "retry_max": base_cfg.get('retry_max'),
                    "sleep_between_requests": base_cfg.get('sleep_between_requests'),
                    "timeout": base_cfg.get('timeout'),
                    "mode": "batch_api",  # 标记为 Batch API 模式
                }
                if style_preset: 
                    ep["style_preset"] = style_preset
                if style_instruction: 
                    ep["style_instruction"] = style_instruction[:300]
                crud.update_translation_task(db, task_id_str, {"engine_params": ep})
            except Exception:
                pass

            # 关联到批次
            db.add(models.BatchItem(batch_id=batch_id, task_id=task_id_str))
            db.commit()

            # 启动后台处理：改为通过 Celery 队列执行，确保由 worker 处理并正确落盘
            # 通过 Celery 派发，同时也在本进程后台线程执行一次作为兜底，确保文件一定生成
            try:
                process_batch_translation_task.delay(
                    task_id=task_id_str,
                    file_path=file_path,
                    output_path=output_path,
                    source_lang=source_lang,
                    target_lang=target_lang,
                    category_ids=parsed_category_ids,
                    style_instruction=style_instruction,
                    style_preset=style_preset,
                )
            except Exception:
                pass
            background_tasks.add_task(
                process_batch_translation_task,
                task_id=task_id_str,
                file_path=file_path,
                output_path=output_path,
                source_lang=source_lang,
                target_lang=target_lang,
                category_ids=parsed_category_ids,
                style_instruction=style_instruction,
                style_preset=style_preset,
            )
            created.append({"file": filename, "task_id": task_id_str})
        except Exception as e:
            logger.error(f"Batch submit failed for {f.filename}: {e}")
            continue

    return {"batch_id": batch_id, "items": created}

@api_router.get("/batch/{batch_id}")
async def batch_status(batch_id: str, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_active_user)):
    """查看批次内任务状态与汇总"""
    job = db.query(models.BatchJob).filter(models.BatchJob.batch_id == batch_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Batch not found")
    
    items = db.query(models.BatchItem).filter(models.BatchItem.batch_id == batch_id).all()
    results = []
    total = len(items)
    completed = 0
    failed = 0
    tokens_sum = 0
    
    for it in items:
        t = crud.get_translation_task(db, it.task_id)
        if not t:
            continue
        status = str(t.status).split('.')[-1] if t.status else "pending"
        if status == 'completed':
            completed += 1
        if status == 'failed':
            failed += 1
        try:
            tokens_sum += int(t.token_count or 0)
        except Exception:
            pass
        results.append({
            "task_id": t.task_id,
            "file_name": t.file_name,
            "status": status,
            "engine": t.engine,
            "strategy": t.strategy,
            "token_count": t.token_count,
            "result_path": t.result_path,
        })
    
    summary = {
        "batch_id": batch_id,
        "total": total,
        "completed": completed,
        "failed": failed,
        "tokens": tokens_sum,
        "items": results,
    }
    # 若全部完成或失败（无待处理），回填汇总到 batch_metrics
    if total > 0 and (completed + failed == total):
        try:
            crud.upsert_batch_metrics(db, batch_id, total, completed, failed, int(tokens_sum or 0))
        except Exception as _e:
            logger.warning(f"upsert_batch_metrics failed: {_e}")
    return summary

@api_router.get("/batch/metrics/{batch_id}")
async def batch_metrics(batch_id: str, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_active_user)):
    m = crud.get_batch_metrics(db, batch_id)
    if not m:
        raise HTTPException(status_code=404, detail="Metrics not found")
    return {"batch_id": m.batch_id, "total": m.total, "completed": m.completed, "failed": m.failed, "tokens": m.tokens, "update_time": m.update_time}

@api_router.post("/batch/metrics/prune")
async def batch_metrics_prune(days: int = 30, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_active_user)):
    removed = crud.prune_old_batch_metrics(db, days=days)
    return {"removed": removed}

@api_router.get("/batch/of_task/{task_id}")
async def batch_of_task(task_id: str, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_active_user)):
    """查询某个 task_id 所属的 batch_id，并返回已持久化的汇总（如有）。"""
    it = db.query(models.BatchItem).filter(models.BatchItem.task_id == task_id).first()
    if not it:
        raise HTTPException(status_code=404, detail="Batch item not found")
    m = crud.get_batch_metrics(db, it.batch_id)
    resp = {"batch_id": it.batch_id}
    if m:
        resp["metrics"] = {"total": m.total, "completed": m.completed, "failed": m.failed, "tokens": m.tokens, "update_time": m.update_time}
    return resp

# --- Admin utilities ---
@api_router.post("/admin/history/cleanup/pending-batch")
async def admin_cleanup_pending_batch(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """清理批量翻译历史中 status=pending 的任务，连同批次关联。
    仅管理员可用：彻底删除 translation_tasks 记录与 batch_items 关联；
    若某个 batch_job 已无关联项，则一并删除该 batch_job。
    """
    role_val = getattr(current_user, 'role', None)
    role_str = None
    try:
        role_str = role_val.value if hasattr(role_val, 'value') else str(role_val)
    except Exception:
        role_str = str(role_val)
    if role_str != 'admin':
        raise HTTPException(status_code=403, detail="Admin only")

    deleted_tasks = 0
    deleted_items = 0
    deleted_batches = 0

    # 找出待删除任务
    tasks = (
        db.query(models.TranslationTask)
        .filter(models.TranslationTask.strategy == 'batch_api')
        .filter(models.TranslationTask.status == models.TaskStatus.pending)
        .all()
    )
    task_ids = [t.task_id for t in tasks]
    if task_ids:
        # 删除 batch_items 关联
        items = db.query(models.BatchItem).filter(models.BatchItem.task_id.in_(task_ids)).all()
        for it in items:
            db.delete(it)
        deleted_items = len(items)

        # 删除任务记录
        for t in tasks:
            db.delete(t)
        deleted_tasks = len(tasks)
        db.commit()

    # 清理空的 batch_job（没有任何 batch_item 的）
    jobs = db.query(models.BatchJob).all()
    for job in jobs:
        has_items = db.query(models.BatchItem).filter(models.BatchItem.batch_id == job.batch_id).first()
        if not has_items:
            db.delete(job)
            deleted_batches += 1
    if deleted_batches:
        db.commit()

    return {"deleted_tasks": deleted_tasks, "deleted_batch_items": deleted_items, "deleted_empty_batches": deleted_batches}

@api_router.post("/batch/cancel/{batch_id}")
async def batch_cancel(batch_id: str, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_active_user)):
    """前端强制清理时，可调用此接口清空该批次项（不删除历史记录）。"""
    job = db.query(models.BatchJob).filter(models.BatchJob.batch_id == batch_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Batch not found")
    db.query(models.BatchItem).filter(models.BatchItem.batch_id == batch_id).delete()
    db.commit()
    return {"ok": True}

@api_router.post("/batch/prune/{batch_id}")
async def batch_prune(batch_id: str, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_active_user)):
    """清理批次中已完成/失败或无效（无文件名）的项，避免前端残留。"""
    # 找到该批次的所有项，联表查询任务状态
    items = db.query(models.BatchItem).filter(models.BatchItem.batch_id == batch_id).all()
    removed = 0
    for it in items:
        t = crud.get_translation_task(db, it.task_id)
        status = str(getattr(t, 'status', '')).split('.')[-1] if t and t.status else 'pending'
        file_name = getattr(t, 'file_name', '') if t else ''
        if not t or not file_name or status in ("completed", "failed"):
            db.delete(it)
            removed += 1
    db.commit()
    return {"ok": True, "removed": removed}


# Include routers
app.include_router(api_router)
app.include_router(terminology.router, prefix="/api/terminology", tags=["terminology"])
app.include_router(users.router, prefix="/api/users", tags=["users"])
app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(admin.router, prefix="/api/admin", tags=["admin"])
async def get_deepseek_settings():
    """获取DeepSeek设置"""
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
        logger.error(f"Failed to get DeepSeek settings: {e}")
        raise HTTPException(status_code=500, detail="Failed to get DeepSeek settings")

@app.post("/api/admin/settings/deepseek")
async def update_deepseek_settings_legacy(settings: dict):
    """更新DeepSeek设置"""
    try:
        # 验证设置参数
        use_json_format = settings.get('use_json_format')
        json_batch_size = settings.get('json_batch_size')
        
        if use_json_format is not None:
            if not isinstance(use_json_format, bool):
                raise HTTPException(status_code=400, detail="use_json_format must be boolean")
        
        if json_batch_size is not None:
            if not isinstance(json_batch_size, int) or json_batch_size <= 0:
                raise HTTPException(status_code=400, detail="json_batch_size must be positive integer")
            if json_batch_size > 100:
                raise HTTPException(status_code=400, detail="json_batch_size cannot exceed 100")
        
        # 更新环境变量（这里只是临时更新，重启后会恢复）
        # 在生产环境中，你可能需要持久化这些设置到数据库或配置文件
        if use_json_format is not None:
            os.environ['DEEPSEEK_USE_JSON_FORMAT'] = str(use_json_format).lower()
        
        if json_batch_size is not None:
            os.environ['DEEPSEEK_JSON_BATCH_SIZE'] = str(json_batch_size)
        
        logger.info(f"DeepSeek settings updated: use_json_format={use_json_format}, json_batch_size={json_batch_size}")
        
        return {"message": "DeepSeek settings updated successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update DeepSeek settings: {e}")
        raise HTTPException(status_code=500, detail="Failed to update DeepSeek settings")

@app.get("/api/admin/settings/engines")
async def get_all_engine_settings_legacy():
    """获取所有AI引擎设置"""
    try:
        from app.services.engine_config import EngineConfig
        
        settings = {}
        
        # DeepSeek设置
        try:
            deepseek_config = EngineConfig.get_deepseek_config()
            settings['deepseek'] = {
                "use_json_format": deepseek_config.get('use_json_format', True),
                "json_batch_size": deepseek_config.get('json_batch_size', 50),
                "batch_size": deepseek_config.get('batch_size', 20),
                "max_workers": deepseek_config.get('max_workers', 10),
                "timeout": deepseek_config.get('timeout', 60)
            }
        except Exception as e:
            logger.warning(f"Failed to get DeepSeek config: {e}")
            settings['deepseek'] = {"error": "Configuration unavailable"}
        
        # Kimi设置
        try:
            kimi_config = EngineConfig.get_kimi_config()
            settings['kimi'] = {
                "batch_size": kimi_config.get('batch_size', 8),
                "max_workers": kimi_config.get('max_workers', 2),
                "timeout": kimi_config.get('timeout', 60)
            }
        except Exception as e:
            logger.warning(f"Failed to get Kimi config: {e}")
            settings['kimi'] = {"error": "Configuration unavailable"}
        
        # Youdao设置
        try:
            youdao_config = EngineConfig.get_youdao_config()
            settings['youdao'] = {
                "batch_size": youdao_config.get('batch_size', 10),
                "max_workers": youdao_config.get('max_workers', 3),
                "timeout": youdao_config.get('timeout', 60),
                "max_batch_size": youdao_config.get('max_batch_size', 5),
                "max_chars_per_batch": youdao_config.get('max_chars_per_batch', 1000)
            }
        except Exception as e:
            logger.warning(f"Failed to get Youdao config: {e}")
            settings['youdao'] = {"error": "Configuration unavailable"}
        
        # Tencent设置
        try:
            tencent_config = EngineConfig.get_tencent_config()
            settings['tencent'] = {
                "batch_size": tencent_config.get('batch_size', 15),
                "max_workers": tencent_config.get('max_workers', 5),
                "timeout": tencent_config.get('timeout', 60)
            }
        except Exception as e:
            logger.warning(f"Failed to get Tencent config: {e}")
            settings['tencent'] = {"error": "Configuration unavailable"}
        # Qwen3 设置
        try:
            qwen_config = EngineConfig.get_qwen3_config()
            settings['qwen3'] = {
                "model": qwen_config.get('model', 'qwen-mt-turbo'),
                "batch_size": qwen_config.get('batch_size', 50),
                "max_workers": qwen_config.get('max_workers', 12),
                "timeout": qwen_config.get('timeout', 60)
            }
        except Exception as e:
            logger.warning(f"Failed to get Qwen3 config: {e}")
            settings['qwen3'] = {"error": "Configuration unavailable"}
        # Qwen Plus 设置
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
        except Exception as e:
            logger.warning(f"Failed to get Qwen Plus config: {e}")
            settings['qwen_plus'] = {"error": "Configuration unavailable"}
        
        return settings
        
    except Exception as e:
        logger.error(f"Failed to get engine settings: {e}")
        raise HTTPException(status_code=500, detail="Failed to get engine settings")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)