#!/usr/bin/env python3
"""
多AI引擎翻译器 - 支持DeepSeek、腾讯原子能力、Kimi等
"""
import os
import json
import time
import logging
import requests
from abc import ABC, abstractmethod
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Any, Optional

# --- 配置日志 ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- 配置加载 ---
# load_dotenv() # 移除，改为直接从环境变量加载

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
                    logger.error(f"[{self.__class__.__name__}] Translation failed, returning failure")
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
                logger.info(f"[{self.__class__.__name__}] Batch translation successful, got {len(translated_texts)} results")
                
                # 确保结果数量匹配
                if len(translated_texts) >= len(texts):
                    return [[text] for text in translated_texts[:len(texts)]], tokens
                else:
                    logger.warning(f"[{self.__class__.__name__}] Response count mismatch: expected {len(texts)}, got {len(translated_texts)}")
                    # 使用原文填充缺失的结果
                    results = []
                    for i in range(len(texts)):
                        if i < len(translated_texts):
                            results.append([translated_texts[i]])
                        else:
                            results.append([texts[i]])
                    return results, tokens
            else:
                logger.error(f"[{self.__class__.__name__}] Batch API request failed, using original texts")
                return [[text] for text in texts], 0
                
        except Exception as e:
            logger.error(f"[{self.__class__.__name__}] Batch processing failed: {e}, using original texts")
            return [[text] for text in texts], 0
    
    def _get_headers(self) -> Dict[str, str]:
        """获取请求头"""
        return {"Content-Type": "application/json"}

