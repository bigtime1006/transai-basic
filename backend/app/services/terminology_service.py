import os
import re
import time
from typing import List, Tuple, Dict, Optional, Union

# Local app imports
from app.database import SessionLocal
from app import crud


TERMINOLOGY_CACHE_TTL_SECONDS = int(os.getenv("TERMINOLOGY_CACHE_TTL_SECONDS", "300"))


class _TerminologyCache:
    def __init__(self):
        # key: (src_lang, tgt_lang) -> {"expire": ts, "terms": List[Tuple[src, tgt]]}
        self._store: Dict[Tuple[str, str], Dict[str, object]] = {}

    def get(self, src_lang: str, tgt_lang: str) -> Optional[List[Tuple[str, str]]]:
        key = (src_lang or "", tgt_lang or "")
        entry = self._store.get(key)
        if not entry:
            return None
        if entry["expire"] < time.time():
            self._store.pop(key, None)
            return None
        return entry["terms"]  # type: ignore

    def set(self, src_lang: str, tgt_lang: str, terms: List[Tuple[str, str]]):
        key = (src_lang or "", tgt_lang or "")
        self._store[key] = {
            "expire": time.time() + TERMINOLOGY_CACHE_TTL_SECONDS,
            "terms": terms,
        }


_cache = _TerminologyCache()


def _to_bool(value: Optional[str], default: bool = True) -> bool:
    if value is None:
        return default
    v = value.strip().lower()
    return v in ("1", "true", "yes", "on")


def is_terminology_enabled(db=None) -> bool:
    should_close = False
    if db is None:
        db = SessionLocal()
        should_close = True
    try:
        setting = crud.get_system_setting_by_key(db, "terminology_enabled")
        if not setting:
            # default enabled
            return True
        return _to_bool(setting.value, True)
    finally:
        if should_close:
            db.close()


def get_terminology_options(db=None) -> Dict[str, object]:
    """Fetch minimal options for terminology processing.
    - terminology_enabled: bool (default True)
    - case_sensitive: bool (default False)
    - categories_enabled: bool (default True)
    - max_categories_per_translation: int (default 10)
    """
    should_close = False
    if db is None:
        db = SessionLocal()
        should_close = True
    try:
        enabled = is_terminology_enabled(db)
        case_sensitive = False
        cs_setting = crud.get_system_setting_by_key(db, "terminology_case_sensitive")
        if cs_setting:
            case_sensitive = _to_bool(cs_setting.value, False)
        
        # 新增分类相关配置
        categories_enabled = True
        cs_enabled_setting = crud.get_system_setting_by_key(db, "terminology_categories_enabled")
        if cs_enabled_setting:
            categories_enabled = _to_bool(cs_enabled_setting.value, True)
        
        max_categories = 10
        max_cat_setting = crud.get_system_setting_by_key(db, "terminology_max_categories_per_translation")
        if max_cat_setting and max_cat_setting.value.isdigit():
            max_categories = int(max_cat_setting.value)
        
        return {
            "terminology_enabled": enabled,
            "case_sensitive": case_sensitive,
            "categories_enabled": categories_enabled,
            "max_categories_per_translation": max_categories,
        }
    finally:
        if should_close:
            db.close()


def _load_terms_by_categories(db, category_ids: List[int], src_lang: str, tgt_lang: str, user_id: Optional[Union[int, str]] = None) -> List[Tuple[str, str]]:
    """根据分类ID列表加载术语"""
    if not category_ids:
        return []
    
    # 使用新的CRUD函数按分类加载术语
    terms = crud.get_terms_by_categories(db, category_ids, src_lang, tgt_lang, user_id)
    pairs: List[Tuple[str, str]] = []
    for t in terms:
        # Normalize to str pairs
        pairs.append((t.source_text, t.target_text))

    # Sort by source length desc for longest-match-first
    pairs.sort(key=lambda x: len(x[0] or ""), reverse=True)
    
    return pairs


def _load_terms(db, src_lang: str, tgt_lang: str, user_id: Optional[Union[int, str]] = None) -> List[Tuple[str, str]]:
    # Try cache first
    cached = _cache.get(src_lang, tgt_lang)
    if cached is not None:
        return cached

    # Only public + approved terms for MVP
    # If user_id provided (or env var present), include user's private terms as well
    if user_id is None:
        env_uid = os.getenv("TERMINOLOGY_USER_ID")
        user_id = int(env_uid) if env_uid and env_uid.isdigit() else None

    terms = crud.get_terms_by_lang_pair(db, src_lang=src_lang, tgt_lang=tgt_lang, only_public=(user_id is None), user_id=(int(user_id) if user_id is not None else None))
    pairs: List[Tuple[str, str]] = []
    for t in terms:
        # Normalize to str pairs
        pairs.append((t.source_text, t.target_text))

    # Sort by source length desc for longest-match-first
    pairs.sort(key=lambda x: len(x[0] or ""), reverse=True)

    _cache.set(src_lang, tgt_lang, pairs)
    return pairs


