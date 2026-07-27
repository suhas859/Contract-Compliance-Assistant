import re

def parse_md(file_path: str) -> str:
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    cleaned = re.sub(r"[#>*`~\-]", "", content)
    cleaned = re.sub(r"\n{2,}", "\n", cleaned)

    return cleaned.strip()
