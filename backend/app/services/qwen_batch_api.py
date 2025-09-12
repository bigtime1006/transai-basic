#!/usr/bin/env python3
"""
Qwen Plus Batch API 服务
用于批量文件翻译，避免限流，降低成本
"""
import json
import time
import logging
import requests
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta

from .engine_config import EngineConfig

logger = logging.getLogger(__name__)


class QwenBatchAPI:
    """Qwen Plus Batch API 客户端"""
    
    def __init__(self, **kwargs):
        cfg = EngineConfig.get_qwen_plus_config()
        self.api_key = kwargs.get('api_key') or cfg.get('api_key')
        self.api_url = kwargs.get('api_url') or cfg.get('api_url')
        self.model = kwargs.get('model') or cfg.get('model') or 'qwen-plus'
        
        if not self.api_key:
            raise ValueError("Qwen Plus API key is required")
        
        # Batch API 特定配置
        self.batch_api_url = self.api_url.replace('/v1/chat/completions', '/v1/batch')
        self.max_batch_size = kwargs.get('max_batch_size', 100)  # 单批次最大文件数
        self.max_wait_time = kwargs.get('max_wait_time', 3600)   # 最大等待时间（秒）
        
    def create_batch_job(self, 
                         texts: List[str], 
                         src_lang: str, 
                         tgt_lang: str,
                         **options) -> Dict[str, Any]:
        """创建批量翻译任务"""
        
        # 构建 Batch API 请求
        batch_request = {
            "model": self.model,
            "input_file_id": None,  # 需要先上传文件
            "endpoint": "/v1/chat/completions",
            "completion_window": self.max_wait_time,
            "metadata": {
                "source_lang": src_lang,
                "target_lang": tgt_lang,
                "style_preset": options.get('style_preset'),
                "style_instruction": options.get('style_instruction'),
                "enable_thinking": options.get('enable_thinking', False)
            }
        }
        
        # 构建聊天消息
        style_instruction = (options.get('style_instruction') or '').strip()
        style_preset = (options.get('style_preset') or '').strip()
        enable_thinking = bool(options.get('enable_thinking', False))
        
        system_parts = [
            "You are a professional translation engine.",
            f"Translate each item from {src_lang} to {tgt_lang} while preserving the item order.",
            "Return ONLY a valid JSON array of strings with exactly the same number of items as the input array.",
            "Do not include any keys, labels, comments, or extra text outside the JSON array.",
        ]
        if style_preset:
            system_parts.append(f"Writing style preset: {style_preset}.")
        if style_instruction:
            system_parts.append(f"Additional style instruction: {style_instruction}.")
            
        user_content = (
            "Here is the input array (JSON):\n" +
            json.dumps(texts, ensure_ascii=False) +
            f"\nReturn ONLY the translated JSON array of length {len(texts)}."
        )
        
        messages = [
            {"role": "system", "content": " ".join(system_parts)},
            {"role": "user", "content": user_content},
        ]
        
        # 构建 OpenAI 兼容的请求体
        request_body = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.0,
        }
        if enable_thinking:
            request_body["enable_thinking"] = True
            
        batch_request["request_body"] = request_body
        
        return batch_request
    
    def submit_batch_job(self, batch_request: Dict[str, Any]) -> str:
        """提交批量任务，返回 batch_id"""
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        try:
            response = requests.post(
                self.batch_api_url,
                headers=headers,
                json=batch_request,
                timeout=30
            )
            response.raise_for_status()
            
            result = response.json()
            batch_id = result.get('id')
            if not batch_id:
                raise ValueError("No batch ID returned from API")
                
            logger.info(f"Batch job created: {batch_id}")
            return batch_id
            
        except Exception as e:
            logger.error(f"Failed to create batch job: {e}")
            raise
    
    def get_batch_status(self, batch_id: str) -> Dict[str, Any]:
        """获取批量任务状态"""
        
        headers = {
            "Authorization": f"Bearer {self.api_key}"
        }
        
        try:
            response = requests.get(
                f"{self.batch_api_url}/{batch_id}",
                headers=headers,
                timeout=30
            )
            response.raise_for_status()
            
            return response.json()
            
        except Exception as e:
            logger.error(f"Failed to get batch status: {e}")
            raise
    
    def get_batch_results(self, batch_id: str) -> Optional[List[Dict[str, Any]]]:
        """获取批量任务结果"""
        
        status = self.get_batch_status(batch_id)
        
        if status.get('status') != 'completed':
            return None
            
        # 获取结果文件
        output_file_id = status.get('output_file_id')
        if not output_file_id:
            return None
            
        # 这里需要下载结果文件并解析
        # 由于 Batch API 的结果格式可能不同，需要根据实际 API 响应调整
        try:
            # 下载结果文件的逻辑
            # 解析翻译结果
            # 返回格式化的结果
            pass
        except Exception as e:
            logger.error(f"Failed to get batch results: {e}")
            return None
            
        return None
    
    def wait_for_completion(self, batch_id: str, 
                          check_interval: int = 30,
                          max_wait: int = None) -> Dict[str, Any]:
        """等待批量任务完成"""
        
        if max_wait is None:
            max_wait = self.max_wait_time
            
        start_time = time.time()
        
        while True:
            if time.time() - start_time > max_wait:
                raise TimeoutError(f"Batch job {batch_id} did not complete within {max_wait} seconds")
                
            status = self.get_batch_status(batch_id)
            current_status = status.get('status')
            
            if current_status == 'completed':
                logger.info(f"Batch job {batch_id} completed successfully")
                return status
            elif current_status == 'failed':
                error = status.get('error', {})
                raise RuntimeError(f"Batch job {batch_id} failed: {error}")
            elif current_status in ['pending', 'running']:
                logger.info(f"Batch job {batch_id} status: {current_status}")
                time.sleep(check_interval)
            else:
                logger.warning(f"Unknown batch status: {current_status}")
                time.sleep(check_interval)


def create_batch_translation_job(texts: List[str], 
                                src_lang: str, 
                                tgt_lang: str,
                                **options) -> str:
    """便捷函数：创建批量翻译任务"""
    
    batch_api = QwenBatchAPI()
    batch_request = batch_api.create_batch_job(texts, src_lang, tgt_lang, **options)
    return batch_api.submit_batch_job(batch_request)


def get_batch_translation_status(batch_id: str) -> Dict[str, Any]:
    """便捷函数：获取批量翻译状态"""
    
    batch_api = QwenBatchAPI()
    return batch_api.get_batch_status(batch_id)


def wait_for_batch_completion(batch_id: str, **kwargs) -> Dict[str, Any]:
    """便捷函数：等待批量翻译完成"""
    
    batch_api = QwenBatchAPI()
    return batch_api.wait_for_completion(batch_id, **kwargs)
