#!/usr/bin/env python3
"""
多AI引擎翻译器 - 支持DeepSeek、腾讯原子能力、Kimi等
"""
import os
import json
import time
import logging
import requests
import re
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from .engine_config import EngineConfig

logger = logging.getLogger(__name__)

# --- Qwen3 runtime metrics (process-wide, reset per batch) ---
QWEN3_METRICS = {"total": 0, "success": 0, "429": 0}

def qwen3_reset_metrics():
    try:
        QWEN3_METRICS["total"] = 0
        QWEN3_METRICS["success"] = 0
        QWEN3_METRICS["429"] = 0
    except Exception:
        pass

def qwen3_get_metrics():
    try:
        return {"total": int(QWEN3_METRICS.get("total", 0)), "success": int(QWEN3_METRICS.get("success", 0)), "429": int(QWEN3_METRICS.get("429", 0))}
    except Exception:
        return {"total": 0, "success": 0, "429": 0}

class TranslationEngine(ABC):
    """AI翻译引擎抽象基类"""
    
    def __init__(self, api_key: str, api_url: str, **kwargs):
        self.api_key = api_key
        self.api_url = api_url
        self.max_workers = kwargs.get('max_workers', 5)
        self.timeout = kwargs.get('timeout', 60)
        self.batch_size = kwargs.get('batch_size', 20)
    
    @abstractmethod
    def build_payload(self, texts: List[str], src_lang: str, tgt_lang: str) -> Dict[str, Any]:
        """构建API请求负载"""
        pass
    
    @abstractmethod
    def parse_response(self, response, expected_count: int) -> List[str]:
        """解析API响应"""
        pass
    
    @abstractmethod
    def send_request(self, payload: Dict[str, Any], headers: Dict[str, str]) -> tuple:
        """发送API请求"""
        pass
    
    def translate_batch(self, texts: List[str], src_lang: str, tgt_lang: str) -> tuple:
        """批量翻译（通用实现）"""
        logger.info(f"[{self.__class__.__name__}] Starting batch translation: {len(texts)} texts, {src_lang} -> {tgt_lang}")
        
        if not texts:
            return texts, 0
        
        # 分批处理
        if len(texts) > self.batch_size:
            batch_size = self.batch_size
            logger.info(f"[{self.__class__.__name__}] Large batch detected ({len(texts)} texts), processing in batches of {batch_size}")
            
            all_results = []
            total_tokens = 0
            
            for i in range(0, len(texts), batch_size):
                batch_texts = texts[i:i + batch_size]
                logger.info(f"[{self.__class__.__name__}] Processing batch {i//batch_size + 1}/{(len(texts) + batch_size - 1)//batch_size}: {len(batch_texts)} texts")
                
                try:
                    batch_results, batch_tokens = self._process_batch(batch_texts, src_lang, tgt_lang)
                    all_results.extend(batch_results)
                    total_tokens += batch_tokens
                except Exception as e:
                    logger.error(f"[{self.__class__.__name__}] Batch {i//batch_size + 1} failed: {e}")
                    # 直接返回失败，不使用原文回退
                    logger.error(f"[{self.__class__.__name__}] Youdao API failed, returning failure")
                    raise e
            
            return all_results, total_tokens
        else:
            return self._process_batch(texts, src_lang, tgt_lang)
    
    def _process_batch(self, texts: List[str], src_lang: str, tgt_lang: str) -> tuple:
        """处理单个批次"""
        try:
            logger.info(f"[{self.__class__.__name__}] Building payload for {len(texts)} texts, {src_lang} -> {tgt_lang}")
            payload = self.build_payload(texts, src_lang, tgt_lang)
            headers = self._get_headers()
            
            response, tokens = self.send_request(payload, headers)
            
            if response:
                translated_texts = self.parse_response(response, len(texts))
                
                # 检查是否有有效的翻译结果
                valid_translations = [t for t in translated_texts if t and t.strip()]
                
                if len(valid_translations) == 0:
                    logger.warning(f"[{self.__class__.__name__}] No valid translations received from Qwen3 API")
                    logger.warning(f"[{self.__class__.__name__}] This might be due to language combination not supported or API limits")
                    raise Exception("Qwen3 API failed: No valid translations received")
                
                logger.info(f"[{self.__class__.__name__}] Batch translation successful, got {len(translated_texts)} results")
                
                # 确保结果数量匹配
                if len(translated_texts) >= len(texts):
                    return translated_texts[:len(texts)], tokens
                else:
                    logger.warning(f"[{self.__class__.__name__}] Response count mismatch: expected {len(texts)}, got {len(translated_texts)}")
                    # 使用原文填充缺失的结果
                    results = []
                    for i in range(len(texts)):
                        if i < len(translated_texts):
                            results.append(translated_texts[i])
                        else:
                            results.append(texts[i])  # 使用原文
                    return results, tokens
            else:
                logger.error(f"[{self.__class__.__name__}] Failed to get response from Qwen3 API")
                raise Exception("Qwen3 API failed: No response received")
                
        except Exception as e:
            logger.error(f"[{self.__class__.__name__}] Error in _process_batch: {e}")
            raise e
    
    def _get_headers(self) -> Dict[str, str]:
        """获取请求头"""
        return {"Content-Type": "application/json"}

