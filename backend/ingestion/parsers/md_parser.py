import re

def parse_md(file_path: str) -> str:
    """
    Do NOT strip formatting characters:
    - '#' headers must survive so MarkdownHeaderTextSplitter can chunk by section.
    - '-' must survive because it appears inside contract IDs (CTR-2026-0088),
      tax IDs (94-3021177), and dates (2026-01-15) throughout this corpus.
      Stripping it silently corrupts every one of those identifiers.
    """
    
    with open(file_path, "r", encoding="utf-8") as f:
        return f.read().strip()
