import os
import time
from typing import Optional, List, Dict, Any
from .services.utils_translator import translate_batch
from .services.translator_text import translate_text_direct
from .services.translator_ooxml_direct import translate_docx_inplace
from .services.translator_xlsx_direct import translate_xlsx_direct
from .services.translator_pptx_direct import translate_pptx_direct
from .database import get_db
from . import crud, models

def process_translation_task(
    task_id: str,
    file_path: str,
    output_path: str,
    source_lang: str,
    target_lang: str,
    engine: str = "deepseek",
    strategy: str = "ooxml_direct",
    category_ids=None,
    style_instruction: str | None = None,
    style_preset: str | None = None,
):
    """处理翻译任务的后台函数"""
    db = next(get_db())
    
    try:
        # 读取任务以获取 user_id
        task = crud.get_translation_task(db, task_id)
        task_user_id = task.user_id if task else None
        # 更新任务状态为处理中
        crud.update_translation_task(db, task_id, {"status": "processing", "progress": 10})
        
        # 根据策略与扩展名执行实际翻译
        os.makedirs("downloads", exist_ok=True)

        ext = os.path.splitext(file_path)[1].lower()

        # 进度推进
        for progress in [20, 40]:
            time.sleep(0.5)
            crud.update_translation_task(db, task_id, {"progress": progress})

        start_ts = time.time()
        meta = {}
        if strategy == "text_direct" or ext in [".txt", ".md"]:
            meta = translate_text_direct(file_path, output_path, source_lang, target_lang, engine=engine, user_id=task_user_id, category_ids=category_ids) or {}
        elif strategy == "ooxml_direct" and ext == ".docx":
            # 读取并发设置
            db_settings = { s.key: s for s in db.query(models.SystemSetting).filter(models.SystemSetting.category=="ooxml").all() }
            workers = 5
            try:
                if db_settings.get("docx_parallel_workers") and str(db_settings["docx_parallel_workers"].value).isdigit():
                    workers = int(db_settings["docx_parallel_workers"].value)
            except Exception:
                pass
            meta = translate_docx_inplace(
                file_path, output_path, source_lang, target_lang,
                engine=engine, workers=workers, debug=False,
                user_id=task_user_id, category_ids=category_ids,
                style_instruction=style_instruction, style_preset=style_preset
            ) or {}
        elif strategy == "ooxml_direct" and ext == ".xlsx":
            # 允许通过设置控制是否启用 OOXML 模式（当前实现默认走 OOXML，回退 openpyxl）
            meta = translate_xlsx_direct(
                file_path, output_path, source_lang, target_lang,
                engine=engine, user_id=task_user_id, category_ids=category_ids,
                style_instruction=style_instruction, style_preset=style_preset
            ) or {}
        elif strategy == "ooxml_direct" and ext == ".pptx":
            meta = translate_pptx_direct(
                file_path, output_path, source_lang, target_lang,
                engine=engine, user_id=task_user_id, category_ids=category_ids,
                style_instruction=style_instruction, style_preset=style_preset
            ) or {}
        else:
            # 未实现的类型，先直接复制
            import shutil
            shutil.copy2(file_path, output_path)
        # 计算耗时
        duration = max(0.0, time.time() - start_ts)
        # 目标文件大小
        target_size = None
        try:
            if os.path.exists(output_path):
                target_size = os.path.getsize(output_path)
        except Exception:
            pass

        # 完成
        crud.update_translation_task(db, task_id, {
            "status": "completed",
            "progress": 100,
            "result_path": output_path,
            "target_file_size": target_size,
            "character_count": meta.get("character_count"),
            "token_count": meta.get("token_count"),
            "duration": duration,
        })
        # 记录通用统计：写入 error_message(JSON)
        try:
            extra_common = {}
            if isinstance(meta, dict):
                if meta.get("total_texts") is not None:
                    extra_common["total_texts"] = int(meta.get("total_texts"))
                if meta.get("translated_texts") is not None:
                    extra_common["translated_texts"] = int(meta.get("translated_texts"))
            if extra_common:
                import json as _json
                task = crud.get_translation_task(db, task_id)
                prev = {}
                try:
                    if task and task.error_message and task.error_message.strip().startswith('{'):
                        prev = _json.loads(task.error_message)
                except Exception:
                    prev = {}
                prev.update(extra_common)
                crud.update_translation_task(db, task_id, {"error_message": _json.dumps(prev, ensure_ascii=False)})
                # 控制台输出
                print(f"[Engine:{engine}] 文档文本统计: total_texts={extra_common.get('total_texts')} translated_texts={extra_common.get('translated_texts')} chars={meta.get('character_count')}")
        except Exception:
            pass

        # 附加：汇总统计/风格参数并附加到任务记录的 error_message(JSON)
        try:
            import json as _json
            task = crud.get_translation_task(db, task_id)
            prev = {}
            try:
                if task and task.error_message and task.error_message.strip().startswith('{'):
                    prev = _json.loads(task.error_message)
            except Exception:
                prev = {}
            # qwen3 统计
            if str(engine).lower() == 'qwen3':
                from .services.multi_engine_translator import qwen3_get_metrics
                m = qwen3_get_metrics()
                stats = {"qwen3_total": m.get('total'), "qwen3_success": m.get('success'), "qwen3_429": m.get('429')}
                if isinstance(meta, dict):
                    if meta.get("total_texts") is not None:
                        stats["total_texts"] = int(meta.get("total_texts"))
                    if meta.get("translated_texts") is not None:
                        stats["translated_texts"] = int(meta.get("translated_texts"))
                prev.update(stats)
                print(f"[Qwen3] 文档翻译统计: total={stats.get('qwen3_total')} success={stats.get('qwen3_success')} 429={stats.get('qwen3_429')} texts={stats.get('total_texts')} translated={stats.get('translated_texts')}")
            # 附加风格参数
            try:
                if style_preset or style_instruction:
                    ep = prev.get('engine_params', {})
                    if style_preset:
                        ep['style_preset'] = style_preset
                    if style_instruction:
                        ep['style_instruction'] = style_instruction[:300]
                    prev['engine_params'] = ep
            except Exception:
                pass
            crud.update_translation_task(db, task_id, {"error_message": _json.dumps(prev, ensure_ascii=False)})
        except Exception:
            pass
        
        print(f"翻译任务 {task_id} 完成")
        
    except Exception as e:
        # 更新任务状态为失败
        crud.update_translation_task(db, task_id, {
            "status": "failed",
            "error_message": str(e)
        })
        print(f"翻译任务 {task_id} 失败: {e}")
        
    finally:
        db.close()