class DeepSeekTranslator(TranslationEngine):
    """DeepSeek翻译器"""
    
    def __init__(self):
        config = EngineConfig.get_deepseek_config()
        self.api_key = config['api_key']
        self.api_url = config['api_url']
        self.max_workers = config['max_workers']
        self.batch_size = config['batch_size']
        self.timeout = config['timeout']
        self.use_json_format = config.get('use_json_format', False)  # 新增：是否使用JSON格式
        self.json_batch_size = config.get('json_batch_size', 50)    # 新增：JSON格式的批次大小
        
        if not self.api_key:
            raise ValueError("DeepSeek API key is required")
        
        logger.info(f"[{self.__class__.__name__}] Initialized with JSON format: {self.use_json_format}")
    
    def translate_batch(self, texts: List[str], src_lang: str, tgt_lang: str) -> tuple:
        """批量翻译"""
        if not texts:
            return texts, 0
        
        logger.info(f"[{self.__class__.__name__}] Starting batch translation: {len(texts)} texts, {src_lang} -> {tgt_lang}")
        logger.info(f"[{self.__class__.__name__}] Using JSON format: {self.use_json_format}")
        
        if self.use_json_format:
            return self._translate_batch_json(texts, src_lang, tgt_lang)
        else:
            return self._translate_batch_text(texts, src_lang, tgt_lang)
    
    def _translate_batch_json(self, texts: List[str], src_lang: str, tgt_lang: str) -> tuple:
        """使用JSON格式的批量翻译（更高效）"""
        logger.info(f"[{self.__class__.__name__}] Using JSON format for batch translation")
        
        all_results = []
        total_tokens = 0
        
        # 按批次大小分组
        for i in range(0, len(texts), self.json_batch_size):
            batch_texts = texts[i:i + self.json_batch_size]
            logger.info(f"[{self.__class__.__name__}] Processing JSON batch {i//self.json_batch_size + 1}: {len(batch_texts)} texts")
            
            try:
                batch_results, batch_tokens = self._process_batch_json(batch_texts, src_lang, tgt_lang)
                all_results.extend(batch_results)
                total_tokens += batch_tokens
                
                # 添加批次间延迟，避免API限制
                if i + self.json_batch_size < len(texts):
                    time.sleep(0.5)
                    
            except Exception as e:
                logger.error(f"[{self.__class__.__name__}] JSON batch failed: {e}")
                raise e
        
        return all_results, total_tokens
    
    def _translate_batch_text(self, texts: List[str], src_lang: str, tgt_lang: str) -> tuple:
        """使用文本格式的批量翻译（原有方式）"""
        logger.info(f"[{self.__class__.__name__}] Using text format for batch translation")
        
        all_results = []
        total_tokens = 0
        
        # 按批次大小分组
        for i in range(0, len(texts), self.batch_size):
            batch_texts = texts[i:i + self.batch_size]
            logger.info(f"[{self.__class__.__name__}] Processing text batch {i//self.batch_size + 1}: {len(batch_texts)} texts")
            
            try:
                batch_results, batch_tokens = self._process_batch_text(batch_texts, src_lang, tgt_lang)
                all_results.extend(batch_results)
                total_tokens += batch_tokens
                
                # 添加批次间延迟，避免API限制
                if i + self.batch_size < len(texts):
                    time.sleep(0.5)
                    
            except Exception as e:
                logger.error(f"[{self.__class__.__name__}] Text batch failed: {e}")
                raise e
        
        return all_results, total_tokens
    
    def _process_batch_json(self, texts: List[str], src_lang: str, tgt_lang: str) -> tuple:
        """处理JSON格式的批次翻译"""
        # 构建JSON格式的提示词
        prompt = f"""Translate the following texts from {src_lang} to {tgt_lang}. 
Return the result as a JSON array with the same order as input texts.

Input texts:
{json.dumps(texts, ensure_ascii=False)}

Expected output format:
["translated_text_1", "translated_text_2", ...]"""

        payload = {
            "model": "deepseek-chat",
            "messages": [{"role": "user", "content": prompt}],
            "response_format": {"type": "json_object"},
            "temperature": 0.0
        }
        
        try:
            response = self._send_request_json(payload)
            return self._parse_json_response(response, texts)
        except Exception as e:
            logger.error(f"[{self.__class__.__name__}] JSON translation failed: {e}")
            raise e
    
    def _process_batch_text(self, texts: List[str], src_lang: str, tgt_lang: str) -> tuple:
        """处理文本格式的批次翻译（原有方式）"""
        # 构建文本格式的提示词
        prompt = f"Translate the following texts from {src_lang} to {tgt_lang}. Return only the translations, one per line:\n\n"
        prompt += "\n".join(texts)
        
        payload = {
            "model": "deepseek-chat",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.0
        }
        
        try:
            response = self._send_request_text(payload)
            return self._parse_text_response(response, texts)
        except Exception as e:
            logger.error(f"[{self.__class__.__name__}] Text translation failed: {e}")
            raise e
    
    def _send_request_json(self, payload: dict) -> dict:
        """发送JSON格式请求"""
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        logger.info(f"[{self.__class__.__name__}] Sending JSON request to DeepSeek API")
        response = requests.post(
            self.api_url,
            headers=headers,
            json=payload,
            timeout=self.timeout
        )
        
        if response.status_code != 200:
            logger.error(f"[{self.__class__.__name__}] DeepSeek API error: {response.status_code} - {response.text}")
            raise Exception(f"DeepSeek API error: {response.status_code}")
        
        return response.json()
    
    def _send_request_text(self, payload: dict) -> dict:
        """发送文本格式请求（原有方式）"""
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        logger.info(f"[{self.__class__.__name__}] Sending text request to DeepSeek API")
        response = requests.post(
            self.api_url,
            headers=headers,
            json=payload,
            timeout=self.timeout
        )
        
        if response.status_code != 200:
            logger.error(f"[{self.__class__.__name__}] DeepSeek API error: {response.status_code} - {response.text}")
            raise Exception(f"DeepSeek API error: {response.status_code}")
        
        return response.json()
    
    def _parse_json_response(self, response: dict, original_texts: List[str]) -> tuple:
        """解析JSON格式的响应"""
        try:
            content = response['choices'][0]['message']['content']
            logger.info(f"[{self.__class__.__name__}] Raw JSON response length: {len(content)}")
            logger.info(f"[{self.__class__.__name__}] Raw JSON response: {content[:500]}...")
            
            # 保存原始响应到临时文件用于调试
            try:
                import os
                from datetime import datetime
                
                # 创建临时目录
                temp_dir = "/app/temp_responses"
                os.makedirs(temp_dir, exist_ok=True)
                
                # 生成带时间戳的文件名
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"deepseek_response_{timestamp}.json"
                filepath = os.path.join(temp_dir, filename)
                
                # 保存完整响应内容
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(f"// DeepSeek API Response at {timestamp}\n")
                    f.write(f"// Request: {len(original_texts)} texts\n")
                    f.write(f"// Response length: {len(content)}\n")
                    f.write("// Raw response content:\n")
                    f.write(content)
                    f.write("\n\n// Full response object:\n")
                    f.write(json.dumps(response, ensure_ascii=False, indent=2))
                
                logger.info(f"[{self.__class__.__name__}] Response saved to temp file: {filepath}")
                
            except Exception as e:
                logger.warning(f"[{self.__class__.__name__}] Failed to save response to temp file: {e}")
            
            # 尝试直接解析JSON响应
            try:
                parsed = json.loads(content)
                # 1) 直接是数组
                if isinstance(parsed, list):
                    logger.info(f"[{self.__class__.__name__}] Successfully parsed JSON array: {len(parsed)} items")
                    if len(original_texts) == 1 and len(parsed) > 1:
                        return ([" ".join(map(str, parsed))], response.get('usage', {}).get('total_tokens', 0))
                    if len(parsed) != len(original_texts):
                        logger.warning(f"[{self.__class__.__name__}] Translation count mismatch: expected {len(original_texts)}, got {len(parsed)}")
                    cleaned = [t[0] if isinstance(t, list) and t else (t if isinstance(t, str) else str(t)) for t in parsed]
                    return cleaned[:len(original_texts)], response.get('usage', {}).get('total_tokens', 0)
                # 2) 对象，常见 {"translated_texts": [...]}
                if isinstance(parsed, dict):
                    for key in ("translated_texts", "translations", "data", "result"):
                        if key in parsed and isinstance(parsed[key], list):
                            arr = parsed[key]
                            if len(original_texts) == 1 and len(arr) > 1:
                                return ([" ".join(map(str, arr))], response.get('usage', {}).get('total_tokens', 0))
                            cleaned = [t[0] if isinstance(t, list) and t else (t if isinstance(t, str) else str(t)) for t in arr]
                            return cleaned[:len(original_texts)], response.get('usage', {}).get('total_tokens', 0)
            except json.JSONDecodeError as e:
                logger.warning(f"[{self.__class__.__name__}] Direct JSON parsing failed: {e}")
            
            # 如果直接解析失败，尝试提取JSON部分
            import re
            # 优先从对象中提取 translated_texts 数组
            obj_match = re.search(r'\{[\s\S]*?"translated_texts"\s*:\s*(\[[\s\S]*?\])[\s\S]*?\}', content, re.DOTALL)
            if obj_match:
                try:
                    json_content = obj_match.group(1)
                    translations = json.loads(json_content)
                    if isinstance(translations, list):
                        if len(original_texts) == 1 and len(translations) > 1:
                            return ([" ".join(map(str, translations))], response.get('usage', {}).get('total_tokens', 0))
                        cleaned = [t[0] if isinstance(t, list) and t else (t if isinstance(t, str) else str(t)) for t in translations]
                        return cleaned[:len(original_texts)], response.get('usage', {}).get('total_tokens', 0)
                except json.JSONDecodeError as e:
                    logger.warning(f"[{self.__class__.__name__}] Extracted translated_texts parsing failed: {e}")
            # 回退提取任意数组
            json_match = re.search(r'\[[\s\S]*\]', content, re.DOTALL)
            if json_match:
                try:
                    json_content = json_match.group()
                    logger.info(f"[{self.__class__.__name__}] Extracted JSON content: {json_content[:200]}...")
                    translations = json.loads(json_content)
                    if isinstance(translations, list):
                        if len(original_texts) == 1 and len(translations) > 1:
                            return ([" ".join(map(str, translations))], response.get('usage', {}).get('total_tokens', 0))
                        cleaned = [t[0] if isinstance(t, list) and t else (t if isinstance(t, str) else str(t)) for t in translations]
                        return cleaned[:len(original_texts)], response.get('usage', {}).get('total_tokens', 0)
                except json.JSONDecodeError as e:
                    logger.warning(f"[{self.__class__.__name__}] Extracted JSON parsing failed: {e}")
            
            # 如果JSON解析都失败了，尝试按行分割作为最后的回退方案
            lines = [line.strip() for line in content.split('\n') if line.strip()]
            lines = [ln for ln in lines if '"translated_texts"' not in ln]
            logger.warning(f"[{self.__class__.__name__}] JSON parsing failed, fallback to line parsing: {len(lines)} lines")
            
            # 过滤掉非翻译内容（如markdown标记、空行等）
            filtered_lines = []
            for line in lines:
                # 移除markdown代码块标记
                if line.startswith('```') or line.startswith('`'):
                    continue
                # 移除空行
                if not line.strip():
                    continue
                # 移除可能的JSON标记
                if line.startswith('{') or line.startswith('['):
                    continue
                filtered_lines.append(line.strip())
            
            logger.info(f"[{self.__class__.__name__}] Filtered lines: {len(filtered_lines)}")
            return filtered_lines, response.get('usage', {}).get('total_tokens', 0)
            
        except Exception as e:
            logger.error(f"[{self.__class__.__name__}] Failed to parse JSON response: {e}")
            logger.error(f"[{self.__class__.__name__}] Response content: {response}")
            raise Exception(f"Failed to parse DeepSeek JSON response: {e}")
    
    def _parse_text_response(self, response: dict, original_texts: List[str]) -> tuple:
        """解析文本格式的响应（原有方式）"""
        try:
            content = response['choices'][0]['message']['content']
            logger.info(f"[{self.__class__.__name__}] Raw text response: {content[:200]}...")
            
            # 保存原始响应到临时文件用于调试
            try:
                import os
                from datetime import datetime
                
                # 创建临时目录
                temp_dir = "/app/temp_responses"
                os.makedirs(temp_dir, exist_ok=True)
                
                # 生成带时间戳的文件名
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"deepseek_text_response_{timestamp}.txt"
                filepath = os.path.join(temp_dir, filename)
                
                # 保存完整响应内容
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(f"# DeepSeek Text API Response at {timestamp}\n")
                    f.write(f"# Request: {len(original_texts)} texts\n")
                    f.write(f"# Response length: {len(content)}\n")
                    f.write("# Raw response content:\n")
                    f.write(content)
                    f.write("\n\n# Full response object:\n")
                    f.write(json.dumps(response, ensure_ascii=False, indent=2))
                
                logger.info(f"[{self.__class__.__name__}] Text response saved to temp file: {filepath}")
                
            except Exception as e:
                logger.warning(f"[{self.__class__.__name__}] Failed to save text response to temp file: {e}")
            
            # 按行分割并清理
            lines = [line.strip() for line in content.split('\n') if line.strip()]
            
            # 移除可能的编号和标记
            cleaned_lines = []
            for line in lines:
                # 移除常见的编号格式
                cleaned = re.sub(r'^\d+\.\s*', '', line)
                cleaned = re.sub(r'^-\s*', '', cleaned)
                cleaned = re.sub(r'^•\s*', '', cleaned)
                if cleaned.strip():
                    cleaned_lines.append(cleaned.strip())
            
            logger.info(f"[{self.__class__.__name__}] Parsed {len(cleaned_lines)} translations from text response")
            return cleaned_lines, response.get('usage', {}).get('total_tokens', 0)
            
        except Exception as e:
            logger.error(f"[{self.__class__.__name__}] Failed to parse text response: {e}")
            logger.error(f"[{self.__class__.__name__}] Response content: {response}")
            raise Exception(f"Failed to parse DeepSeek text response: {e}")
    
    # 实现抽象方法以保持兼容性
    def build_payload(self, texts: List[str], src_lang: str, tgt_lang: str) -> Dict[str, Any]:
        """构建API请求负载（兼容性方法）"""
        if self.use_json_format:
            return self._build_json_payload(texts, src_lang, tgt_lang)
        else:
            return self._build_text_payload(texts, src_lang, tgt_lang)
    
    def _build_json_payload(self, texts: List[str], src_lang: str, tgt_lang: str) -> Dict[str, Any]:
        """构建JSON格式的请求负载"""
        prompt = f"""Please translate the following texts from {src_lang} to {tgt_lang}.

Input texts:
{json.dumps(texts, ensure_ascii=False)}

Please return ONLY a JSON array with the translations in the same order as the input texts. Do not include any explanations, markdown formatting, or additional text.

Expected output format:
["translated_text_1", "translated_text_2", "translated_text_3", ...]"""

        return {
            "model": "deepseek-chat",
            "messages": [{"role": "user", "content": prompt}],
            "response_format": {"type": "json_object"},
            "temperature": 0.0,
            "max_tokens": 4000  # 确保有足够的token返回完整响应
        }
    
    def _build_text_payload(self, texts: List[str], src_lang: str, tgt_lang: str) -> Dict[str, Any]:
        """构建文本格式的请求负载"""
        prompt = f"Translate the following texts from {src_lang} to {tgt_lang}. Return only the translations, one per line:\n\n"
        prompt += "\n".join(texts)
        
        return {
            "model": "deepseek-chat",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.0
        }
    
    def parse_response(self, response, expected_count: int) -> List[str]:
        """解析API响应（兼容性方法）"""
        if self.use_json_format:
            return self._parse_json_response_compat(response, expected_count)
        else:
            return self._parse_text_response_compat(response, expected_count)
    
    def _parse_json_response_compat(self, response, expected_count: int) -> List[str]:
        """兼容性JSON响应解析"""
        try:
            if hasattr(response, 'json'):
                response_data = response.json()
            else:
                response_data = response
            
            content = response_data['choices'][0]['message']['content']
            logger.info(f"[{self.__class__.__name__}] Raw JSON response: {content[:200]}...")
            
            # 尝试解析JSON响应
            try:
                parsed = json.loads(content)
                # 1) 直接是数组
                if isinstance(parsed, list):
                    logger.info(f"[{self.__class__.__name__}] Successfully parsed JSON array: {len(parsed)} items")
                    if expected_count == 1 and len(parsed) > 1:
                        # 输入只有1条，但返回了多条，合并为单个字符串
                        return [" ".join(map(str, parsed))]
                    return parsed[:expected_count]
                # 2) 是对象，常见为 {"translated_texts": [...]}
                if isinstance(parsed, dict):
                    # 优先 keys: translated_texts / translations / data
                    for key in ("translated_texts", "translations", "data", "result"):
                        if key in parsed and isinstance(parsed[key], list):
                            arr = parsed[key]
                            logger.info(f"[{self.__class__.__name__}] Parsed JSON object key '{key}' as array: {len(arr)} items")
                            if expected_count == 1 and len(arr) > 1:
                                return [" ".join(map(str, arr))]
                            return arr[:expected_count]
                    # 嵌套对象中继续查找
                    for v in parsed.values():
                        if isinstance(v, dict):
                            for key in ("translated_texts", "translations", "data"):
                                if key in v and isinstance(v[key], list):
                                    arr = v[key]
                                    logger.info(f"[{self.__class__.__name__}] Parsed nested JSON key '{key}' as array: {len(arr)} items")
                                    if expected_count == 1 and len(arr) > 1:
                                        return [" ".join(map(str, arr))]
                                    return arr[:expected_count]
            except json.JSONDecodeError:
                pass
            
            # 如果直接解析失败，尝试提取JSON部分
            import re
            # 优先提取对象中的 translated_texts 数组
            obj_match = re.search(r'\{[\s\S]*?"translated_texts"\s*:\s*(\[[\s\S]*?\])[\s\S]*?\}', content, re.DOTALL)
            if obj_match:
                try:
                    arr_str = obj_match.group(1)
                    arr = json.loads(arr_str)
                    if isinstance(arr, list):
                        logger.info(f"[{self.__class__.__name__}] Extracted translated_texts array: {len(arr)} items")
                        if expected_count == 1 and len(arr) > 1:
                            return [" ".join(map(str, arr))]
                        return arr[:expected_count]
                except json.JSONDecodeError:
                    pass
            # 回退提取任何顶层数组
            json_match = re.search(r'\[[\s\S]*\]', content, re.DOTALL)
            if json_match:
                try:
                    any_arr = json.loads(json_match.group())
                    if isinstance(any_arr, list):
                        logger.info(f"[{self.__class__.__name__}] Extracted JSON array from response: {len(any_arr)} items")
                        if expected_count == 1 and len(any_arr) > 1:
                            return [" ".join(map(str, any_arr))]
                        return any_arr[:expected_count]
                except json.JSONDecodeError:
                    pass
            
            # 如果都失败了，尝试按行分割
            lines = [line.strip() for line in content.split('\n') if line.strip()]
            # 过滤掉明显的JSON键行
            lines = [ln for ln in lines if '"translated_texts"' not in ln]
            logger.info(f"[{self.__class__.__name__}] Fallback to line parsing: {len(lines)} lines")
            return lines[:expected_count]
            
        except Exception as e:
            logger.error(f"[{self.__class__.__name__}] Failed to parse JSON response: {e}")
            logger.error(f"[{self.__class__.__name__}] Response content: {response}")
            return [""] * expected_count
    
    def _parse_text_response_compat(self, response, expected_count: int) -> List[str]:
        """兼容性文本响应解析"""
        try:
            if hasattr(response, 'json'):
                response_data = response.json()
            else:
                response_data = response
            
            content = response_data['choices'][0]['message']['content']
            logger.info(f"[{self.__class__.__name__}] Raw text response: {content[:200]}...")
            
            # 按行分割并清理
            lines = [line.strip() for line in content.split('\n') if line.strip()]
            
            # 移除可能的编号和标记
            cleaned_lines = []
            for line in lines:
                # 移除常见的编号格式
                cleaned = re.sub(r'^\d+\.\s*', '', line)
                cleaned = re.sub(r'^-\s*', '', cleaned)
                cleaned = re.sub(r'^•\s*', '', cleaned)
                if cleaned.strip():
                    cleaned_lines.append(cleaned.strip())
            
            logger.info(f"[{self.__class__.__name__}] Parsed {len(cleaned_lines)} translations from text response")
            return cleaned_lines[:expected_count]
            
        except Exception as e:
            logger.error(f"[{self.__class__.__name__}] Failed to parse text response: {e}")
            logger.error(f"[{self.__class__.__name__}] Response content: {response}")
            return [""] * expected_count
    
    def send_request(self, payload: Dict[str, Any], headers: Dict[str, str]) -> tuple:
        """发送API请求（兼容性方法）"""
        try:
            if self.use_json_format:
                response = self._send_request_json(payload)
                return response, response.get('usage', {}).get('total_tokens', 0)
            else:
                response = self._send_request_text(payload)
                return response, response.get('usage', {}).get('total_tokens', 0)
        except Exception as e:
            logger.error(f"[{self.__class__.__name__}] Request failed: {e}")
            return None, 0
    
    def _get_headers(self) -> Dict[str, str]:
        """获取请求头"""
        return {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }

class TencentTranslator(TranslationEngine):
    """腾讯原子能力翻译引擎"""
    
    def __init__(self, **kwargs):
        api_key = kwargs.get('api_key') or os.getenv("TENCENT_API_KEY", "").strip()
        api_url = kwargs.get('api_url') or os.getenv("TENCENT_API_URL", "https://api.tencent.com/translation")
        super().__init__(api_key, api_url, **kwargs)
        
        if not self.api_key:
            raise ValueError("Tencent API key is required")
        
        logger.info(f"TencentTranslator initialized - API URL: {self.api_url}, Batch Size: {self.batch_size}")
    
    def build_payload(self, texts: List[str], src_lang: str, tgt_lang: str) -> Dict[str, Any]:
        """构造腾讯API请求负载"""
        return {
            "Action": "TextTranslate",
            "Version": "2018-03-21",
            "Region": "ap-beijing",
            "SourceText": json.dumps(texts, ensure_ascii=False),
            "Source": src_lang,
            "Target": tgt_lang,
            "ProjectId": 0
        }
    
    def parse_response(self, response, expected_count: int) -> List[str]:
        """解析腾讯API响应"""
        try:
            data = response.json()
            if "Response" in data and "TargetText" in data["Response"]:
                target_text = data["Response"]["TargetText"]
                # 腾讯API返回的是JSON字符串，需要再次解析
                translations = json.loads(target_text)
                if isinstance(translations, list) and len(translations) == expected_count:
                    logger.info(f"Successfully parsed {len(translations)} translations from Tencent")
                    return translations
            
            logger.warning(f"Failed to parse Tencent response properly")
            return [""] * expected_count
        except Exception as e:
            logger.error(f"Tencent response parse error: {e}")
            return [""] * expected_count
    
    def send_request(self, payload: Dict[str, Any], headers: Dict[str, str]) -> tuple:
        """发送腾讯API请求"""
        headers["Authorization"] = f"Bearer {self.api_key}"
        
        try:
            start_time = time.time()
            response = requests.post(self.api_url, headers=headers, json=payload, timeout=self.timeout)
            response.raise_for_status()
            
            elapsed_time = time.time() - start_time
            tokens = 0  # 腾讯API可能不返回token信息
            
            logger.info(f"Tencent request successful, elapsed: {elapsed_time:.2f}s")
            return response, tokens
            
        except Exception as e:
            logger.error(f"Tencent request failed: {e}")
            return None, 0

