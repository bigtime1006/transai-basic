import sys
import zipfile
import shutil
import os
from io import BytesIO
from lxml import etree as ET
from concurrent.futures import ThreadPoolExecutor, as_completed
from app.services.utils_translator import translate_batch
from app.services.utils_translator import translate_batch as _tb2
from app.services.terminology_service import (
    get_terminology_options,
    preprocess_texts,
    preprocess_texts_with_categories,
    postprocess_texts,
)
from app.database import SessionLocal


def is_translatable(text):
    """判断是否需要翻译：去掉首尾空格后为空、纯数字、纯符号则跳过"""
    if not text or not text.strip():
        return False
    stripped = text.strip()
    if stripped.isdigit():
        return False
    if all(not ch.isalnum() for ch in stripped):
        return False
    return True


def batch_translate_with_retry(texts, src_lang, tgt_lang, engine, debug=False, **options):
    """批量翻译，失败时自动拆分重试"""
    try:
        res = translate_batch(texts, src_lang, tgt_lang, engine=engine, **options)
        # 统一返回为 List[str]
        return res[0] if isinstance(res, tuple) else res
    except Exception as e:
        if debug:
            print(f"[Retry] batch of {len(texts)} failed: {e}")
        if len(texts) == 1:
            res = translate_batch(texts, src_lang, tgt_lang, engine=engine, **options)
            return res[0] if isinstance(res, tuple) else res
        mid = len(texts) // 2
        left = batch_translate_with_retry(texts[:mid], src_lang, tgt_lang, engine, debug, **options)
        right = batch_translate_with_retry(texts[mid:], src_lang, tgt_lang, engine, debug, **options)
        return left + right