def preprocess_texts_with_categories(db, texts: List[str], src_lang: str, tgt_lang: str, 
                                   category_ids: List[int], case_sensitive: bool = False, 
                                   user_id: Optional[Union[int, str]] = None) -> Tuple[List[str], List[Dict[str, str]]]:
    """根据分类ID列表进行术语前处理"""
    if not texts or not category_ids:
        return texts, [{} for _ in texts]

    terms = _load_terms_by_categories(db, category_ids, src_lang, tgt_lang, user_id)
    if not terms:
        return texts, [{} for _ in texts]

    flags = 0 if case_sensitive else re.IGNORECASE
    # Use ASCII sentinel placeholders that models通常会保留，且不易与自然文本冲突
    # Each placeholder is unique per term index
    placeholders = [f"__TRANS_TERM_{i}__" for i in range(len(terms))]
    patterns = [re.compile(re.escape(src), flags) for src, _ in terms]

    processed_list: List[str] = []
    mappings: List[Dict[str, str]] = []
    for text in texts:
        if not isinstance(text, str) or not text:
            processed_list.append(text)
            mappings.append({})
            continue

        mapping: Dict[str, str] = {}
        processed = text
        # Replace by descending length order
        for idx, ((src, tgt), pattern) in enumerate(zip(terms, patterns)):
            placeholder = placeholders[idx]
            if pattern.search(processed):
                # 仅替换完整匹配，避免数字/标号误替换；保留原文边界
                processed = pattern.sub(placeholder, processed)
                mapping[placeholder] = tgt

        processed_list.append(processed)
        mappings.append(mapping)

    return processed_list, mappings


def preprocess_texts(db, texts: List[str], src_lang: str, tgt_lang: str, case_sensitive: bool = False, user_id: Optional[Union[int, str]] = None) -> Tuple[List[str], List[Dict[str, str]]]:
    """Replace source terms with placeholders to protect them from being altered by models.
    Returns processed_texts and a list of mapping dicts per text: placeholder -> target_term.
    """
    if not texts:
        return texts, [{} for _ in range(0)]

    terms = _load_terms(db, src_lang, tgt_lang, user_id=user_id)
    if not terms:
        return texts, [{} for _ in texts]

    flags = 0 if case_sensitive else re.IGNORECASE
    # Use ASCII sentinel placeholders that models通常会保留，且不易与自然文本冲突
    # Each placeholder is unique per term index
    placeholders = [f"__TRANS_TERM_{i}__" for i in range(len(terms))]
    patterns = [re.compile(re.escape(src), flags) for src, _ in terms]

    processed_list: List[str] = []
    mappings: List[Dict[str, str]] = []
    for text in texts:
        if not isinstance(text, str) or not text:
            processed_list.append(text)
            mappings.append({})
            continue

        mapping: Dict[str, str] = {}
        processed = text
        # Replace by descending length order
        for idx, ((src, tgt), pattern) in enumerate(zip(terms, patterns)):
            placeholder = placeholders[idx]
            if pattern.search(processed):
                # 仅替换完整匹配，避免数字/标号误替换；保留原文边界
                processed = pattern.sub(placeholder, processed)
                mapping[placeholder] = tgt

        processed_list.append(processed)
        mappings.append(mapping)

    return processed_list, mappings


def postprocess_texts(translated_texts: List[str], mappings: List[Dict[str, str]]) -> List[str]:
    if not translated_texts or not mappings:
        return translated_texts
    if len(translated_texts) != len(mappings):
        # Best-effort: pad mappings
        if len(mappings) < len(translated_texts):
            mappings = mappings + [{} for _ in range(len(translated_texts) - len(mappings))]
        else:
            mappings = mappings[:len(translated_texts)]

    results: List[str] = []
    for text, mapping in zip(translated_texts, mappings):
        if not mapping:
            results.append(text)
            continue
        fixed = text
        for placeholder, tgt in mapping.items():
            fixed = fixed.replace(placeholder, tgt)
        results.append(fixed)
    return results


def record_translation_term_set(db, translation_id: str, translation_type: str, category_ids: List[int]):
    """记录翻译任务使用的术语分类"""
    try:
        from .. import crud
        term_set = {
            "translation_id": translation_id,
            "translation_type": translation_type,
            "category_ids": category_ids
        }
        crud.create_translation_term_set(db, term_set)
    except Exception as e:
        # 记录失败不影响翻译流程
        print(f"Failed to record translation term set: {e}")