class KimiTranslator(TranslationEngine):
    """Kimi API翻译引擎"""
    
    def __init__(self, **kwargs):
        api_key = kwargs.get('api_key') or os.getenv("KIMI_API_KEY", "").strip()
        api_url = kwargs.get('api_url') or os.getenv("KIMI_API_URL", "https://api.moonshot.cn/v1/chat/completions")
        super().__init__(api_key, api_url, **kwargs)
        
        if not self.api_key:
            raise ValueError("Kimi API key is required")
        
        # Kimi API对限流比较敏感，降低批次大小和并发数
        self.max_workers = kwargs.get('max_workers', 2)  # 降低并发数
        self.batch_size = kwargs.get('batch_size', 10)   # 降低批次大小
        self.retry_delay = 2  # 重试延迟（秒）
        
        logger.info(f"KimiTranslator initialized - API URL: {self.api_url}, Batch Size: {self.batch_size}, Max Workers: {self.max_workers}")
    
    def build_payload(self, texts: List[str], src_lang: str, tgt_lang: str) -> Dict[str, Any]:
        """构造Kimi API请求负载"""
        system_msg = (
            f"You are a professional translation engine. Translate the following texts from {src_lang} to {tgt_lang}.\n"
            "Return ONLY a valid JSON array of strings with the translations in order.\n"
            "Example: [\"translation1\", \"translation2\", ...]"
        )
        
        user_content = f"Texts to translate:\n{json.dumps(texts, ensure_ascii=False)}"
        
        return {
            "model": "moonshot-v1-8k",
            "messages": [
                {"role": "system", "content": system_msg},
                {"role": "user", "content": user_content}
            ],
            "temperature": 0.1,
            "max_tokens": 4000
        }
    
    def parse_response(self, response, expected_count: int) -> List[str]:
        """解析Kimi API响应"""
        import re
        
        try:
            data = response.json()
            content = data["choices"][0]["message"]["content"].strip()
            
            logger.info(f"Kimi raw response content: {content[:200]}...")
            
            # 尝试直接解析JSON
            try:
                translations = json.loads(content)
                if isinstance(translations, list) and len(translations) == expected_count:
                    logger.info(f"Successfully parsed {len(translations)} translations from Kimi (direct JSON)")
                    return translations
                else:
                    logger.warning(f"Kimi JSON parse: expected {expected_count}, got {len(translations) if isinstance(translations, list) else 'not a list'}")
            except json.JSONDecodeError as e:
                logger.warning(f"Kimi direct JSON parse failed: {e}")
            except Exception as e:
                logger.warning(f"Kimi direct JSON parse error: {e}")
            
            # 尝试正则匹配JSON数组
            match = re.search(r'\s*(\[.*?\])\s*', content, re.DOTALL)
            if match:
                json_str = match.group(1)
                try:
                    translations = json.loads(json_str)
                    if isinstance(translations, list) and len(translations) == expected_count:
                        logger.info(f"Successfully parsed {len(translations)} translations from Kimi (regex)")
                        return translations
                    else:
                        logger.warning(f"Kimi regex JSON parse: expected {expected_count}, got {len(translations) if isinstance(translations, list) else 'not a list'}")
                except json.JSONDecodeError as e:
                    logger.warning(f"Kimi regex JSON parse failed: {e}")
                except Exception as e:
                    logger.warning(f"Kimi regex JSON parse error: {e}")
            
            # 尝试其他格式：可能是换行分隔的翻译
            lines = content.strip().split('\n')
            if len(lines) >= expected_count:
                # 过滤空行和无效内容
                valid_lines = [line.strip() for line in lines if line.strip() and not line.strip().startswith('[') and not line.strip().startswith('{')]
                if len(valid_lines) >= expected_count:
                    logger.info(f"Successfully parsed {len(valid_lines[:expected_count])} translations from Kimi (line-based)")
                    return valid_lines[:expected_count]
            
            logger.warning(f"Failed to parse Kimi response properly, content: {content[:200]}...")
            logger.warning(f"Expected {expected_count} translations, but couldn't parse any valid format")
            return [""] * expected_count
        except Exception as e:
            logger.error(f"Kimi response parse error: {e}")
            return [""] * expected_count
    
    def send_request(self, payload: Dict[str, Any], headers: Dict[str, str]) -> tuple:
        """发送Kimi API请求（含限流处理）"""
        headers["Authorization"] = f"Bearer {self.api_key}"
        
        max_retries = 3
        for attempt in range(max_retries):
            try:
                start_time = time.time()
                response = requests.post(self.api_url, headers=headers, json=payload, timeout=self.timeout)
                
                if response.status_code == 429:  # Too Many Requests
                    if attempt < max_retries - 1:
                        wait_time = self.retry_delay * (2 ** attempt)  # 指数退避
                        logger.warning(f"Kimi API rate limited (429), waiting {wait_time}s before retry {attempt + 1}/{max_retries}")
                        time.sleep(wait_time)
                        continue
                    else:
                        logger.error(f"Kimi API rate limited after {max_retries} attempts")
                        return None, 0
                
                response.raise_for_status()
                
                elapsed_time = time.time() - start_time
                tokens = response.json().get("usage", {}).get("total_tokens", 0)
                
                logger.info(f"Kimi request successful on attempt {attempt + 1}, elapsed: {elapsed_time:.2f}s, tokens: {tokens}")
                return response, tokens
                
            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 429 and attempt < max_retries - 1:
                    wait_time = self.retry_delay * (2 ** attempt)
                    logger.warning(f"Kimi API rate limited (429), waiting {wait_time}s before retry {attempt + 1}/{max_retries}")
                    time.sleep(wait_time)
                    continue
                else:
                    logger.error(f"Kimi request failed on attempt {attempt + 1}: {e}")
                    return None, 0
            except Exception as e:
                logger.error(f"Kimi request failed on attempt {attempt + 1}: {e}")
                if attempt < max_retries - 1:
                    time.sleep(self.retry_delay)
                    continue
                return None, 0
        
        return None, 0
    
    def translate_batch(self, texts: List[str], src_lang: str, tgt_lang: str) -> tuple:
        """Kimi批量翻译（含限流控制）"""
        logger.info(f"[{self.__class__.__name__}] Starting batch translation: {len(texts)} texts, {src_lang} -> {tgt_lang}")
        
        if not texts:
            return texts, 0
        
        # Kimi API对限流敏感，使用更小的批次
        batch_size = min(self.batch_size, 8)  # 进一步降低批次大小
        
        if len(texts) > batch_size:
            logger.info(f"[{self.__class__.__name__}] Large batch detected ({len(texts)} texts), processing in batches of {batch_size}")
            
            all_results = []
            total_tokens = 0
            
            for i in range(0, len(texts), batch_size):
                batch_texts = texts[i:i + batch_size]
                logger.info(f"[{self.__class__.__name__}] Processing batch {i//batch_size + 1}/{(len(texts) + batch_size - 1)//batch_size}: {len(batch_texts)} texts")
                
                try:
                    batch_results, batch_tokens = self._process_batch(batch_texts, src_lang, tgt_lang)
                    all_results.extend(batch_results)
                    total_tokens += batch_tokens
                    
                    # 在批次之间添加延迟，避免触发限流
                    if i + batch_size < len(texts):
                        logger.info(f"Adding delay between batches to avoid rate limiting...")
                        time.sleep(1)  # 1秒延迟
                        
                except Exception as e:
                    logger.error(f"[{self.__class__.__name__}] Batch {i//batch_size + 1} failed: {e}")
                    # 直接返回失败，不使用原文回退
                    logger.error(f"[{self.__class__.__name__}] Youdao API failed, returning failure")
                    raise e
            
            return all_results, total_tokens
        else:
            return self._process_batch(texts, src_lang, tgt_lang)

