#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
translator_text.py

A simple text file translator for .txt and .md files.
It reads the file, translates content line by line, and writes to a new file.
Now with robust encoding detection.
"""
import os
from typing import List
import chardet

try:
    from app.services.utils_translator import translate_batch
    from app.services.terminology_service import (
        get_terminology_options,
        preprocess_texts,
        postprocess_texts,
    )
    from app.database import SessionLocal
except (ImportError, ModuleNotFoundError):
    from utils_translator import translate_batch

def read_file_with_fallback(path: str) -> List[str]:
    """
    Reads a text file with robust encoding detection.
    Tries UTF-8 first, then falls back to chardet's detection.
    """
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return f.readlines()
    except UnicodeDecodeError:
        print(f"Warning: UTF-8 decoding failed for {path}. Detecting encoding...")
        with open(path, 'rb') as f:
            raw_data = f.read()
        detected_encoding = chardet.detect(raw_data)['encoding']
        if detected_encoding:
            print(f"Detected encoding: {detected_encoding}. Retrying read.")
            return raw_data.decode(detected_encoding, errors='ignore').splitlines(keepends=True)
        else:
            # If chardet fails, fall back to a common encoding with error ignoring
            print("Warning: Encoding detection failed. Falling back to latin-1.")
            return raw_data.decode('latin-1').splitlines(keepends=True)


def translate_text_file(input_path: str, output_path: str, src_lang: str, tgt_lang: str, engine: str = "deepseek", user_id: int | None = None):
    """
    Translates a text-based file (.txt, .md).
    """
    try:
        lines = read_file_with_fallback(input_path)
        
        original_lines = [line.strip() for line in lines]
        translatable_lines = [line for line in original_lines if line]

        if not translatable_lines:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.writelines(lines)
            return {
                "translated_file_path": output_path,
                "token_count": 0,
                "character_count": 0
            }

        translated_lines_map = {}
        total_token_count = 0
        total_character_count = 0
        
        if translatable_lines:
            # 术语前处理
            try:
                db = SessionLocal()
            except Exception:
                db = None
            options = get_terminology_options(db) if db else {"terminology_enabled": True, "case_sensitive": False, "categories_enabled": True}
            if options.get("terminology_enabled", True):
                # 统一规则：启用分类且未选择分类 -> 不应用术语
                cat_ids = None  # 文本直译默认无分类参数
                if options.get("categories_enabled", True) and (not cat_ids or (isinstance(cat_ids, list) and len(cat_ids) == 0)):
                    processed_lines, mappings = translatable_lines, [{} for _ in translatable_lines]
                else:
                    processed_lines, mappings = preprocess_texts(
                        db, translatable_lines, src_lang, tgt_lang,
                        case_sensitive=bool(options.get("case_sensitive", False)), user_id=user_id
                    )
            else:
                processed_lines, mappings = translatable_lines, [{} for _ in translatable_lines]

            translated_processed, batch_token_count = translate_batch(processed_lines, src_lang, tgt_lang, engine=engine)
            total_token_count += batch_token_count
            total_character_count += sum(len(line) for line in translatable_lines)

            # 术语后处理
            if options.get("terminology_enabled", True):
                translated_lines = postprocess_texts(translated_processed, mappings)
            else:
                translated_lines = translated_processed

            translated_lines_map = dict(zip(translatable_lines, translated_lines))
            if db:
                try:
                    db.close()
                except Exception:
                    pass

        output_lines = []
        for line in lines:
            stripped_line = line.strip()
            if stripped_line in translated_lines_map:
                output_lines.append(line.replace(stripped_line, translated_lines_map[stripped_line]))
            else:
                output_lines.append(line)

        with open(output_path, 'w', encoding='utf-8') as f:
            f.writelines(output_lines)

        # 简要统计：总文本行数与有效翻译行数
        try:
            total_texts = len([l for l in original_lines if l])
            translated_texts = sum(1 for l in translatable_lines if translated_lines_map.get(l, l) != l)
        except Exception:
            total_texts = None
            translated_texts = None
        return {
            "translated_file_path": output_path,
            "token_count": total_token_count,
            "character_count": total_character_count,
            "total_texts": total_texts,
            "translated_texts": translated_texts,
        }

    except Exception as e:
        print(f"Error translating text file {input_path}: {e}")
        raise

def translate_text_direct(input_path: str, output_path: str, src_lang: str, tgt_lang: str, engine="deepseek", user_id: int | None = None, **kwargs):
    """
    Direct entry point for text translation.
    """
    result = translate_text_file(input_path, output_path, src_lang, tgt_lang, engine=engine, user_id=user_id)
    return result