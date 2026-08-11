from backend.llm.llm_provider import LLMProvider

PROMPT_TEMPLATE = """Summarize the message below as a short, descriptive title for a \
chat sidebar entry -- 3 to 6 words, title case, no ending punctuation, no quotes.

MESSAGE:
{message}

TITLE:"""


def generate_title(llm: LLMProvider, message: str) -> str | None:
    """
    Generates a short descriptive title for a new session from its
    first real text message, instead of just truncating that message
    verbatim. Returns None on any failure -- callers fall back to the
    existing truncation-based title in that case, so a slow/broken LLM
    never blocks the chat itself.
    """
    try:
        title = llm.generate(PROMPT_TEMPLATE.format(message=message[:500])).strip()
        title = title.strip('"').strip("'").strip()
        return title[:60] or None
    except Exception:
        return None