class YoudaoTranslator(TranslationEngine):
    """有道云批量翻译引擎"""
    
    def __init__(self, **kwargs):
        api_key = kwargs.get('api_key') or os.getenv("YOUDAO_API_KEY", "").strip()
        # 根据官方文档，使用有道智云的新API端点
        api_url = kwargs.get('api_url') or os.getenv("YOUDAO_API_URL", "https://openapi.youdao.com/api")
        app_id = kwargs.get('app_id') or os.getenv("YOUDAO_APP_ID", "").strip()
        app_secret = kwargs.get('app_secret') or os.getenv("YOUDAO_APP_SECRET", "").strip()
        
        # 根据有道云API限制进一步优化批次大小
        # 单次查询最大字符数：5000字符，我们设置为更保守的值
        # 单次查询最大文本数：建议不超过5个，避免API限制
        max_batch_size = kwargs.get('batch_size') or int(os.getenv("YOUDAO_MAX_BATCH_SIZE", "5"))  # 减少到5
        max_chars_per_batch = kwargs.get('max_chars_per_batch') or int(os.getenv("YOUDAO_MAX_CHARS_PER_BATCH", "1000"))  # 减少到1000
        
        super().__init__(api_key, api_url, **kwargs)
        self.app_id = app_id
        self.app_secret = app_secret
        self.max_chars_per_batch = max_chars_per_batch  # 每批次最大字符数
        
        if not self.app_id or not self.app_secret:
            raise ValueError("Youdao APP_ID and APP_SECRET are required")
        
        logger.info(f"YoudaoTranslator initialized - API URL: {self.api_url}, Batch Size: {self.batch_size}, Max Chars per Batch: {self.max_chars_per_batch}")
    
    def _truncate(self, text: str) -> str:
        """有道API要求的truncate函数"""
        if len(text) <= 20:
            return text
        return text[:10] + str(len(text)) + text[-10:]
    
    def _map_language_code(self, lang_code: str) -> str:
        """映射语言代码到有道API支持的格式"""
        language_mapping = {
            'en': 'eng',
            'ja': 'jpn',
            'zh': 'zh-CHS',
            'zh-CN': 'zh-CHS',
            'zh-TW': 'zh-CHT',
            'ko': 'ko',
            'fr': 'fr',
            'de': 'de',
            'es': 'es',
            'ru': 'ru',
            'pt': 'pt',
            'it': 'it',
            'auto': 'zh-CHS'  # 对于中文内容，默认使用zh-CHS
        }
        return language_mapping.get(lang_code, lang_code)
    
    def build_payload(self, texts: List[str], src_lang: str, tgt_lang: str) -> Dict[str, Any]:
        """构造有道云批量翻译API请求负载"""
        import hashlib
        import time
        import uuid
        
        # 映射语言代码
        mapped_src_lang = self._map_language_code(src_lang)
        mapped_tgt_lang = self._map_language_code(tgt_lang)
        
        # 有道云API需要特殊处理
        salt = str(uuid.uuid4())
        curtime = str(int(time.time()))
        
        # 根据官方文档，确保所有文本都是正确的UTF-8编码
        encoded_texts = []
        for text in texts:
            if isinstance(text, str):
                # 确保文本是UTF-8编码，这是官方文档强调的重点
                try:
                    # 强制转换为UTF-8编码
                    text_bytes = text.encode('utf-8')
                    text_utf8 = text_bytes.decode('utf-8')
                    encoded_texts.append(text_utf8)
                    logger.debug(f"[YoudaoTranslator] Text encoded: '{text}' -> '{text_utf8}'")
                except UnicodeError as e:
                    logger.error(f"[YoudaoTranslator] Encoding error for text '{text}': {e}")
                    # 如果编码失败，尝试忽略错误
                    text_utf8 = text.encode('utf-8', errors='ignore').decode('utf-8')
                    encoded_texts.append(text_utf8)
            else:
                # 如果不是字符串，转换为字符串并编码
                text_str = str(text)
                text_utf8 = text_str.encode('utf-8').decode('utf-8')
                encoded_texts.append(text_utf8)
        
        # 计算签名 - 使用官方要求的truncate函数
        input_text = "".join(encoded_texts)  # 合并所有UTF-8编码的文本
        sign_str = self.app_id + self._truncate(input_text) + salt + curtime + self.app_secret
        
        logger.info(f"[YoudaoTranslator] Debug - app_id: {self.app_id}")
        logger.info(f"[YoudaoTranslator] Debug - input_text: {input_text}")
        logger.info(f"[YoudaoTranslator] Debug - truncated: {self._truncate(input_text)}")
        logger.info(f"[YoudaoTranslator] Debug - salt: {salt}")
        logger.info(f"[YoudaoTranslator] Debug - curtime: {curtime}")
        logger.info(f"[YoudaoTranslator] Debug - sign_str: {sign_str}")
        
        # 确保签名字符串是UTF-8编码
        sign_str_encoded = sign_str.encode('utf-8')
        sign = hashlib.sha256(sign_str_encoded).hexdigest()
        logger.info(f"[YoudaoTranslator] Debug - sign: {sign}")
        
        # 构建批量请求参数
        payload = {
            "from": mapped_src_lang,
            "to": mapped_tgt_lang,
            "appKey": self.app_id,
            "salt": salt,
            "sign": sign,
            "signType": "v3",
            "curtime": curtime,
            "vocabId": "general"
        }
        
        # 有道云批量翻译API需要将多个q参数作为列表传递
        # 使用requests的data参数时，会自动处理列表格式
        payload["q"] = encoded_texts
        
        logger.info(f"[YoudaoTranslator] Debug - final payload: {payload}")
        logger.info(f"[YoudaoTranslator] Debug - language mapping: {src_lang} -> {mapped_src_lang}, {tgt_lang} -> {mapped_tgt_lang}")
        
        return payload
    
    def parse_response(self, response, expected_count: int) -> List[str]:
        """解析有道云API响应"""
        try:
            data = response.json()
            logger.info(f"Youdao raw response: {data}")
            
            # 检查是否有错误码
            if "errorCode" in data and data["errorCode"] != "0":
                error_msg = data.get("msg", f"Error code: {data['errorCode']}")
                logger.error(f"Youdao API error: {error_msg}")
                
                # 根据错误码提供具体的错误信息
                if data["errorCode"] == "202":
                    logger.error("Language combination not supported or invalid language codes")
                    logger.error("This might be due to encoding issues. Please ensure all text is UTF-8 encoded.")
                    logger.error("Check if there are any special characters or encoding problems in the input text.")
                elif data["errorCode"] == "101":
                    logger.error("Missing required parameters or authentication failed")
                elif data["errorCode"] == "102":
                    logger.error("Signature verification failed or timestamp expired")
                
                # 返回空结果，让上层处理
                return [""] * expected_count
            
            if "translation" in data:
                translation_text = data["translation"]
                
                if isinstance(translation_text, list):
                    # 如果返回的是列表，直接使用
                    translations = translation_text
                    logger.info(f"Successfully parsed {len(translations)} translations from Youdao (list)")
                else:
                    # 如果返回的是字符串，尝试按原文本分割
                    # 这是一个简化的处理方式，实际应用中可能需要更智能的分割
                    translations = [translation_text]
                    logger.info(f"Successfully parsed 1 translation from Youdao (string)")
                
                # 确保结果数量匹配
                if len(translations) >= expected_count:
                    # 确保返回的是字符串列表，而不是包含字符串的列表的列表
                    result = []
                    for trans in translations[:expected_count]:
                        if isinstance(trans, list):
                            # 如果trans是列表，取第一个元素
                            result.append(trans[0] if trans else "")
                        else:
                            # 如果trans是字符串，直接使用
                            result.append(trans if trans else "")
                    logger.info(f"Returning {len(result)} translations in correct format")
                    return result
                else:
                    # 如果结果数量不够，用原文填充
                    while len(translations) < expected_count:
                        translations.append("")
                    # 同样确保格式正确
                    result = []
                    for trans in translations[:expected_count]:
                        if isinstance(trans, list):
                            result.append(trans[0] if trans else "")
                        else:
                            result.append(trans if trans else "")
                    return result
            
            logger.warning(f"Failed to parse Youdao response properly: {data}")
            return [""] * expected_count
        except Exception as e:
            logger.error(f"Youdao response parse error: {e}")
            return [""] * expected_count
    
    def send_request(self, payload: Dict[str, Any], headers: Dict[str, str]) -> tuple:
        """发送有道云API请求"""
        try:
            start_time = time.time()
            
            # 有道云API不需要Content-Type头，让requests自动处理
            # 移除可能冲突的headers
            clean_headers = {k: v for k, v in headers.items() if k.lower() != 'content-type'}
            
            # 确保payload中的文本都是UTF-8编码
            encoded_payload = {}
            for key, value in payload.items():
                if key == 'q' and isinstance(value, list):
                    # 对q参数中的文本进行UTF-8编码
                    encoded_texts = []
                    for text in value:
                        if isinstance(text, str):
                            # 确保文本是UTF-8编码
                            try:
                                encoded_text = text.encode('utf-8').decode('utf-8')
                                encoded_texts.append(encoded_text)
                            except UnicodeError:
                                # 如果编码有问题，尝试修复
                                encoded_text = text.encode('utf-8', errors='ignore').decode('utf-8')
                                encoded_texts.append(encoded_text)
                        else:
                            encoded_texts.append(str(text))
                    encoded_payload[key] = encoded_texts
                else:
                    encoded_payload[key] = value
            
            logger.info(f"[YoudaoTranslator] Debug - sending request to: {self.api_url}")
            logger.info(f"[YoudaoTranslator] Debug - encoded payload: {encoded_payload}")
            logger.info(f"[YoudaoTranslator] Debug - clean_headers: {clean_headers}")
            
            # 有道云批量翻译API使用POST请求
            response = requests.post(self.api_url, data=encoded_payload, headers=clean_headers, timeout=self.timeout)
            
            logger.info(f"[YoudaoTranslator] Debug - response status: {response.status_code}")
            logger.info(f"[YoudaoTranslator] Debug - response headers: {dict(response.headers)}")
            logger.info(f"[YoudaoTranslator] Debug - response content: {response.text[:500]}")
            
            response.raise_for_status()
            
            elapsed_time = time.time() - start_time
            tokens = 0  # 有道云API不返回token信息
            
            logger.info(f"Youdao request successful, elapsed: {elapsed_time:.2f}s")
            return response, tokens
            
        except Exception as e:
            logger.error(f"Youdao request failed: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Youdao error response: {e.response.text}")
            return None, 0
    
    def translate_batch(self, texts: List[str], src_lang: str, tgt_lang: str) -> tuple:
        """有道云批量翻译（根据字符数智能分批）"""
        logger.info(f"[{self.__class__.__name__}] Starting batch translation: {len(texts)} texts, {src_lang} -> {tgt_lang}")
        
        if not texts:
            return texts, 0
        
        # 检查是否需要两步翻译（中文->英文->目标语言）
        mapped_src = self._map_language_code(src_lang)
        mapped_tgt = self._map_language_code(tgt_lang)
        
        # 有道API支持的语言组合
        supported_combinations = [
            ('zh-CHS', 'eng'),  # 中文 -> 英文
            ('zh-CHT', 'eng'),  # 繁体中文 -> 英文
            ('eng', 'zh-CHS'),  # 英文 -> 中文
            ('eng', 'zh-CHT'),  # 英文 -> 繁体中文
            ('zh-CHS', 'zh-CHT'),  # 简体中文 -> 繁体中文
            ('zh-CHT', 'zh-CHS'),  # 繁体中文 -> 简体中文
        ]
        
        # 检查是否支持直接翻译
        if (mapped_src, mapped_tgt) in supported_combinations:
            logger.info(f"[{self.__class__.__name__}] Direct translation supported: {mapped_src} -> {mapped_tgt}")
            return self._direct_translation(texts, src_lang, tgt_lang)
        
        # 检查是否需要两步翻译（中文->英文->目标语言）
        if mapped_tgt == 'jpn' and mapped_src in ['zh-CHS', 'zh-CHT', 'zh']:
            logger.warning(f"[{self.__class__.__name__}] Language combination {mapped_src} -> {mapped_tgt} not supported by Youdao API")
            logger.error(f"[{self.__class__.__name__}] Youdao API does not support Chinese to Japanese translation, returning failure")
            raise Exception(f"Youdao API does not support language combination: {mapped_src} -> {mapped_tgt}")
        
        # 如果不支持，直接返回失败
        logger.warning(f"[{self.__class__.__name__}] Language combination {mapped_src} -> {mapped_tgt} not supported by Youdao API")
        logger.error(f"[{self.__class__.__name__}] Youdao API does not support this language combination, returning failure")
        raise Exception(f"Youdao API does not support language combination: {mapped_src} -> {mapped_tgt}")
    
    def _direct_translation(self, texts: List[str], src_lang: str, tgt_lang: str) -> tuple:
        """直接翻译（有道API支持的语言组合）"""
        # 根据有道云API的字符数限制来智能分批
        max_chars = self.max_chars_per_batch
        current_chars = sum(len(text) for text in texts)
        
        if current_chars > max_chars:
            logger.info(f"[{self.__class__.__name__}] Large batch detected ({current_chars} chars > {max_chars} limit), processing in smart batches")
            return self._smart_batch_processing(texts, src_lang, tgt_lang)
        else:
            logger.info(f"[{self.__class__.__name__}] Batch within limits ({current_chars} chars <= {max_chars}), processing directly")
            return self._process_batch(texts, src_lang, tgt_lang)
    
    def _smart_batch_processing(self, texts: List[str], src_lang: str, tgt_lang: str) -> tuple:
        """智能分批处理"""
        max_chars = self.max_chars_per_batch
        max_batch_size = 5  # 有道API建议的批次大小，进一步减少避免202错误
        
        all_results = []
        total_tokens = 0
        current_batch = []
        current_batch_chars = 0
        
        for text in texts:
            text_chars = len(text)
            
            # 如果添加这个文本会超过字符限制或批次大小限制，先处理当前批次
            if (current_batch_chars + text_chars > max_chars or len(current_batch) >= max_batch_size) and current_batch:
                logger.info(f"[{self.__class__.__name__}] Processing batch: {len(current_batch)} texts, {current_batch_chars} chars")
                
                try:
                    batch_results, batch_tokens = self._process_batch_with_retry(current_batch, src_lang, tgt_lang)
                    all_results.extend(batch_results)
                    total_tokens += batch_tokens
                except Exception as e:
                    logger.error(f"[{self.__class__.__name__}] Batch failed: {e}")
                    # 直接返回失败，不使用原文回退
                    logger.error(f"[{self.__class__.__name__}] Youdao API failed, returning failure")
                    raise e
                
                # 重置当前批次
                current_batch = [text]
                current_batch_chars = text_chars
            else:
                current_batch.append(text)
                current_batch_chars += text_chars
        
        # 处理最后一个批次
        if current_batch:
            logger.info(f"[{self.__class__.__name__}] Processing final batch: {len(current_batch)} texts, {current_batch_chars} chars")
            
            try:
                batch_results, batch_tokens = self._process_batch_with_retry(current_batch, src_lang, tgt_lang)
                all_results.extend(batch_results)
                total_tokens += batch_tokens
            except Exception as e:
                logger.error(f"[{self.__class__.__name__}] Final batch failed: {e}")
                # 直接返回失败，不使用原文回退
                logger.error(f"[{self.__class__.__name__}] Youdao API failed, returning failure")
                raise e
        
        return all_results, total_tokens
    
    def _process_batch_with_retry(self, texts: List[str], src_lang: str, tgt_lang: str) -> tuple:
        """带重试机制的批次处理"""
        max_retries = 3
        retry_delay = 1  # 秒
        
        for attempt in range(max_retries):
            try:
                logger.info(f"[{self.__class__.__name__}] Attempt {attempt + 1}/{max_retries} for batch of {len(texts)} texts")
                return self._process_batch(texts, src_lang, tgt_lang)
                
            except Exception as e:
                logger.warning(f"[{self.__class__.__name__}] Attempt {attempt + 1} failed: {e}")
                
                if attempt < max_retries - 1:
                    logger.info(f"[{self.__class__.__name__}] Waiting {retry_delay} seconds before retry...")
                    time.sleep(retry_delay)
                    retry_delay *= 2  # 指数退避
                else:
                    logger.error(f"[{self.__class__.__name__}] All retry attempts failed, returning failure")
                    raise e

