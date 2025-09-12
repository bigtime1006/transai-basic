import os
from .translator_ooxml_direct import translate_docx_inplace
from .translator_xlsx_direct import translate_xlsx_direct
from .translator_pptx_direct import translate_pptx_direct
from .translator_text import translate_text_direct

def run(input_path, output_path, strategy="ooxml_direct", src_lang="auto", tgt_lang="ja", engine="deepseek"):
    """
    The main entry point for translation, routing to the correct translator
    based on file type and selected strategy.
    """
    file_extension = os.path.splitext(input_path)[1].lower()

    # Route .txt and .md files to the text translator, regardless of strategy
    if file_extension in [".txt", ".md"]:
        return translate_text_direct(input_path, output_path, src_lang=src_lang, tgt_lang=tgt_lang, engine=engine)

    # Route based on strategy for other file types
    if strategy == "ooxml_direct":
        if file_extension == ".docx":
            return translate_docx_inplace(input_path, output_path, src_lang=src_lang, tgt_lang=tgt_lang, engine=engine)
        elif file_extension == ".xlsx":
            return translate_xlsx_direct(input_path, output_path, src_lang=src_lang, tgt_lang=tgt_lang, engine=engine)
        elif file_extension == ".pptx":
            return translate_pptx_direct(input_path, output_path, src_lang=src_lang, tgt_lang=tgt_lang, engine=engine)
        else:
            raise ValueError(f"Unsupported file type '{file_extension}' for the 'ooxml_direct' strategy.")

    elif strategy == "text_direct":
        # 明确支持text_direct策略
        if file_extension in [".txt", ".md"]:
            return translate_text_direct(input_path, output_path, src_lang=src_lang, tgt_lang=tgt_lang, engine=engine)
        else:
            raise ValueError(f"File type '{file_extension}' is not supported for 'text_direct' strategy. Only .txt and .md files are supported.")

    elif strategy == "html":
        raise NotImplementedError("The 'HTML' strategy is not yet implemented.")

    elif strategy == "aspose":
        raise NotImplementedError("The 'Aspose API' strategy is not yet implemented.")

    else:
        raise ValueError(f"Unknown or unsupported strategy: {strategy}")
