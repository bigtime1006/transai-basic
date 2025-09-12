# translator_base.py
from typing import Optional

class TranslateError(Exception):
    """通用翻译错误"""

def translate_doc(input_path: str, output_path: str, src_lang: str = "zh", tgt_lang: str = "en") -> None:
    """
    通用接口说明（由具体策略实现）：
    - input_path: 源 docx 路径
    - output_path: 目标 docx 路径
    - src_lang / tgt_lang: 语言对
    """
    raise NotImplementedError("请在具体策略模块中实现 translate_doc 函数")