class Qwen3Translator(TranslationEngine):
    """Qwen3 API翻译引擎"""
    
    def __init__(self, **kwargs):
        from .engine_config import EngineConfig
        cfg = EngineConfig.get_qwen3_config()
        # 支持 DASHSCOPE_API_KEY 作为后备来源
        api_key = (
            kwargs.pop('api_key', None)
            or cfg.get('api_key')
            or os.getenv("QWEN3_API_KEY", "").strip()
            or os.getenv("DASHSCOPE_API_KEY", "").strip()
        )
        api_url = kwargs.pop('api_url', None) or cfg.get('api_url') or os.getenv("QWEN3_API_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions")
        # 合并其余参数，去掉可能重复的键
        extras = {**cfg, **kwargs}
        for k in ('api_key','api_url','model'):
          if k in extras: extras.pop(k)
        super().__init__(api_key, api_url, **extras)
        self.model = (kwargs.get('model') or cfg.get('model') or 'qwen-mt-turbo').strip()
        # 轻微退避与配置化重试上限
        self.retry_delay = float(getattr(self, 'retry_delay', 0.7))
        self.retry_max = int(cfg.get('retry_max', 3))
        # 细粒度轻节流（每请求抖动，降低尖峰并发命中率）
        try:
            self.sleep_between_requests = float(cfg.get('sleep_between_requests', 0.0))
        except Exception:
            self.sleep_between_requests = 0.0
        
        if not self.api_key:
          raise ValueError("Qwen3 API key is required")
        
        logger.info(f"Qwen3Translator initialized - API URL: {self.api_url}, Batch Size: {self.batch_size}")
    
    def build_payload(self, texts: List[str], src_lang: str, tgt_lang: str) -> Dict[str, Any]:
        """构造Qwen3 API请求负载（兼容模式）"""
        content = texts[0] if len(texts) == 1 else "\n".join(texts)

        def _map_lang(lang: str) -> str:
            if not lang:
                return "auto"
            lang = lang.strip().lower()
            mapping = {
                "zh": "Chinese",
                "en": "English",
                "ja": "Japanese",
                "ko": "Korean",
                "de": "German",
                "fr": "French",
                "es": "Spanish",
                "ru": "Russian",
                "it": "Italian",
                "pt": "Portuguese",
                "vi": "Vietnamese",
                "th": "Thai",
            }
            if lang in ("auto",):
                return "auto"
            return mapping.get(lang, lang)

        return {
            "model": self.model,
            "messages": [
                {"role": "user", "content": content}
            ],
            "translation_options": {
                "source_lang": _map_lang(src_lang or "auto"),
                "target_lang": _map_lang(tgt_lang),
            }
        }
    
    def parse_response(self, response, expected_count: int) -> List[str]:
        """解析Qwen3 API响应"""
        import re
        
        try:
            data = response.json()
            content = data["choices"][0]["message"]["content"].strip()
            
            logger.info(f"Qwen3 raw response content: {content[:200]}...")
            
            # 尝试直接解析JSON
            try:
                translations = json.loads(content)
                if isinstance(translations, list) and len(translations) == expected_count:
                    logger.info(f"Successfully parsed {len(translations)} translations from Qwen3 (direct JSON)")
                    return translations
                else:
                    logger.warning(f"Qwen3 JSON parse: expected {expected_count}, got {len(translations) if isinstance(translations, list) else 'not a list'}")
            except json.JSONDecodeError as e:
                logger.warning(f"Qwen3 direct JSON parse failed: {e}")
            except Exception as e:
                logger.warning(f"Qwen3 direct JSON parse error: {e}")
            
            # 尝试正则匹配JSON数组
            match = re.search(r'\s*(\[.*?\])\s*', content, re.DOTALL)
            if match:
                json_str = match.group(1)
                try:
                    translations = json.loads(json_str)
                    if isinstance(translations, list) and len(translations) == expected_count:
                        logger.info(f"Successfully parsed {len(translations)} translations from Qwen3 (regex)")
                        return translations
                    else:
                        logger.warning(f"Qwen3 regex JSON parse: expected {expected_count}, got {len(translations) if isinstance(translations, list) else 'not a list'}")
                except json.JSONDecodeError as e:
                    logger.warning(f"Qwen3 regex JSON parse failed: {e}")
                except Exception as e:
                    logger.warning(f"Qwen3 regex JSON parse error: {e}")
            
            # 尝试其他格式：可能是换行分隔的翻译
            lines = content.strip().split('\n')
            if len(lines) >= expected_count:
                # 过滤空行和无效内容
                valid_lines = [line.strip() for line in lines if line.strip() and not line.strip().startswith('[') and not line.strip().startswith('{')]
                if len(valid_lines) >= expected_count:
                    logger.info(f"Successfully parsed {len(valid_lines[:expected_count])} translations from Qwen3 (line-based)")
                    return valid_lines[:expected_count]
            
            logger.warning(f"Failed to parse Qwen3 response properly, content: {content[:200]}...")
            logger.warning(f"Expected {expected_count} translations, but couldn't parse any valid format")
            return [""] * expected_count
        except Exception as e:
            logger.error(f"Qwen3 response parse error: {e}")
            return [""] * expected_count
    
    def send_request(self, payload: Dict[str, Any], headers: Dict[str, str]) -> tuple:
        """发送Qwen3 API请求（含限流处理）"""
        headers["Authorization"] = f"Bearer {self.api_key}"
        
        max_retries = max(1, self.retry_max)
        for attempt in range(max_retries):
            try:
                start_time = time.time()
                response = requests.post(self.api_url, headers=headers, json=payload, timeout=self.timeout)
                
                if response.status_code == 429:  # Too Many Requests
                    try:
                        QWEN3_METRICS["429"] += 1
                    except Exception:
                        pass
                    if attempt < max_retries - 1:
                        wait_time = self.retry_delay * (2 ** attempt)  # 指数退避
                        logger.warning(f"Qwen3 API rate limited (429), waiting {wait_time}s before retry {attempt + 1}/{max_retries}")
                        time.sleep(wait_time)
                        continue
                    else:
                        logger.error(f"Qwen3 API rate limited after {max_retries} attempts")
                        return None, 0
                
                response.raise_for_status()
                
                elapsed_time = time.time() - start_time
                tokens = response.json().get("usage", {}).get("total_tokens", 0)
                
                logger.info(f"Qwen3 request successful on attempt {attempt + 1}, elapsed: {elapsed_time:.2f}s, tokens: {tokens}")
                return response, tokens
                
            except requests.exceptions.HTTPError as e:
                code = getattr(e.response, 'status_code', None)
                retriable = code in (429, 502, 503)
                try:
                    if code == 429:
                        QWEN3_METRICS["429"] += 1
                except Exception:
                    pass
                if retriable and attempt < max_retries - 1:
                    wait_time = min(self.retry_delay * (1.5 ** attempt) + (0.3 * attempt), 10.0)
                    logger.warning(f"Qwen3 HTTP {code}, sleeping {wait_time:.2f}s then retry {attempt + 1}/{max_retries}")
                    time.sleep(wait_time)
                    continue
                logger.error(f"Qwen3 request failed on attempt {attempt + 1}: {e}")
                return None, 0
            except Exception as e:
                # 其他异常也走带抖动退避，但更短
                logger.error(f"Qwen3 request failed on attempt {attempt + 1}: {e}")
                if attempt < max_retries - 1:
                    time.sleep(min(self.retry_delay + 0.2 * attempt, 4.0))
                    continue
                return None, 0
        
        return None, 0
    
    def translate_batch(self, texts: List[str], src_lang: str, tgt_lang: str) -> tuple:
        """Qwen3：逐条请求，避免多条合并导致解析失败；失败回退原文。
        增加轻节流抖动与可配置的重试上限，降低 429 出现频率。
        """
        logger.info(f"[{self.__class__.__name__}] Starting batch translation: {len(texts)} texts, {src_lang} -> {tgt_lang}")
        if not texts:
            return texts, 0

        # reset metrics per batch
        try:
            qwen3_reset_metrics()
            QWEN3_METRICS["total"] = len(texts)
        except Exception:
            pass

        outputs: List[str] = []
        total_tokens = 0
        for i, t in enumerate(texts):
            # 每条请求前抖动，降低尖峰
            try:
                if self.sleep_between_requests and self.sleep_between_requests > 0:
                    time.sleep(min(self.sleep_between_requests, 0.2))
            except Exception:
                pass
            try:
                payload = self.build_payload([t], src_lang, tgt_lang)
                headers = self._get_headers()
                headers["Authorization"] = f"Bearer {self.api_key}"
                resp, tokens = self.send_request(payload, headers)
                if not resp:
                    outputs.append(t)
                    continue
                parsed = self.parse_response(resp, expected_count=1)
                out = parsed[0] if isinstance(parsed, list) and parsed else ""
                outputs.append(out or t)
                try:
                    if out and out.strip() and out.strip() != t.strip():
                        QWEN3_METRICS["success"] += 1
                except Exception:
                    pass
                try:
                    total_tokens += int(tokens or 0)
                except Exception:
                    pass
                # 轻微节流，降低429概率
                try:
                    time.sleep(0.1)
                except Exception:
                    pass
            except Exception as e:
                logger.warning(f"[{self.__class__.__name__}] item {i} failed: {e}")
                outputs.append(t)
        # summary
        try:
            m = qwen3_get_metrics()
            logger.info(f"Qwen3 summary: total={m['total']} success={m['success']} 429={m['429']}")
        except Exception:
            pass
        return outputs, total_tokens

