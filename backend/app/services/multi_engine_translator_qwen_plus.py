#!/usr/bin/env python3
import json
import time
import logging
import requests
from typing import List, Dict, Any

from .engine_config import EngineConfig
from .multi_engine_translator import TranslationEngine

logger = logging.getLogger(__name__)


class QwenPlusChatTranslator(TranslationEngine):
    """Qwen Plus 聊天式翻译引擎（OpenAI 兼容模式）"""

    def __init__(self, **kwargs):
        cfg = EngineConfig.get_qwen_plus_config()
        api_key = kwargs.get('api_key') or cfg.get('api_key')
        api_url = kwargs.get('api_url') or cfg.get('api_url')
        super().__init__(api_key, api_url, **{
            'max_workers': kwargs.get('max_workers', cfg.get('max_workers', 10)),
            'batch_size': kwargs.get('batch_size', cfg.get('batch_size', 30)),
            'timeout': kwargs.get('timeout', cfg.get('timeout', 60)),
        })
        self.model = (kwargs.get('model') or cfg.get('model') or 'qwen-plus').strip()
        self.retry_max = int(kwargs.get('retry_max', cfg.get('retry_max', 3)))
        try:
            self.sleep_between_requests = float(kwargs.get('sleep_between_requests', cfg.get('sleep_between_requests', 0.05)))
        except Exception:
            self.sleep_between_requests = 0.05

        if not self.api_key:
            raise ValueError("Qwen Plus API key is required")

    def build_payload(self, texts: List[str], src_lang: str, tgt_lang: str, **options) -> Dict[str, Any]:
        """构造聊天式 payload；强制严格 JSON 数组输出，避免逐行分割导致错位。"""
        style_instruction = (options.get('style_instruction') or '').strip()
        style_preset = (options.get('style_preset') or '').strip()
        enable_thinking = bool(options.get('enable_thinking', False))

        # 将输入以 JSON 数组提供给模型，要求仅返回等长 JSON 数组（严格顺序对齐）
        input_array = texts
        expected_len = len(input_array)

        system_parts = [
            "You are a professional translation engine.",
            f"Translate each item strictly into {tgt_lang} regardless of the detected language.",
            "Preserve the item order and formatting markers.",
            "Return ONLY a valid JSON array of strings with exactly the same number of items as the input array.",
            "Do not include any keys, labels, comments, or extra text outside the JSON array.",
        ]
        if style_preset:
            system_parts.append(f"Writing style preset: {style_preset}.")
        if style_instruction:
            system_parts.append(f"Additional style instruction: {style_instruction}.")

        user_content = (
            "Here is the input array (JSON):\n" +
            json.dumps(input_array, ensure_ascii=False) +
            f"\nReturn ONLY the translated JSON array of length {expected_len}."
        )

        messages = [
            {"role": "system", "content": " ".join(system_parts)},
            {"role": "user", "content": user_content},
        ]

        payload: Dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.0,
        }
        if enable_thinking:
            payload["enable_thinking"] = True

        return payload

    # 为工厂的 options 传递提供扩展入口
    def translate_batch_with_options(self, texts: List[str], src_lang: str, tgt_lang: str, **options) -> tuple:
        if not texts:
            return texts, 0
        all_results: List[str] = []
        total_tokens = 0
        batch_size = self.batch_size
        for i in range(0, len(texts), batch_size):
            chunk = texts[i:i+batch_size]
            payload = self.build_payload(chunk, src_lang, tgt_lang, **options)
            resp, tokens = self.send_request(payload, {})
            if not resp:
                # 失败则原文回填
                all_results.extend(chunk)
                continue
            parsed = self.parse_response(resp, expected_count=len(chunk))
            if parsed and len(parsed) == len(chunk):
                # 空串视为无效，回退原文，避免清空内容
                for j, val in enumerate(parsed):
                    if isinstance(val, str) and val.strip():
                        all_results.append(val)
                    else:
                        all_results.append(chunk[j])
            else:
                # 尺寸不一致时尽量对齐，缺失回填原文
                for j in range(len(chunk)):
                    cand = parsed[j] if (isinstance(parsed, list) and j < len(parsed)) else None
                    if isinstance(cand, str) and cand.strip():
                        all_results.append(cand)
                    else:
                        all_results.append(chunk[j])
            try:
                total_tokens += int(tokens or 0)
            except Exception:
                pass
            # 轻微节流
            try:
                time.sleep(self.sleep_between_requests)
            except Exception:
                pass
        return all_results, total_tokens

    def parse_response(self, response, expected_count: int) -> List[str]:
        try:
            data = response.json() if hasattr(response, 'json') else response
            content = data["choices"][0]["message"].get("content", "").strip()
            # 1) 直接 JSON
            try:
                arr = json.loads(content)
                if isinstance(arr, list):
                    return [str(x) for x in arr][:expected_count]
            except Exception:
                pass
            # 2) 正则提取 JSON 数组
            import re
            m = re.search(r"\[\s*[\"']?", content)
            if m:
                try:
                    start = content.find('[', m.start())
                    end = content.rfind(']')
                    if start != -1 and end != -1 and end > start:
                        arr2 = json.loads(content[start:end+1])
                        if isinstance(arr2, list):
                            return [str(x) for x in arr2][:expected_count]
                except Exception:
                    pass
            # 3) 逐行回退（弱退路，仅当完全找不到 JSON 时使用）
            lines = [ln.strip() for ln in content.split('\n') if ln.strip()]
            if len(lines) >= expected_count:
                return lines[:expected_count]
            # 若长度不够，返回空串占位以触发上层用原文补齐
            return [""] * expected_count
        except Exception as e:
            logger.error(f"Qwen Plus parse error: {e}")
            return [""] * expected_count

    def send_request(self, payload: Dict[str, Any], options: Dict[str, Any]) -> tuple:
        """发送请求到 Qwen Plus API"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        retry_count = 0
        while retry_count <= self.retry_max:
            try:
                start_time = time.time()
                response = requests.post(
                    self.api_url,
                    headers=headers,
                    json=payload,
                    timeout=self.timeout
                )
                
                if response.status_code == 200:
                    result = response.json()
                    # 提取 token 使用量
                    usage = result.get('usage', {})
                    total_tokens = usage.get('total_tokens', 0)
                    
                    # 应用请求间隔
                    if self.sleep_between_requests > 0:
                        time.sleep(self.sleep_between_requests)
                    
                    return result, total_tokens
                
                elif response.status_code == 429:
                    # 限流错误，等待后重试
                    retry_count += 1
                    if retry_count <= self.retry_max:
                        wait_time = 2 ** retry_count  # 指数退避
                        logger.warning(f"Rate limited, waiting {wait_time}s before retry {retry_count}")
                        time.sleep(wait_time)
                        continue
                    else:
                        logger.error("Max retries exceeded for rate limit")
                        return None, 0
                
                elif response.status_code >= 500:
                    # 服务器错误，重试
                    retry_count += 1
                    if retry_count <= self.retry_max:
                        wait_time = 2 ** retry_count
                        logger.warning(f"Server error {response.status_code}, waiting {wait_time}s before retry {retry_count}")
                        time.sleep(wait_time)
                        continue
                    else:
                        logger.error(f"Max retries exceeded for server error {response.status_code}")
                        return None, 0
                
                else:
                    # 其他错误
                    logger.error(f"API request failed with status {response.status_code}: {response.text}")
                    return None, 0
                    
            except requests.exceptions.Timeout:
                retry_count += 1
                if retry_count <= self.retry_max:
                    logger.warning(f"Request timeout, retry {retry_count}")
                    continue
                else:
                    logger.error("Max retries exceeded for timeout")
                    return None, 0
                    
            except Exception as e:
                logger.error(f"Request failed: {e}")
                return None, 0
        
        return None, 0


