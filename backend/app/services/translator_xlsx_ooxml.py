import zipfile
from io import BytesIO
from typing import List, Tuple, Dict
from lxml import etree as ET

from app.services.utils_translator import translate_batch
from app.services.terminology_service import (
    get_terminology_options,
    preprocess_texts,
    preprocess_texts_with_categories,
    postprocess_texts,
)
from app.database import SessionLocal


NS_SS = {
    'a': 'http://schemas.openxmlformats.org/drawingml/2006/main',
}


def _collect_shared_strings(xml_bytes: bytes) -> Tuple[List[str], List[Tuple[str, int]], ET._ElementTree]:
    if not xml_bytes:
        return [], [], None
    tree = ET.parse(BytesIO(xml_bytes))
    root = tree.getroot()
    texts: List[str] = []
    positions: List[Tuple[str, int]] = []  # (type, index) si index
    si_elems = root.findall('.//{*}si')
    for i, si in enumerate(si_elems):
        # direct <t>
        t = si.find('.//{*}t')
        if t is not None and t.text:
            texts.append(t.text)
            positions.append(('si', i))
        else:
            # rich text runs <r><t>
            runs = si.findall('.//{*}r/{*}t')
            if runs:
                # 合并成一个字符串供翻译
                s = ''.join([r.text or '' for r in runs])
                if s:
                    texts.append(s)
                    positions.append(('si_r', i))
    return texts, positions, tree


def _apply_shared_strings(tree: ET._ElementTree, translations: Dict[Tuple[str, str], str]):
    if tree is None:
        return
    root = tree.getroot()
    for si in root.findall('.//{*}si'):
        t = si.find('.//{*}t')
        if t is not None and t.text:
            key = (t.text, 't')
            if key in translations:
                t.text = translations[key]
        else:
            runs = si.findall('.//{*}r/{*}t')
            if runs:
                original = ''.join([r.text or '' for r in runs])
                key = (original, 'r')
                if key in translations:
                    new_text = translations[key]
                    # 简化：把第一 run 填完整，其余置空
                    if runs:
                        runs[0].text = new_text
                        for r in runs[1:]:
                            r.text = ''


def _collect_sheet_inline(xml_bytes: bytes) -> Tuple[List[str], List[ET._ElementTree]]:
    if not xml_bytes:
        return [], []
    tree = ET.parse(BytesIO(xml_bytes))
    texts: List[str] = []
    # inline strings <is><t> and rich <is><r><t>
    for t in tree.findall('.//{*}is/{*}t'):
        if t.text:
            texts.append(t.text)
    for r in tree.findall('.//{*}is/{*}r/{*}t'):
        if r.text:
            texts.append(r.text)
    return texts, [tree]


def _apply_sheet_inline(tree: ET._ElementTree, translations: Dict[str, str]):
    # replace <is><t> and <is><r><t>
    for t in tree.findall('.//{*}is/{*}t'):
        if t.text and t.text in translations:
            t.text = translations[t.text]
    for r in tree.findall('.//{*}is/{*}r/{*}t'):
        if r.text and r.text in translations:
            r.text = translations[r.text]


def _collect_drawing_text(xml_bytes: bytes) -> Tuple[List[str], ET._ElementTree]:
    if not xml_bytes:
        return [], None
    tree = ET.parse(BytesIO(xml_bytes))
    texts: List[str] = []
    for t in tree.findall('.//a:t', namespaces=NS_SS):
        if t.text:
            texts.append(t.text)
    return texts, tree


def _apply_drawing_text(tree: ET._ElementTree, translations: Dict[str, str]):
    if tree is None:
        return
    for t in tree.findall('.//a:t', namespaces=NS_SS):
        if t.text and t.text in translations:
            t.text = translations[t.text]


def _collect_comments(xml_bytes: bytes) -> Tuple[List[str], ET._ElementTree]:
    """Collect texts from xl/comments*.xml (commentList/comment/r/t)."""
    if not xml_bytes:
        return [], None
    tree = ET.parse(BytesIO(xml_bytes))
    texts: List[str] = []
    # comments/commentList/comment
    for c in tree.findall('.//{*}comment'):
        # rich runs under comment//r/t
        runs = c.findall('.//{*}r/{*}t')
        if runs:
            s = ''.join([r.text or '' for r in runs])
            if s:
                texts.append(s)
        else:
            t = c.find('.//{*}t')
            if t is not None and t.text:
                texts.append(t.text)
    return texts, tree