# Celery配置（如果需要的话）
from celery import Celery
from datetime import datetime, timedelta
import os

# 从环境变量中获取Redis URL，并提供一个默认值
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

celery_app = Celery(
    "transai",
    broker=REDIS_URL,
    backend=REDIS_URL
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)

@celery_app.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):
    # 每天 03:00 运行清理任务
    sender.add_periodic_task(24*60*60, cleanup_old_histories.s(), name='daily_cleanup_histories')

@celery_app.task
def cleanup_old_histories():
    """按系统设置的保留天数清理过期文本/文档记录与生成文件。
    文本：直接删除记录与meta。
    文档：删除生成文件，并保留记录（仅置空 result_path）。
    """
    from .database import SessionLocal
    from . import models
    from . import crud

    db = SessionLocal()
    try:
        # 读取保留天数
        def _get_int(key: str, default: int) -> int:
            try:
                s = crud.get_system_setting_by_key(db, key)
                return int(s.value) if s and str(s.value).isdigit() else default
            except Exception:
                return default

        text_days = _get_int('text_retention_days', 30)
        doc_days = _get_int('doc_retention_days', 30)
        now = datetime.utcnow()
        text_cutoff = now - timedelta(days=text_days)
        doc_cutoff = now - timedelta(days=doc_days)

        # 清理文本内容（保留记录与meta）
        old_texts = db.query(models.TextTranslation).filter(models.TextTranslation.create_time < text_cutoff).all()
        text_ids = [t.id for t in old_texts]
        for t in old_texts:
            t.source_text = ""
            t.translated_text = ""
        db.commit()

        # 清理文档文件（生成文件与源文件），保留记录
        old_docs = db.query(models.TranslationTask).filter(models.TranslationTask.create_time < doc_cutoff).all()
        for task in old_docs:
            try:
                if task.result_path and os.path.exists(task.result_path):
                    os.remove(task.result_path)
                if task.file_name:
                    src_path = os.path.join('uploads', task.file_name)
                    if os.path.exists(src_path):
                        os.remove(src_path)
                task.result_path = None
                task.file_name = None
            except Exception:
                pass
        db.commit()
        return {
            'text_deleted': len(text_ids),
            'docs_files_cleared': len(old_docs)
        }
    except Exception as e:
        return {'error': str(e)}
    finally:
        db.close()