# 引擎工厂类
class TranslationEngineFactory:
    """翻译引擎工厂类"""
    
    _engines = {
        'deepseek': DeepSeekTranslator,
        'tencent': TencentTranslator,
        'kimi': KimiTranslator,
        'youdao': YoudaoTranslator,
        'qwen3': Qwen3Translator
    }
    
    @classmethod
    def create_engine(cls, engine_name: str, **kwargs) -> TranslationEngine:
        """创建指定的翻译引擎"""
        engine_name = engine_name.lower()
        
        if engine_name not in cls._engines:
            # 延迟注册 qwen_plus，避免文件顶部循环依赖
            if engine_name in ('qwen_plus','qwen-plus'):
                try:
                    from .multi_engine_translator_qwen_plus import QwenPlusChatTranslator
                    cls._engines['qwen_plus'] = QwenPlusChatTranslator
                    engine_name = 'qwen_plus'
                except Exception as e:
                    raise ValueError(f"Unsupported engine: {engine_name}. Failed to load qwen_plus: {e}")
            else:
                raise ValueError(f"Unsupported engine: {engine_name}. Supported engines: {list(cls._engines.keys())}")
        
        engine_class = cls._engines[engine_name]
        return engine_class(**kwargs)
    
    @classmethod
    def get_available_engines(cls) -> List[str]:
        """获取可用的引擎列表"""
        return list(cls._engines.keys())

# 兼容层
def translate_batch(texts, src_lang='auto', tgt_lang='ja', engine='deepseek', debug=False, **options):
    """模块级批量翻译函数，支持多引擎"""
    try:
        translator = TranslationEngineFactory.create_engine(engine)
        # 优先使用带 options 的路径（供聊天式引擎注入风格/指令等）
        if hasattr(translator, 'translate_batch_with_options'):
            return getattr(translator, 'translate_batch_with_options')(texts, src_lang, tgt_lang, **options)
        # 兜底：使用常规路径
        return translator.translate_batch(texts, src_lang, tgt_lang)
    except Exception as e:
        logger.error(f"Failed to create engine {engine}: {e}")
        # 直接返回失败，不使用DeepSeek回退
        logger.error(f"Engine {engine} failed, returning failure")
        raise e
