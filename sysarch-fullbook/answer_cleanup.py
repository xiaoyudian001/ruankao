import re


def strip_think(text: str) -> str:
    return re.sub(r'<think\b[^>]*>.*?(?:</think\s*>|$)', '', text,
                  flags=re.IGNORECASE | re.DOTALL).strip()


def clean_answer(text: str) -> str:
    text = strip_think(text)
    text = re.sub(r'<!--\s*formula-not-decoded\s*-->', '[公式未完整识别]', text, flags=re.I)
    text = re.sub(r'\[\s*公式占位\s*\]', '[公式未完整识别]', text)
    return re.sub(r'\bformula-not-decoded\b', '公式未完整识别', text, flags=re.I)