def parallel_translate(texts, src_lang, tgt_lang, engine, workers=5, debug=False, **options):
    """多线程并行批量翻译，保持顺序"""
    if not texts:
        return []

    chunk_size = max(1, len(texts) // workers)
    chunks = [(i, texts[i:i + chunk_size]) for i in range(0, len(texts), chunk_size)]
    results_map = {}

    if debug:
        print(f"[Parallel] {len(texts)} texts split into {len(chunks)} chunks, {workers} workers.")

    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {
            executor.submit(batch_translate_with_retry, chunk, src_lang, tgt_lang, engine, debug, **options): idx
            for idx, chunk in chunks
        }
        for future in as_completed(futures):
            idx = futures[future]
            try:
                # 结果应为 List[str]
                results_map[idx] = future.result()
            except Exception as e:
                if debug:
                    print(f"[Parallel] Chunk {idx} failed: {e}")
                results_map[idx] = []

    # 按原顺序合并
    translated_texts = []
    for i in sorted(results_map.keys()):
        translated_texts.extend(results_map[i])

    return translated_texts


def translate_docx_inplace(input_path, output_path, src_lang, tgt_lang, engine="deepseek", workers=5, debug=False, user_id: int | None = None, **kwargs):
    total_token_count = 0
    total_character_count = 0
    # 1. 打开 DOCX zip
    with zipfile.ZipFile(input_path, "r") as zin:
        xml_parts = [p for p in zin.namelist() if p.startswith("word/") and p.endswith(".xml")]

        trees = {}
        text_nodes = []
        original_texts = []

        for part in xml_parts:
            with zin.open(part) as f:
                tree = ET.parse(f)
                root = tree.getroot()
                ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}

                for node in root.xpath(".//w:t", namespaces=ns):
                    txt = node.text
                    if is_translatable(txt):
                        text_nodes.append((part, node))
                        original_texts.append(txt)
                        total_character_count += len(txt)

                trees[part] = tree

        # 2. 去重
        unique_texts = list(dict.fromkeys(original_texts))
        if debug:
            print(f"[OOXML] collected {len(original_texts)} texts, {len(unique_texts)} unique to translate.")

        # 3. 并行翻译（术语前后处理）
        translations = {}
        if unique_texts:
            db = SessionLocal()
            try:
                options = get_terminology_options(db)
                if options.get("terminology_enabled", True):
                    cat_ids = kwargs.get("category_ids", None)
                    # 规则：若启用分类且未显式选择分类（None）或选择为空数组([])，则不应用术语
                    if options.get("categories_enabled", True):
                        if cat_ids is None or (isinstance(cat_ids, list) and len(cat_ids) == 0):
                            processed_texts, mappings = unique_texts, [{} for _ in unique_texts]
                        else:
                            processed_texts, mappings = preprocess_texts_with_categories(
                                db, unique_texts, src_lang, tgt_lang, cat_ids, case_sensitive=bool(options.get("case_sensitive", False)), user_id=user_id
                            )
                    else:
                        processed_texts, mappings = preprocess_texts(
                            db, unique_texts, src_lang, tgt_lang, case_sensitive=bool(options.get("case_sensitive", False)), user_id=user_id
                        )
                else:
                    processed_texts, mappings = unique_texts, [{} for _ in unique_texts]

                # Qwen3: 避免并发，多条顺序翻译，降低429
                if str(engine).lower() == 'qwen3':
                    translated_unique = []
                    for s in processed_texts:
                        try:
                            from app.services.utils_translator import translate_batch as _tb
                            _r = _tb([s], src_lang, tgt_lang, engine=engine, **kwargs)
                            if isinstance(_r, tuple) and len(_r) >= 1:
                                _r = _r[0]
                            if isinstance(_r, list) and _r:
                                translated_unique.append(str(_r[0]))
                            else:
                                translated_unique.append(s)
                            import time as _t; _t.sleep(0.08)
                        except Exception:
                            translated_unique.append(s)
                else:
                    # 根据系统设置决定是否严格顺序以精确统计 tokens
                    try:
                        from app.database import SessionLocal as _SL
                        _db = _SL();
                        from app import models as _M
                        setting = _db.query(_M.SystemSetting).filter(_M.SystemSetting.key=="docx_collect_tokens", _M.SystemSetting.category=="ooxml").first()
                        collect_tokens = str(getattr(setting, 'value', 'false')).lower() == 'true'
                        _db.close()
                    except Exception:
                        collect_tokens = False
                    if collect_tokens:
                        _r = parallel_translate([""], src_lang, tgt_lang, engine=engine, workers=1, debug=debug, **kwargs)  # no-op to keep flow
                        _res = _tb2(processed_texts, src_lang, tgt_lang, engine=engine, **kwargs)
                        if isinstance(_res, tuple) and len(_res)>=2:
                            translated_unique = _res[0]
                            try:
                                total_token_count += int(_res[1] or 0)
                            except Exception:
                                pass
                    else:
                        # 并行批量翻译，按 workers 拆分（更快，但 tokens 统计可能不精确）
                        translated_unique = parallel_translate(processed_texts, src_lang, tgt_lang, engine=engine, workers=workers, debug=debug, **kwargs)
                # token 统计：并行翻译改为顺序聚合（workers>1 时仍按并行，但无法逐批拿到tokens，这里退化为单批统计）
                try:
                    _res = _tb2(processed_texts, src_lang, tgt_lang, engine=engine, **kwargs)
                    if isinstance(_res, tuple) and len(_res) >= 2:
                        translated_unique = _res[0]
                        _tok = _res[1]
                        total_token_count += int(_tok or 0)
                except Exception:
                    pass

                if options.get("terminology_enabled", True):
                    translated_unique = postprocess_texts(translated_unique, mappings)

                translations = {
                    src: (dst if isinstance(dst, str) and dst.strip() else src)
                    for src, dst in zip(unique_texts, translated_unique)
                }
            finally:
                db.close()

        # 4. 写回
        for part, node in text_nodes:
            old_text = node.text
            new_text = translations.get(old_text, old_text)
            if debug:
                print(f"[DEBUG] {part} | OLD: {old_text!r} -> NEW: {new_text!r}")
            node.text = new_text

        # 5. 保存新 DOCX
        with zipfile.ZipFile(output_path, "w") as zout:
            for item in zin.infolist():
                if item.filename in trees:
                    xml_bytes = BytesIO()
                    trees[item.filename].write(xml_bytes, encoding="utf-8", xml_declaration=True)
                    zout.writestr(item, xml_bytes.getvalue())
                else:
                    zout.writestr(item, zin.read(item.filename))
    
    # 6. 统计：总文本（节点级）与成功翻译数（节点级，译文与原文不同）
    try:
        total_text_nodes = len(original_texts)
        translated_nodes = sum(1 for s in original_texts if translations.get(s, s) != s)
    except Exception:
        total_text_nodes = len(original_texts)
        translated_nodes = 0

    return {
        "token_count": total_token_count,
        "character_count": total_character_count,
        "total_texts": total_text_nodes,
        "translated_texts": translated_nodes,
    }
                    
    # Return metadata
    return {
        "translated_file_path": output_path,
        "token_count": total_token_count,
        "character_count": character_count
    }


if __name__ == "__main__":
    if len(sys.argv) < 5:
        print("Usage: python -m app.services.translator_ooxml_direct <input.docx> <output.docx> <src_lang> <tgt_lang> [engine] [workers]")
        sys.exit(1)

    inp, outp, src, tgt = sys.argv[1:5]
    engine = sys.argv[5] if len(sys.argv) > 5 else "deepseek"
    workers = int(sys.argv[6]) if len(sys.argv) > 6 else 5
    debug = True

    translate_docx_inplace(inp, outp, src, tgt, engine=engine, workers=workers, debug=debug)