@celery_app.task
def translate_document_task(
    task_id: str,
    file_path: str,
    output_path: str,
    source_lang: str,
    target_lang: str,
    engine: str = "deepseek",
    strategy: str = "ooxml_direct",
    category_ids=None,
    style_instruction: str | None = None,
    style_preset: str | None = None,
):
    """Celery任务：翻译文档"""
    return process_translation_task(
        task_id=task_id,
        file_path=file_path,
        output_path=output_path,
        source_lang=source_lang,
        target_lang=target_lang,
        engine=engine,
        strategy=strategy,
        category_ids=category_ids,
        style_instruction=style_instruction,
        style_preset=style_preset,
    )

def run_batch_translation_task(
    task_id: str,
    file_path: str,
    output_path: str,
    source_lang: str,
    target_lang: str,
    category_ids: Optional[List[int]] = None,
    style_instruction: Optional[str] = None,
    style_preset: Optional[str] = None,
):
    """纯函数：执行批量翻译任务（供 Celery 与后台线程共用）。"""
    # 更新任务状态为处理中
    from .database import get_db
    from . import crud
    db = next(get_db())
    try:
        crud.update_translation_task(db, task_id, {"status": "processing"})

        file_ext = os.path.splitext(file_path)[1].lower()

        if file_ext == '.docx':
            result = translate_docx_batch_api(
                file_path, output_path, source_lang, target_lang,
                category_ids, style_instruction, style_preset
            )
        elif file_ext == '.pptx':
            result = translate_pptx_batch_api(
                file_path, output_path, source_lang, target_lang,
                category_ids, style_instruction, style_preset
            )
        elif file_ext == '.xlsx':
            result = translate_xlsx_batch_api(
                file_path, output_path, source_lang, target_lang,
                category_ids, style_instruction, style_preset
            )
        elif file_ext in ['.txt', '.md']:
            result = translate_text_batch_api(
                file_path, output_path, source_lang, target_lang,
                category_ids, style_instruction, style_preset
            )
        else:
            raise ValueError(f"Unsupported file type: {file_ext}")

        crud.update_translation_task(db, task_id, {
            "status": "completed",
            "token_count": result.get('token_count', 0),
            "character_count": result.get('character_count', 0),
            "target_file_size": os.path.getsize(output_path) if os.path.exists(output_path) else None,
            "duration": result.get('duration', 0)
        })
        try:
            # 记录语言到 error_message 便于追踪
            task = crud.get_translation_task(db, task_id)
            import json as _json
            info = {}
            try:
                if task and task.error_message and task.error_message.strip().startswith('{'):
                    info = _json.loads(task.error_message)
            except Exception:
                info = {}
            info.update({"src_lang": source_lang, "tgt_lang": target_lang})
            crud.update_translation_task(db, task_id, {"error_message": _json.dumps(info, ensure_ascii=False)})
        except Exception:
            pass
        print(f"Batch translation task {task_id} completed successfully")
    except Exception as e:
        print(f"Batch translation task {task_id} failed: {str(e)}")
        try:
            crud.update_translation_task(db, task_id, {
                "status": "failed",
                "error_message": str(e)
            })
        except Exception:
            pass
        raise
    finally:
        try:
            db.close()
        except Exception:
            pass


@celery_app.task
def process_batch_translation_task(
    task_id: str,
    file_path: str,
    output_path: str,
    source_lang: str,
    target_lang: str,
    category_ids: Optional[List[int]] = None,
    style_instruction: Optional[str] = None,
    style_preset: Optional[str] = None,
):
    return run_batch_translation_task(
        task_id=task_id,
        file_path=file_path,
        output_path=output_path,
        source_lang=source_lang,
        target_lang=target_lang,
        category_ids=category_ids,
        style_instruction=style_instruction,
        style_preset=style_preset,
    )

def translate_docx_batch_api(
    file_path: str,
    output_path: str,
    source_lang: str,
    target_lang: str,
    category_ids: Optional[List[int]] = None,
    style_instruction: Optional[str] = None,
    style_preset: Optional[str] = None,
) -> Dict[str, Any]:
    """使用 Batch API 翻译 DOCX 文件"""
    start_time = time.time()
    
    try:
        from .services.translator_ooxml_direct import translate_docx_inplace
        result = translate_docx_inplace(
            file_path, output_path, source_lang, target_lang,
            category_ids, style_instruction, style_preset,
            engine="qwen_plus", strategy="batch_api"
        )
        
        duration = time.time() - start_time
        result['duration'] = duration
        
        return result
    except Exception as e:
        print(f"DOCX batch translation failed: {e}")
        raise