class DeepSeekTranslator(TranslationEngine):
    """DeepSeek翻译引擎"""
    
    def __init__(self, **kwargs):
        api_key = kwargs.get('api_key') or os.getenv("DEEPSEEK_API_KEY", "").strip()
        api_url = kwargs.get('api_url') or os.getenv("DEEPSEEK_API_URL", "https://api.deepseek.com/v1/chat/completions")
        
        # 从环境变量或配置中获取批次大小设置
        batch_size = kwargs.get('batch_size') or int(os.getenv("DEEPSEEK_BATCH_SIZE", "20"))
        json_batch_size = kwargs.get('json_batch_size') or int(os.getenv("DEEPSEEK_JSON_BATCH_SIZE", "50"))
        use_json_format = kwargs.get('use_json_format') or os.getenv("DEEPSEEK_USE_JSON_FORMAT", "true").lower() == "true"
        
        # 根据是否使用JSON格式选择批次大小
        effective_batch_size = json_batch_size if use_json_format else batch_size
        
        super().__init__(api_key, api_url, batch_size=effective_batch_size, **kwargs)
        
        if not self.api_key:
            raise ValueError("DeepSeek API key is required")
        
        logger.info(f"DeepSeekTranslator initialized - API URL: {self.api_url}, Batch Size: {self.batch_size}, JSON Format: {use_json_format}, JSON Batch Size: {json_batch_size}")
    
    def build_payload(self, texts: List[str], src_lang: str, tgt_lang: str) -> Dict[str, Any]:
        """构造DeepSeek API请求负载"""
        lang_instruction = f"Translate the following texts from {src_lang} to {tgt_lang}."
        
        system_msg = (
            f"You are a professional translation engine. {lang_instruction}\n"
            "Follow these rules:\n"
            "1. PRESERVE all format markers like [b], [/b], [c:#FF0000], etc.\n"
            "2. Return a single, valid JSON array of strings with the translations in order.\n"
            "3. The JSON array must have exactly the same number of items as the input.\n"
            "4. ALWAYS translate the content to the target language, even if it appears to be already in that language."
        )
        
        user_content = f"Source language: {src_lang}\nTarget language: {tgt_lang}\nTexts to translate:\n{json.dumps(texts, ensure_ascii=False)}"
        
        return {
            "model": "deepseek-chat",
            "messages": [
                {"role": "system", "content": system_msg},
                {"role": "user", "content": user_content}
            ],
            "temperature": 0.1
        }
    
    def parse_response(self, response, expected_count: int) -> List[str]:
        """解析DeepSeek API响应"""
        import re
        
        try:
            data = response.json()
            content = data["choices"][0]["message"]["content"].strip()
            
            # 1) 优先尝试把 content 解析为 JSON
            try:
                parsed = json.loads(content)
                # 1.1 直接是数组
                if isinstance(parsed, list):
                    if expected_count == 1 and len(parsed) > 1:
                        return [" ".join(map(str, parsed))]
                    if len(parsed) != expected_count:
                        logger.warning(f"Parsed JSON array count mismatch: expected {expected_count}, got {len(parsed)}")
                    else:
                        logger.info(f"Successfully parsed JSON array: {len(parsed)} items")
                    return parsed if isinstance(parsed, list) else [str(parsed)]
                # 1.2 是对象，常见为 {"translated_texts": [...]}
                if isinstance(parsed, dict):
                    for key in ("translated_texts", "translations", "data", "result"):
                        if key in parsed and isinstance(parsed[key], list):
                            arr = parsed[key]
                            if expected_count == 1 and len(arr) > 1:
                                return [" ".join(map(str, arr))]
                            if len(arr) != expected_count:
                                logger.warning(f"Parsed JSON object key '{key}' count mismatch: expected {expected_count}, got {len(arr)}")
                            else:
                                logger.info(f"Parsed JSON object key '{key}' as array: {len(arr)} items")
                            return arr
                    # 嵌套对象继续查找一次
                    for v in parsed.values():
                        if isinstance(v, dict):
                            for key in ("translated_texts", "translations", "data"):
                                if key in v and isinstance(v[key], list):
                                    arr = v[key]
                                    logger.info(f"Parsed nested JSON key '{key}' as array: {len(arr)} items")
                                    if expected_count == 1 and len(arr) > 1:
                                        return [" ".join(map(str, arr))]
                                    return arr
            except json.JSONDecodeError:
                pass

            # 2) 提取对象中的 translated_texts 数组
            obj_match = re.search(r'\{[\s\S]*?"translated_texts"\s*:\s*(\[[\s\S]*?\])[\s\S]*?\}', content, re.DOTALL)
            if obj_match:
                try:
                    arr = json.loads(obj_match.group(1))
                    if isinstance(arr, list):
                        if expected_count == 1 and len(arr) > 1:
                            return [" ".join(map(str, arr))]
                        if len(arr) != expected_count:
                            logger.warning(f"Extracted translated_texts count mismatch: expected {expected_count}, got {len(arr)}")
                        else:
                            logger.info(f"Extracted translated_texts array: {len(arr)} items")
                        return arr
                except json.JSONDecodeError:
                    pass

            # 3) 退回提取任意 JSON 数组
            match = re.search(r'\s*(\[.*?\])\s*', content, re.DOTALL)
            if match:
                try:
                    json_str = match.group(1)
                    translations = json.loads(json_str)
                    if isinstance(translations, list):
                        if expected_count == 1 and len(translations) > 1:
                            return [" ".join(map(str, translations))]
                        if len(translations) != expected_count:
                            logger.warning(f"Extracted JSON array count mismatch: expected {expected_count}, got {len(translations)}")
                        else:
                            logger.info(f"Successfully extracted {len(translations)} translations")
                        return translations
                except json.JSONDecodeError:
                    pass
            
            logger.warning(f"Failed to parse response properly, content: {content[:100]}...")
            # 回落到原文，保证返回非空字符串
            return [content] if expected_count == 1 else [content for _ in range(expected_count)]
        except Exception as e:
            logger.error(f"Response parse error: {e}")
            return [""] * expected_count
    
    def send_request(self, payload: Dict[str, Any], headers: Dict[str, str]) -> tuple:
        """发送DeepSeek API请求"""
        headers["Authorization"] = f"Bearer {self.api_key}"
        
        try:
            start_time = time.time()
            response = requests.post(self.api_url, headers=headers, json=payload, timeout=self.timeout)
            response.raise_for_status()
            
            elapsed_time = time.time() - start_time
            tokens = response.json().get("usage", {}).get("total_tokens", 0)
            
            logger.info(f"DeepSeek request successful, elapsed: {elapsed_time:.2f}s, tokens: {tokens}")
            return response, tokens
            
        except Exception as e:
            logger.error(f"DeepSeek request failed: {e}")
            return None, 0

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
        # 腾讯API需要特殊的签名认证
        headers["Authorization"] = f"Bearer {self.api_key}"
        
        try:
            start_time = time.time()
            response = requests.post(self.api_url, headers=headers, json=payload, timeout=self.timeout)
            response.raise_for_status()
            
            elapsed_time = time.time() - start_time
            # 腾讯API可能不返回token信息
            tokens = 0
            
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
        
        logger.info(f"KimiTranslator initialized - API URL: {self.api_url}, Batch Size: {self.batch_size}")
    
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
            
            # 尝试直接解析JSON
            try:
                translations = json.loads(content)
                if isinstance(translations, list) and len(translations) == expected_count:
                    logger.info(f"Successfully parsed {len(translations)} translations from Kimi")
                    return translations
            except:
                pass
            
            # 尝试正则匹配JSON数组
            match = re.search(r'\s*(\[.*?\])\s*', content, re.DOTALL)
            if match:
                json_str = match.group(1)
                translations = json.loads(json_str)
                if isinstance(translations, list) and len(translations) == expected_count:
                    logger.info(f"Successfully parsed {len(translations)} translations from Kimi (regex)")
                    return translations
            
            logger.warning(f"Failed to parse Kimi response properly, content: {content[:100]}...")
            return [""] * expected_count
        except Exception as e:
            logger.error(f"Kimi response parse error: {e}")
            return [""] * expected_count
    
    def send_request(self, payload: Dict[str, Any], headers: Dict[str, str]) -> tuple:
        """发送Kimi API请求"""
        headers["Authorization"] = f"Bearer {self.api_key}"
        
        try:
            start_time = time.time()
            response = requests.post(self.api_url, headers=headers, json=payload, timeout=self.timeout)
            response.raise_for_status()
            
            elapsed_time = time.time() - start_time
            tokens = response.json().get("usage", {}).get("total_tokens", 0)
            
            logger.info(f"Kimi request successful, elapsed: {elapsed_time:.2f}s, tokens: {tokens}")
            return response, tokens
            
        except Exception as e:
            logger.error(f"Kimi request failed: {e}")
            return None, 0

