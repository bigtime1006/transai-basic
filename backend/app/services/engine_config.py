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
    def get_deepseek_config() -> Dict[str, Any]:
        """获取DeepSeek翻译配置"""
        return {
            'api_key': os.getenv("DEEPSEEK_API_KEY", "").strip(),
            'api_url': os.getenv("DEEPSEEK_API_URL", "https://api.deepseek.com/v1/chat/completions"),
            'max_workers': int(os.getenv("DEEPSEEK_MAX_WORKERS", "10")),
            'batch_size': int(os.getenv("DEEPSEEK_BATCH_SIZE", "20")),
            'timeout': int(os.getenv("DEEPSEEK_TIMEOUT", "60")),
            'use_json_format': os.getenv("DEEPSEEK_USE_JSON_FORMAT", "true").lower() == "true",  # 默认启用JSON格式
            'json_batch_size': int(os.getenv("DEEPSEEK_JSON_BATCH_SIZE", "50"))  # 新增：JSON格式的批次大小
        }
    
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
            'batch_size': int(os.getenv("TENCENT_BATCH_SIZE", "50")),  # 腾讯支持更大的批次
            'timeout': int(os.getenv("TENCENT_TIMEOUT", "60"))
        }
    
    @staticmethod
    def get_kimi_config() -> Dict[str, Any]:
        """获取Kimi API配置"""
        return {
            'api_key': os.getenv("KIMI_API_KEY", "").strip(),
            'api_url': os.getenv("KIMI_API_URL", "https://api.moonshot.cn/v1/chat/completions"),
            'max_workers': int(os.getenv("KIMI_MAX_WORKERS", "5")),
            'batch_size': int(os.getenv("KIMI_BATCH_SIZE", "30")),
            'timeout': int(os.getenv("KIMI_TIMEOUT", "60"))
        }
    
    @staticmethod
    def get_qwen3_config() -> Dict[str, Any]:
        """获取 Qwen3 配置（阿里通义）"""
        # 1) 先用环境变量做为默认
        cfg = {
            'api_key': (os.getenv("QWEN3_API_KEY", "") or os.getenv("DASHSCOPE_API_KEY", "")).strip(),
            'api_url': os.getenv("QWEN3_API_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"),
            'max_workers': int(os.getenv("QWEN3_MAX_WORKERS", "12")),
            'batch_size': int(os.getenv("QWEN3_BATCH_SIZE", "50")),
            'timeout': int(os.getenv("QWEN3_TIMEOUT", "60")),
            'model': os.getenv("QWEN3_MODEL", "qwen-mt-turbo")
        }

        # 2) 若可用，优先从数据库 translation_engines 表读取 qwen3 的 api_config 覆盖
        if SessionLocal and models is not None:
            try:
                db = SessionLocal()
                # 兼容不同命名：qwen3 / qwen / qwen-mt
                engine = (
                    db.query(models.TranslationEngine)
                    .filter(models.TranslationEngine.engine_name.in_(['qwen3','qwen','qwen-mt']))
                    .first()
                )
                if engine and engine.api_config:
                    api_conf = engine.api_config or {}
                    if isinstance(api_conf, dict):
                        cfg['api_key'] = (api_conf.get('api_key') or cfg['api_key'] or "").strip()
                        cfg['api_url'] = api_conf.get('api_url') or cfg['api_url']
                        cfg['model'] = (api_conf.get('model') or cfg['model']).strip()
                        if 'max_workers' in api_conf:
                            cfg['max_workers'] = int(api_conf.get('max_workers') or cfg['max_workers'])
                        if 'batch_size' in api_conf:
                            cfg['batch_size'] = int(api_conf.get('batch_size') or cfg['batch_size'])
                        if 'timeout' in api_conf:
                            cfg['timeout'] = int(api_conf.get('timeout') or cfg['timeout'])
                        # 可选：细粒度控制
                        if 'sleep_between_requests' in api_conf:
                            try:
                                cfg['sleep_between_requests'] = float(api_conf.get('sleep_between_requests'))
                            except Exception:
                                pass
                        if 'retry_max' in api_conf:
                            try:
                                cfg['retry_max'] = int(api_conf.get('retry_max'))
                            except Exception:
                                pass
                # 3) 如未在引擎配置中指定模型，尝试从系统设置中读取（engine_qwen3.qwen3_model）
                if not cfg.get('model'):
                    try:
                        setting = (
                            db.query(models.SystemSetting)
                            .filter(models.SystemSetting.category == 'engine_qwen3')
                            .filter(models.SystemSetting.key == 'qwen3_model')
                            .first()
                        )
                        if setting and setting.value:
                            cfg['model'] = str(setting.value).strip()
                    except Exception:
                        pass
            except Exception:
                pass
            finally:
                try:
                    db.close()
                except Exception:
                    pass

        return cfg

    @staticmethod
    def get_qwen_plus_config() -> Dict[str, Any]:
        """获取 Qwen Plus（聊天式）配置（阿里通义 OpenAI 兼容）"""
        cfg = {
            'api_key': (os.getenv("DASHSCOPE_API_KEY", "") or os.getenv("QWEN3_API_KEY", "")).strip(),
            'api_url': os.getenv("QWEN_PLUS_API_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"),
            'model': os.getenv("QWEN_PLUS_MODEL", "qwen-plus"),
            'max_workers': int(os.getenv("QWEN_PLUS_MAX_WORKERS", "10")),
            'batch_size': int(os.getenv("QWEN_PLUS_BATCH_SIZE", "30")),
            'timeout': int(os.getenv("QWEN_PLUS_TIMEOUT", "60")),
            # 节流/重试（可由管理端覆盖）
            'retry_max': int(os.getenv("QWEN_PLUS_RETRY_MAX", "3")),
            'sleep_between_requests': float(os.getenv("QWEN_PLUS_SLEEP_BETWEEN_REQUESTS", "0.05")),
        }

        # 2) 如DB存在 translation_engines 配置，以其为准
        if SessionLocal and models is not None:
            try:
                db = SessionLocal()
                engine = (
                    db.query(models.TranslationEngine)
                    .filter(models.TranslationEngine.engine_name.in_(['qwen_plus','qwen-plus']))
                    .first()
                )
                if engine and engine.api_config and isinstance(engine.api_config, dict):
                    api_conf = engine.api_config
                    cfg['api_key'] = (api_conf.get('api_key') or cfg['api_key'] or "").strip()
                    cfg['api_url'] = api_conf.get('api_url') or cfg['api_url']
                    cfg['model'] = (api_conf.get('model') or cfg['model']).strip()
                    for k in ('max_workers','batch_size','timeout','retry_max'):
                        if k in api_conf and api_conf.get(k) is not None:
                            try:
                                cfg[k] = int(api_conf[k])
                            except Exception:
                                pass
                    if 'sleep_between_requests' in api_conf and api_conf.get('sleep_between_requests') is not None:
                        try:
                            cfg['sleep_between_requests'] = float(api_conf.get('sleep_between_requests'))
                        except Exception:
                            pass
            except Exception:
                pass
            finally:
                try:
                    db.close()
                except Exception:
                    pass

        return cfg
    
    @staticmethod
    def get_youdao_config() -> Dict[str, Any]:
        """获取有道云翻译配置"""
        return {
            'api_key': os.getenv("YOUDAO_API_KEY", "").strip(),
            'api_url': os.getenv("YOUDAO_API_URL", "https://openapi.youdao.com/api"),
            'app_id': os.getenv("YOUDAO_APP_ID", "").strip(),
            'app_secret': os.getenv("YOUDAO_APP_SECRET", "").strip(),
            'max_workers': int(os.getenv("YOUDAO_MAX_WORKERS", "3")),
            'batch_size': int(os.getenv("YOUDAO_BATCH_SIZE", "10")),  # 有道云建议小批次
            'timeout': int(os.getenv("YOUDAO_TIMEOUT", "60"))
        }
    
    @staticmethod
    def get_engine_config(engine_name: str) -> Dict[str, Any]:
        """获取指定引擎的配置"""
        engine_name = engine_name.lower()
        
        if engine_name == 'deepseek':
            return EngineConfig.get_deepseek_config()
        elif engine_name == 'tencent':
            return EngineConfig.get_tencent_config()
        elif engine_name == 'kimi':
            return EngineConfig.get_kimi_config()
        elif engine_name == 'youdao':
            return EngineConfig.get_youdao_config()
        elif engine_name == 'qwen3':
            return EngineConfig.get_qwen3_config()
        elif engine_name in ('qwen_plus','qwen-plus'):
            return EngineConfig.get_qwen_plus_config()
        else:
            raise ValueError(f"Unsupported engine: {engine_name}")
    
    @staticmethod
    def is_engine_available(engine_name: str) -> bool:
        """检查指定引擎是否可用（有API密钥）"""
        try:
            config = EngineConfig.get_engine_config(engine_name)
            if engine_name == 'youdao':
                # 有道云需要app_id和app_secret
                return bool(config.get('app_id') and config.get('app_secret'))
            else:
                return bool(config.get('api_key'))
        except:
            return False
    
    @staticmethod
    def get_available_engines() -> list:
        """获取所有可用的引擎列表"""
        available = []
        engines = ['deepseek', 'tencent', 'kimi', 'youdao', 'qwen3', 'qwen_plus']
        
        for engine in engines:
            if EngineConfig.is_engine_available(engine):
                available.append(engine)
        
        return available
    
    @staticmethod
    def get_default_engine() -> str:
        """获取默认引擎（优先DeepSeek，其次其他可用引擎）"""
        if EngineConfig.is_engine_available('deepseek'):
            return 'deepseek'
        
        available = EngineConfig.get_available_engines()
        if available:
            return available[0]
        
        return 'deepseek'  # 如果都没有配置，返回DeepSeek作为默认值