def translate_pptx_batch_api(
    file_path: str,
    output_path: str,
    source_lang: str,
    target_lang: str,
    category_ids: Optional[List[int]] = None,
    style_instruction: Optional[str] = None,
    style_preset: Optional[str] = None,
) -> Dict[str, Any]:
    """使用 Batch API 翻译 PPTX 文件"""
    start_time = time.time()
    
    try:
        from .services.translator_pptx_direct import translate_pptx
        # 注意：translate_pptx 的签名为 (input_path, output_path, src, tgt, engine="deepseek", max_workers=4, user_id=None, **kwargs)
        # 因此前四个位置参数后，其他参数需使用关键字传递，避免“multiple values for argument 'engine'”。
        result = translate_pptx(
            file_path,
            output_path,
            source_lang,
            target_lang,
            engine="qwen_plus",
            category_ids=category_ids,
            style_instruction=style_instruction,
            style_preset=style_preset,
        )
        
        duration = time.time() - start_time
        result['duration'] = duration
        
        return result
    except Exception as e:
        print(f"PPTX batch translation failed: {e}")
        raise

def translate_xlsx_batch_api(
    file_path: str,
    output_path: str,
    source_lang: str,
    target_lang: str,
    category_ids: Optional[List[int]] = None,
    style_instruction: Optional[str] = None,
    style_preset: Optional[str] = None,
) -> Dict[str, Any]:
    """使用 Batch API + OOXML 方式翻译 XLSX 文件，尽量保留图形/形状文本。"""
    start_time = time.time()
    
    try:
        from .services.translator_xlsx_ooxml import translate_xlsx_ooxml
        # OOXML 路径当前不接收风格参数，后续可在 translate_batch 内统一注入
        result = translate_xlsx_ooxml(
            input_path=file_path,
            output_path=output_path,
            src_lang=source_lang,
            tgt_lang=target_lang,
            engine="qwen_plus",
            user_id=None,
            category_ids=category_ids,
        ) or {}
        
        duration = time.time() - start_time
        result['duration'] = duration
        
        return result
    except Exception as e:
        print(f"XLSX batch translation failed: {e}")
        raise

def translate_text_batch_api(
    file_path: str,
    output_path: str,
    source_lang: str,
    target_lang: str,
    category_ids: Optional[List[int]] = None,
    style_instruction: Optional[str] = None,
    style_preset: Optional[str] = None,
) -> Dict[str, Any]:
    """使用现有的翻译服务翻译文本文件"""
    start_time = time.time()
    
    try:
        # 读取文本文件
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 使用现有的文本翻译服务
        from .services.translator_text import translate_text_direct
        
        # 直接调用文本翻译服务
        result = translate_text_direct(
            file_path, output_path, source_lang, target_lang,
            engine="qwen_plus", user_id=None, category_ids=category_ids
        ) or {}
        
        # 如果翻译失败，尝试简单的逐行翻译
        if not result or not os.path.exists(output_path):
            print("Direct translation failed, trying line-by-line translation...")
            
            # 按行分割文本
            lines = [line.strip() for line in content.split('\n') if line.strip()]
            
            if lines:
                # 使用多引擎翻译器进行逐行翻译
                from .services.multi_engine_translator import translate_batch
                
                # 准备翻译选项
                options = {}
                if style_instruction:
                    options['style_instruction'] = style_instruction
                if style_preset:
                    options['style_preset'] = style_preset
                
                # 翻译所有行
                translated_lines, tokens = translate_batch(
                    lines, source_lang, target_lang, 
                    engine="qwen_plus", **options
                )
                
                # 写入输出文件
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write('\n'.join(translated_lines))
                
                result = {
                    'token_count': tokens,
                    'character_count': len(content),
                    'total_texts': len(lines)
                }
            else:
                # 如果文件为空，直接复制
                import shutil
                shutil.copy2(file_path, output_path)
                result = {
                    'token_count': 0,
                    'character_count': 0,
                    'total_texts': 0
                }
        
        duration = time.time() - start_time
        result['duration'] = duration
        
        return result
        
    except Exception as e:
        print(f"Text batch translation failed: {e}")
        # 如果翻译失败，至少复制原文件
        try:
            import shutil
            shutil.copy2(file_path, output_path)
            return {
                'token_count': 0,
                'character_count': 0,
                'total_texts': 0,
                'duration': time.time() - start_time,
                'error': str(e)
            }
        except Exception as copy_error:
            print(f"Failed to copy original file: {copy_error}")
            raise