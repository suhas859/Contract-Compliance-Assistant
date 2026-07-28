from langchain_text_splitters import RecursiveCharacterTextSplitter
 
_char_splitter = RecursiveCharacterTextSplitter(
    chunk_size=800,       # 150-200 words clause-sized, not page-sized
    chunk_overlap=100,    # preserves context across a split point
    separators=["\n\n", "\n", ". ", " "],
)
 
 
def chunk_text(text: str) -> list[str]:
    """
    Splits text into chunks, preferring natural boundaries in this
    priority order: paragraph break -> line break -> sentence end ->
    word. Falls back to a plain word-level cut only if a single
    "paragraph" is still longer than chunk_size on its own.
    """
    return _char_splitter.split_text(text)