# 引擎工厂类
class TranslationEngineFactory:
    """翻译引擎工厂类"""
    
    _engines = {
        'deepseek': DeepSeekTranslator,
        'tencent': TencentTranslator,
        'kimi': KimiTranslator,
        'youdao': None,  # 将在下面动态导入
        'qwen3': None,   # 将在下面动态导入
        'qwen_plus': None,  # 延迟导入
    }
    
    @classmethod
    def create_engine(cls, engine_name: str, **kwargs) -> TranslationEngine:
        """创建指定的翻译引擎"""
        engine_name = engine_name.lower()
        
        # 动态导入翻译器（避免循环导入）
        if engine_name == 'youdao' and cls._engines['youdao'] is None:
            try:
                from .multi_engine_translator import YoudaoTranslator
                cls._engines['youdao'] = YoudaoTranslator
            except ImportError as e:
                logger.error(f"Failed to import YoudaoTranslator: {e}")
                raise ValueError(f"YoudaoTranslator not available: {e}")
        if engine_name == 'qwen3' and cls._engines['qwen3'] is None:
            try:
                from .multi_engine_translator import Qwen3Translator
                cls._engines['qwen3'] = Qwen3Translator
            except ImportError as e:
                logger.error(f"Failed to import Qwen3Translator: {e}")
                raise ValueError(f"Qwen3Translator not available: {e}")
        if engine_name in ('qwen_plus','qwen-plus') and cls._engines.get('qwen_plus') is None:
            try:
                from .multi_engine_translator_qwen_plus import QwenPlusChatTranslator
                cls._engines['qwen_plus'] = QwenPlusChatTranslator
                engine_name = 'qwen_plus'
            except ImportError as e:
                logger.error(f"Failed to import QwenPlusChatTranslator: {e}")
                raise ValueError(f"QwenPlusChatTranslator not available: {e}")
        
        if engine_name not in cls._engines or cls._engines[engine_name] is None:
            raise ValueError(f"Unsupported engine: {engine_name}. Supported engines: {list(cls._engines.keys())}")
        
        engine_class = cls._engines[engine_name]
        return engine_class(**kwargs)
    
    @classmethod
    def get_available_engines(cls) -> List[str]:
        """获取可用的引擎列表"""
        return [engine for engine in cls._engines.keys() if cls._engines[engine] is not None]

