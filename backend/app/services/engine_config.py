#!/usr/bin/env python3
"""
多AI引擎配置文件
"""
import os
from typing import Dict, Any
try:
    from ..database import SessionLocal
    from .. import models
except Exception:
    SessionLocal = None
    models = None

class EngineConfig:
    """AI引擎配置管理类"""
    
    @staticmethod
    def _get_config_from_db(engine_names: list, defaults: dict) -> dict:
        """从数据库加载配置并与默认值合并"""
        cfg = defaults.copy()
        if not (SessionLocal and models):
            return cfg
        
        db = None
        try:
            db = SessionLocal()
            engine = (
                db.query(models.TranslationEngine)
                .filter(models.TranslationEngine.engine_name.in_(engine_names))
                .first()
            )
            if engine and isinstance(engine.api_config, dict):
                api_conf = engine.api_config
                # 合并配置，数据库中的值优先
                for key, value in api_conf.items():
                    if value is not None:
                        # 类型转换以确保安全
                        if key in cfg and isinstance(cfg[key], int):
                            try: cfg[key] = int(value)
                            except (ValueError, TypeError): pass
                        elif key in cfg and isinstance(cfg[key], float):
                            try: cfg[key] = float(value)
                            except (ValueError, TypeError): pass
                        elif key in cfg and isinstance(cfg[key], bool):
                            cfg[key] = str(value).lower() in ('true', '1', 'yes')
                        else:
                            cfg[key] = value
        except Exception as e:
            # 在日志中记录错误会更好，但这里保持静默失败
            print(f"Error reading engine config from DB: {e}")
        finally:
            if db:
                db.close()
        return cfg

    @staticmethod
    def get_deepseek_config() -> Dict[str, Any]:
        """获取DeepSeek翻译配置"""
        defaults = {
            'api_key': os.getenv("DEEPSEEK_API_KEY", "").strip(),
            'api_url': os.getenv("DEEPSEEK_API_URL", "https://api.deepseek.com/v1/chat/completions"),
            'model': os.getenv("DEEPSEEK_MODEL", "deepseek-chat"),
            'max_workers': int(os.getenv("DEEPSEEK_MAX_WORKERS", "10")),
            'batch_size': int(os.getenv("DEEPSEEK_BATCH_SIZE", "20")),
            'timeout': int(os.getenv("DEEPSEEK_TIMEOUT", "60")),
            'use_json_format': os.getenv("DEEPSEEK_USE_JSON_FORMAT", "true").lower() == "true",
            'json_batch_size': int(os.getenv("DEEPSEEK_JSON_BATCH_SIZE", "50"))
        }
        return EngineConfig._get_config_from_db(['deepseek'], defaults)

    @staticmethod
    def get_tencent_config() -> Dict[str, Any]:
        """获取腾讯原子能力配置"""
        return {
            'api_key': os.getenv("TENCENT_API_KEY", "").strip(),
            'api_url': os.getenv("TENCENT_API_URL", "https://tmt.tencentcloudapi.com"),
            'secret_id': os.getenv("TENCENT_SECRET_ID", "").strip(),
            'secret_key': os.getenv("TENCENT_SECRET_KEY", "").strip(),
            'region': os.getenv("TENCENT_REGION", "ap-beijing"),
            'max_workers': int(os.getenv("TENCENT_MAX_WORKERS", "5")),
            'batch_size': int(os.getenv("TENCENT_BATCH_SIZE", "50")),
            'timeout': int(os.getenv("TENCENT_TIMEOUT", "60"))
        }
    
    @staticmethod
    def get_kimi_config() -> Dict[str, Any]:
        """获取Kimi API配置"""
        defaults = {
            'api_key': os.getenv("KIMI_API_KEY", "").strip(),
            'api_url': os.getenv("KIMI_API_URL", "https://api.moonshot.cn/v1/chat/completions"),
            'model': os.getenv("KIMI_MODEL", "moonshot-v1-8k"),
            'max_workers': int(os.getenv("KIMI_MAX_WORKERS", "5")),
            'batch_size': int(os.getenv("KIMI_BATCH_SIZE", "30")),
            'timeout': int(os.getenv("KIMI_TIMEOUT", "60"))
        }
        return EngineConfig._get_config_from_db(['kimi'], defaults)

    @staticmethod
    def get_qwen3_config() -> Dict[str, Any]:
        """获取 Qwen3 配置（阿里通义）"""
        defaults = {
            'api_key': (os.getenv("QWEN3_API_KEY", "") or os.getenv("DASHSCOPE_API_KEY", "")).strip(),
            'api_url': os.getenv("QWEN3_API_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"),
            'max_workers': int(os.getenv("QWEN3_MAX_WORKERS", "12")),
            'batch_size': int(os.getenv("QWEN3_BATCH_SIZE", "50")),
            'timeout': int(os.getenv("QWEN3_TIMEOUT", "60")),
            'model': os.getenv("QWEN3_MODEL", "qwen-mt-turbo")
        }
        return EngineConfig._get_config_from_db(['qwen3', 'qwen', 'qwen-mt'], defaults)

    @staticmethod
    def get_qwen_plus_config() -> Dict[str, Any]:
        """获取 Qwen Plus 配置（阿里通义 OpenAI 兼容）"""
        defaults = {
            'api_key': (os.getenv("DASHSCOPE_API_KEY", "") or os.getenv("QWEN3_API_KEY", "")).strip(),
            'api_url': os.getenv("QWEN_PLUS_API_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"),
            'model': os.getenv("QWEN_PLUS_MODEL", "qwen-plus"),
            'max_workers': int(os.getenv("QWEN_PLUS_MAX_WORKERS", "10")),
            'batch_size': int(os.getenv("QWEN_PLUS_BATCH_SIZE", "30")),
            'timeout': int(os.getenv("QWEN_PLUS_TIMEOUT", "60")),
            'retry_max': int(os.getenv("QWEN_PLUS_RETRY_MAX", "3")),
            'sleep_between_requests': float(os.getenv("QWEN_PLUS_SLEEP_BETWEEN_REQUESTS", "0.05")),
        }
        return EngineConfig._get_config_from_db(['qwen_plus', 'qwen-plus'], defaults)
    
    @staticmethod
    def get_youdao_config() -> Dict[str, Any]:
        """获取有道云翻译配置"""
        return {
            'api_key': os.getenv("YOUDAO_API_KEY", "").strip(),
            'api_url': os.getenv("YOUDAO_API_URL", "https://openapi.youdao.com/api"),
            'app_id': os.getenv("YOUDAO_APP_ID", "").strip(),
            'app_secret': os.getenv("YOUDAO_APP_SECRET", "").strip(),
            'max_workers': int(os.getenv("YOUDAO_MAX_WORKERS", "3")),
            'batch_size': int(os.getenv("YOUDAO_BATCH_SIZE", "10")),
            'timeout': int(os.getenv("YOUDAO_TIMEOUT", "60"))
        }

    @staticmethod
    def get_chatgpt_config() -> Dict[str, Any]:
        """获取ChatGPT配置 (样例)"""
        defaults = {
            'api_key': os.getenv("CHATGPT_API_KEY", "").strip(),
            'api_url': os.getenv("CHATGPT_API_URL", "https://api.openai.com/v1/chat/completions"),
            'model': os.getenv("CHATGPT_MODEL", "gpt-4o"),
            'max_workers': int(os.getenv("CHATGPT_MAX_WORKERS", "5")),
            'batch_size': int(os.getenv("CHATGPT_BATCH_SIZE", "20")),
            'timeout': int(os.getenv("CHATGPT_TIMEOUT", "60")),
        }
        return EngineConfig._get_config_from_db(['chatgpt', 'openai'], defaults)

    @staticmethod
    def get_gemini_config() -> Dict[str, Any]:
        """获取Gemini配置 (样例)"""
        defaults = {
            'api_key': os.getenv("GEMINI_API_KEY", "").strip(),
            'api_url': os.getenv("GEMINI_API_URL", "https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent"),
            'model': os.getenv("GEMINI_MODEL", "gemini-pro"),
            'max_workers': int(os.getenv("GEMINI_MAX_WORKERS", "5")),
            'batch_size': int(os.getenv("GEMINI_BATCH_SIZE", "20")),
            'timeout': int(os.getenv("GEMINI_TIMEOUT", "60")),
        }
        return EngineConfig._get_config_from_db(['gemini', 'google'], defaults)

    @staticmethod
    def get_engine_config(engine_name: str) -> Dict[str, Any]:
        """获取指定引擎的配置"""
        engine_map = {
            'deepseek': EngineConfig.get_deepseek_config,
            'tencent': EngineConfig.get_tencent_config,
            'kimi': EngineConfig.get_kimi_config,
            'youdao': EngineConfig.get_youdao_config,
            'qwen3': EngineConfig.get_qwen3_config,
            'qwen_plus': EngineConfig.get_qwen_plus_config,
            'qwen-plus': EngineConfig.get_qwen_plus_config,
            'chatgpt': EngineConfig.get_chatgpt_config,
            'gemini': EngineConfig.get_gemini_config,
        }
        engine_func = engine_map.get(engine_name.lower())
        if engine_func:
            return engine_func()
        raise ValueError(f"Unsupported engine: {engine_name}")
    
    @staticmethod
    def is_engine_available(engine_name: str) -> bool:
        """检查指定引擎是否可用（有API密钥）"""
        try:
            config = EngineConfig.get_engine_config(engine_name)
            if engine_name == 'youdao':
                return bool(config.get('app_id') and config.get('app_secret'))
            return bool(config.get('api_key'))
        except ValueError:
            return False
    
    @staticmethod
    def get_available_engines() -> list:
        """获取所有可用的引擎列表"""
        # 增加对新引擎的检查
        engines = ['deepseek', 'tencent', 'kimi', 'youdao', 'qwen3', 'qwen_plus', 'chatgpt', 'gemini']
        return [engine for engine in engines if EngineConfig.is_engine_available(engine)]
    
    @staticmethod
    def get_default_engine() -> str:
        """获取默认引擎（优先DeepSeek，其次其他可用引擎）"""
        if EngineConfig.is_engine_available('deepseek'):
            return 'deepseek'
        
        available = EngineConfig.get_available_engines()
        return available[0] if available else 'deepseek'
