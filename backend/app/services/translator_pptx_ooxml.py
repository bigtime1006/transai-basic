import zipfile
from io import BytesIO
from typing import Dict, List, Tuple
from lxml import etree as ET

from app.services.utils_translator import translate_batch
from app.services.terminology_service import (
    get_terminology_options,
    preprocess_texts,
    preprocess_texts_with_categories,
    postprocess_texts,
)
from app.database import SessionLocal


NS = {
    'a': 'http://schemas.openxmlformats.org/drawingml/2006/main',
    'p': 'http://schemas.openxmlformats.org/presentationml/2006/main',
}


def _normalize(s: str) -> str:
    if not isinstance(s, str):
        return s
    s = s.replace('_x000B_', '\n').replace('_x000b_', '\n')
    s = s.replace('_x000D_', '\n').replace('_x000d_', '\n')
    s = s.replace('\x0b', '\n')
    return s


def _collect_slide_text(xml_bytes: bytes) -> Tuple[List[str], ET._ElementTree]:
    if not xml_bytes:
        return [], None
    tree = ET.parse(BytesIO(xml_bytes))
    texts: List[str] = []
    for t in tree.findall('.//a:t', namespaces=NS):
        if t.text is not None:
            val = _normalize(t.text)
            if val.strip():
                texts.append(val)
    return texts, tree


def _apply_slide_text(tree: ET._ElementTree, translations: Dict[str, str]):
    for t in tree.findall('.//a:t', namespaces=NS):
        if t.text and t.text in translations:
            t.text = translations[t.text]


def translate_pptx_ooxml(input_path: str, output_path: str, src_lang: str, tgt_lang: str, engine: str = 'deepseek', user_id: int | None = None, category_ids=None, **kwargs):
    with zipfile.ZipFile(input_path, 'r') as zin:
        names = zin.namelist()
        slide_names = [n for n in names if n.startswith('ppt/slides/slide') and n.endswith('.xml')]
        notes_names = [n for n in names if n.startswith('ppt/notesSlides/notesSlide') and n.endswith('.xml')]

        trees: Dict[str, ET._ElementTree] = {}
        all_texts: List[str] = []

        for n in slide_names + notes_names:
            texts, tree = _collect_slide_text(zin.read(n))
            if tree is not None:
                trees[n] = tree
            all_texts.extend(texts)

        unique = list(dict.fromkeys([t for t in all_texts if isinstance(t, str) and t.strip()]))

        translations: Dict[str, str] = {}
        if unique:
            db = SessionLocal()
            try:
                options = get_terminology_options(db)
                case_sensitive = bool(options.get('case_sensitive', False))
                if options.get('terminology_enabled', True):
                    if category_ids:
                        processed, mappings = preprocess_texts_with_categories(db, unique, src_lang, tgt_lang, category_ids, case_sensitive=case_sensitive, user_id=user_id)
                    else:
                        processed, mappings = preprocess_texts(db, unique, src_lang, tgt_lang, case_sensitive=case_sensitive, user_id=user_id)
                else:
                    processed, mappings = unique, [{} for _ in unique]

                translated, _tok = translate_batch(processed, src_lang, tgt_lang, engine=engine, **kwargs)
                try:
                    total_token_count = int(_tok or 0)
                except Exception:
                    total_token_count = 0
                if options.get('terminology_enabled', True):
                    translated = postprocess_texts(translated, mappings)
                for s, d in zip(unique, translated):
                    safe = d if isinstance(d, str) and d.strip() else s
                    translations[s] = _normalize(safe)
            finally:
                try:
                    db.close()
                except Exception:
                    pass

        for n, tree in trees.items():
            _apply_slide_text(tree, translations)

        with zipfile.ZipFile(output_path, 'w') as zout:
            for info in zin.infolist():
                name = info.filename
                if name in trees:
                    bio = BytesIO()
                    trees[name].write(bio, encoding='utf-8', xml_declaration=True)
                    zout.writestr(info, bio.getvalue())
                else:
                    zout.writestr(info, zin.read(name))

    # 统计字符数（粗略）
    total_chars = 0
    try:
        total_chars = sum(len(t) for t in unique)
    except Exception:
        total_chars = 0
    # 简要统计：文本条目数量（去重后作为估计）
    try:
        total_texts = len(unique)
    except Exception:
        total_texts = None
    return {
        'translated_file_path': output_path,
        'token_count': total_token_count,
        'character_count': total_chars,
        'total_texts': total_texts,
    }