# --- 兼容层 ---
# _translator_instance = DeepSeekTranslator(debug=True) # 移除，改为使用工厂类

def translate_batch(texts, src_lang='auto', tgt_lang='ja', engine='deepseek', debug=False, **options):
    """模块级批量翻译函数，支持多引擎"""
    logger.info(f"[translate_batch] Starting translation with engine: {engine}")
    logger.info(f"[translate_batch] Texts count: {len(texts)}, src_lang: {src_lang}, tgt_lang: {tgt_lang}")
    
    # 根据引擎类型创建对应的翻译器
    try:
        logger.info(f"[translate_batch] Creating engine: {engine}")
        translator = TranslationEngineFactory.create_engine(engine)
        logger.info(f"[translate_batch] Engine created successfully: {type(translator).__name__}")
        
        # 若引擎支持带 options 的入口，优先走该路径
        if hasattr(translator, 'translate_batch_with_options'):
            result = translator.translate_batch_with_options(texts, src_lang, tgt_lang, **options)
        else:
            result = translator.translate_batch(texts, src_lang, tgt_lang)
        logger.info(f"[translate_batch] Translation completed, result type: {type(result)}, result length: {len(result) if isinstance(result, (list, tuple)) else 'N/A'}")
        
        # 清理翻译结果：移除可能的额外包装
        if isinstance(result, (list, tuple)) and len(result) >= 2:
            translated_texts = result[0]
            token_count = result[1]
            
            if isinstance(translated_texts, list):
                logger.info(f"[translate_batch] Cleaning translation results...")
                cleaned_translations = []
                for trans in translated_texts:
                    if isinstance(trans, list) and len(trans) == 1:
                        # 如果翻译结果被包装在列表中，提取出来
                        cleaned_translations.append(trans[0])
                        logger.debug(f"[translate_batch] Unwrapped: {trans} -> {trans[0]}")
                    elif isinstance(trans, str):
                        # 如果翻译结果是字符串，直接使用
                        cleaned_translations.append(trans)
                    else:
                        # 其他情况，转换为字符串
                        cleaned_translations.append(str(trans))
                
                logger.info(f"[translate_batch] Cleaned {len(cleaned_translations)} translations")
                return cleaned_translations, token_count
        
        return result
        
    except Exception as e:
        logger.error(f"[translate_batch] Failed to create engine {engine}: {e}")
        # 直接返回失败，不使用DeepSeek回退
        logger.error(f"[translate_batch] Engine {engine} failed, returning failure")
        raise e

# --- 简化测试函数 ---
def simple_translate(text, src_lang='auto', tgt_lang='ja'):
    """简化的翻译函数，用于测试"""
    import requests
    import os
    
    logger.info(f"Simple translate: '{text[:50]}...' from {src_lang} to {tgt_lang}")
    
    api_key = os.getenv("DEEPSEEK_API_KEY", "").strip() # 使用DeepSeek的API key作为默认
    if not api_key:
        logger.error("No API key found")
        return text, 0
    
    api_url = os.getenv("DEEPSEEK_API_URL", "https://api.deepseek.com/v1/chat/completions") # 使用DeepSeek的API URL作为默认
    
    payload = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content": "You are a professional translator. Translate the text to the target language."},
            {"role": "user", "content": f"Translate '{text}' from {src_lang} to {tgt_lang}"}
        ],
        "temperature": 0.1,
        "max_tokens": 200
    }
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    try:
        start_time = time.time()
        logger.info("Sending request to DeepSeek API...")
        
        response = requests.post(api_url, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        
        elapsed_time = time.time() - start_time
        data = response.json()
        content = data["choices"][0]["message"]["content"].strip()
        tokens = data.get("usage", {}).get("total_tokens", 0)
        
        logger.info(f"Translation successful in {elapsed_time:.2f}s, tokens: {tokens}")
        return content, tokens
        
    except Exception as e:
        logger.error(f"Translation error: {e}")
        return text, 0
