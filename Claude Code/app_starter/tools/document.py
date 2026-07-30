from markitdown import MarkItDown, StreamInfo
from io import BytesIO
from pathlib import Path
from pydantic import Field

SUPPORTED_EXTENSIONS = {".docx", ".pdf"}


def binary_document_to_markdown(binary_data: bytes, file_type: str) -> str:
    """Converts binary document data to markdown-formatted text."""
    md = MarkItDown()
    file_obj = BytesIO(binary_data)
    stream_info = StreamInfo(extension=file_type)
    result = md.convert(file_obj, stream_info=stream_info)
    return result.text_content


def document_path_to_markdown(
    path: str = Field(description="Absolute or relative path to a .docx or .pdf file"),
) -> str:
    """Convert a PDF or DOCX file to markdown-formatted text.

    Reads the file at the given path and returns its contents as markdown.

    When to use:
    - When you have a local file path to a document and need its text content
    - When to NOT use: if you already have the binary data, use binary_document_to_markdown instead

    Examples:
    >>> document_path_to_markdown("/tmp/report.pdf")
    "# Report Title\\n\\nContent..."
    """
    if not path:
        raise ValueError("path must not be empty")

    p = Path(path)

    if not p.exists():
        raise FileNotFoundError(f"No such file: {path}")

    if p.is_dir():
        raise IsADirectoryError(f"Path is a directory, not a file: {path}")

    ext = p.suffix.lower()
    if ext not in SUPPORTED_EXTENSIONS:
        raise ValueError(f"Unsupported file type '{ext}'. Supported: {SUPPORTED_EXTENSIONS}")

    with open(p, "rb") as f:
        binary_data = f.read()

    return binary_document_to_markdown(binary_data, ext.lstrip("."))