def _apply_comments(tree: ET._ElementTree, translations: Dict[str, str]):
    if tree is None:
        return
    for c in tree.findall('.//{*}comment'):
        runs = c.findall('.//{*}r/{*}t')
        if runs:
            original = ''.join([r.text or '' for r in runs])
            if original in translations:
                new_text = translations[original]
                runs[0].text = new_text
                for r in runs[1:]:
                    r.text = ''
        else:
            t = c.find('.//{*}t')
            if t is not None and t.text and t.text in translations:
                t.text = translations[t.text]


def _collect_chart_texts(xml_bytes: bytes) -> Tuple[List[str], ET._ElementTree]:
    """Collect visible texts in charts (titles, labels) based on a:t under drawingML in charts."""
    if not xml_bytes:
        return [], None
    tree = ET.parse(BytesIO(xml_bytes))
    texts: List[str] = []
    for t in tree.findall('.//a:t', namespaces=NS_SS):
        if t.text:
            texts.append(t.text)
    return texts, tree


def _apply_chart_texts(tree: ET._ElementTree, translations: Dict[str, str]):
    if tree is None:
        return
    for t in tree.findall('.//a:t', namespaces=NS_SS):
        if t.text and t.text in translations:
            t.text = translations[t.text]

def translate_xlsx_ooxml(input_path: str, output_path: str, src_lang: str, tgt_lang: str, engine: str = 'deepseek', user_id: int | None = None, category_ids=None):
    # 读取 zip
    with zipfile.ZipFile(input_path, 'r') as zin:
        namelist = zin.namelist()
        shared_xml_name = 'xl/sharedStrings.xml'
        shared_bytes = zin.read(shared_xml_name) if shared_xml_name in namelist else b''
        shared_texts, shared_positions, shared_tree = _collect_shared_strings(shared_bytes)

        sheet_names = [n for n in namelist if n.startswith('xl/worksheets/sheet') and n.endswith('.xml')]
        sheet_trees: Dict[str, ET._ElementTree] = {}
        sheet_texts_all: List[str] = []
        for sname in sheet_names:
            texts, trees = _collect_sheet_inline(zin.read(sname))
            sheet_texts_all.extend(texts)
            if trees:
                sheet_trees[sname] = trees[0]

        drawing_names = [n for n in namelist if n.startswith('xl/drawings/') and n.endswith('.xml')]
        drawing_trees: Dict[str, ET._ElementTree] = {}
        drawing_texts_all: List[str] = []
        for dname in drawing_names:
            texts, tree = _collect_drawing_text(zin.read(dname))
            drawing_texts_all.extend(texts)
            if tree is not None:
                drawing_trees[dname] = tree

        # comments
        comment_names = [n for n in namelist if n.startswith('xl/comments') and n.endswith('.xml')]
        comment_trees: Dict[str, ET._ElementTree] = {}
        comment_texts_all: List[str] = []
        for cname in comment_names:
            texts, tree = _collect_comments(zin.read(cname))
            comment_texts_all.extend(texts)
            if tree is not None:
                comment_trees[cname] = tree

        # charts
        chart_names = [n for n in namelist if n.startswith('xl/charts/') and n.endswith('.xml')]
        chart_trees: Dict[str, ET._ElementTree] = {}
        chart_texts_all: List[str] = []
        for chname in chart_names:
            texts, tree = _collect_chart_texts(zin.read(chname))
            chart_texts_all.extend(texts)
            if tree is not None:
                chart_trees[chname] = tree

        # 汇总所有文本去重
        all_texts = []
        for arr in (shared_texts, sheet_texts_all, drawing_texts_all, comment_texts_all, chart_texts_all):
            all_texts.extend(arr)
        unique_texts = list(dict.fromkeys([t for t in all_texts if isinstance(t, str) and t.strip()]))

        translations_map_str: Dict[str, str] = {}
        translations_map_shared: Dict[Tuple[str, str], str] = {}
        if unique_texts:
            db = SessionLocal()
            try:
                options = get_terminology_options(db)
                case_sensitive = bool(options.get('case_sensitive', False))
                if options.get('terminology_enabled', True):
                    if category_ids:
                        processed, mappings = preprocess_texts_with_categories(db, unique_texts, src_lang, tgt_lang, category_ids, case_sensitive=case_sensitive, user_id=user_id)
                    else:
                        processed, mappings = preprocess_texts(db, unique_texts, src_lang, tgt_lang, case_sensitive=case_sensitive, user_id=user_id)
                else:
                    processed, mappings = unique_texts, [{} for _ in unique_texts]

                # 翻译
                translated, _tokens = translate_batch(processed, src_lang, tgt_lang, engine=engine)
                try:
                    total_token_count += int(_tokens or 0)
                except Exception:
                    pass
                
                # 语言后验校验：若输出语言与目标语言不符，则对不合格条目进行二次强制翻译
                def _lang_label(code: str) -> str:
                    return {'zh': 'Chinese', 'ja': 'Japanese', 'ko': 'Korean'}.get(code, code)
                
                def _detect_lang_code(s: str) -> str:
                    if not isinstance(s, str) or not s:
                        return ''
                    total = len(s)
                    if total == 0:
                        return ''
                    # 统计主要文字块占比
                    han = sum(1 for ch in s if '\u4e00' <= ch <= '\u9fff')
                    hira = sum(1 for ch in s if '\u3040' <= ch <= '\u309f')
                    kata = sum(1 for ch in s if '\u30a0' <= ch <= '\u30ff')
                    hangul = sum(1 for ch in s if '\uac00' <= ch <= '\ud7af')
                    jp = hira + kata
                    # 粗略判断
                    if hangul / max(total, 1) > 0.2:
                        return 'ko'
                    if jp / max(total, 1) > 0.2:
                        return 'ja'
                    if han / max(total, 1) > 0.2:
                        return 'zh'
                    return ''
                
                need_fix_indexes = [i for i, txt in enumerate(translated) if _detect_lang_code(txt) not in ('', tgt_lang)]
                if need_fix_indexes:
                    strong_msg = f"Translate strictly into {_lang_label(tgt_lang)} (language code {tgt_lang}). Do NOT output any other language."
                    subset = [processed[i] for i in need_fix_indexes]
                    fixed, _ = translate_batch(subset, src_lang, tgt_lang, engine=engine, style_instruction=strong_msg)
                    for idx, val in zip(need_fix_indexes, fixed):
                        translated[idx] = val
                if options.get('terminology_enabled', True):
                    translated = postprocess_texts(translated, mappings)

                for src, dst in zip(unique_texts, translated):
                    # 保底：空串或None回退原文，避免清空
                    safe = dst if isinstance(dst, str) and dst.strip() else src
                    translations_map_str[src] = safe
                    # sharedStrings 需要区分 t/r，简单地同时登记两个 key 供匹配
                    translations_map_shared[(src, 't')] = safe
                    translations_map_shared[(src, 'r')] = safe
            finally:
                try:
                    db.close()
                except Exception:
                    pass

        # 应用替换
        if shared_tree is not None:
            _apply_shared_strings(shared_tree, translations_map_shared)
        for sname, tree in sheet_trees.items():
            _apply_sheet_inline(tree, translations_map_str)
        for dname, tree in drawing_trees.items():
            _apply_drawing_text(tree, translations_map_str)
        for cname, tree in comment_trees.items():
            _apply_comments(tree, translations_map_str)
        for chname, tree in chart_trees.items():
            _apply_chart_texts(tree, translations_map_str)

        # 写出新的 xlsx
        with zipfile.ZipFile(output_path, 'w') as zout:
            for item in zin.infolist():
                name = item.filename
                if name == shared_xml_name and shared_tree is not None:
                    bio = BytesIO()
                    shared_tree.write(bio, encoding='utf-8', xml_declaration=True)
                    zout.writestr(item, bio.getvalue())
                elif name in sheet_trees:
                    bio = BytesIO()
                    sheet_trees[name].write(bio, encoding='utf-8', xml_declaration=True)
                    zout.writestr(item, bio.getvalue())
                elif name in drawing_trees:
                    bio = BytesIO()
                    drawing_trees[name].write(bio, encoding='utf-8', xml_declaration=True)
                    zout.writestr(item, bio.getvalue())
                elif name in comment_trees:
                    bio = BytesIO()
                    comment_trees[name].write(bio, encoding='utf-8', xml_declaration=True)
                    zout.writestr(item, bio.getvalue())
                elif name in chart_trees:
                    bio = BytesIO()
                    chart_trees[name].write(bio, encoding='utf-8', xml_declaration=True)
                    zout.writestr(item, bio.getvalue())
                else:
                    zout.writestr(item, zin.read(name))

    # 返回简要元数据（可扩展 tokens 统计）
    total_chars = 0
    try:
        # 粗略按去重前的文本集合估算字符数
        all_texts_len = sum(len(t) for t in shared_texts) + sum(len(t) for t in sheet_texts_all) + sum(len(t) for t in drawing_texts_all)
        total_chars = int(all_texts_len)
    except Exception:
        total_chars = 0
    # 粗略统计：文本条目数量（去重后作为估计）
    try:
        total_texts = len(unique_texts)
    except Exception:
        total_texts = None
    return {
        'translated_file_path': output_path,
        'token_count': total_token_count,
        'character_count': total_chars,
        'total_texts': total_texts,
    }


