"""
Splits a NormalizedDocument into semantically coherent chunks, preserving metadata and code syntax boundaries.
"""

import hashlib
import tiktoken
from typing import Any
from dataclasses import dataclass, field
from ingestion.base import NormalizedDocument

# Initialize tokenizer once
try:
    tokenizer = tiktoken.get_encoding("cl100k_base")
except Exception:
    tokenizer = None


@dataclass
class Chunk:
    chunk_id: str
    document_id: str
    text: str
    source_type: str
    metadata: dict[str, Any] = field(default_factory=dict)


def _split_text_by_tokens(text: str, chunk_size: int, overlap: int) -> list[str]:
    """Splits text into chunks based on token count using tiktoken."""
    if not text:
        return []
        
    if not tokenizer:
        # Fallback to character-based splitting if tiktoken is not loaded (1 token ~ 4 chars)
        char_size = chunk_size * 4
        char_overlap = overlap * 4
        chunks = []
        start = 0
        while start < len(text):
            end = start + char_size
            chunks.append(text[start:end])
            start += (char_size - char_overlap)
        return chunks

    tokens = tokenizer.encode(text)
    chunks = []
    
    start_idx = 0
    total_tokens = len(tokens)
    
    while start_idx < total_tokens:
        end_idx = min(start_idx + chunk_size, total_tokens)
        chunk_tokens = tokens[start_idx:end_idx]
        chunks.append(tokenizer.decode(chunk_tokens))
        
        if end_idx == total_tokens:
            break
        start_idx += (chunk_size - overlap)
        
    return chunks


def _chunk_code_file(section: dict[str, Any], chunk_size: int) -> list[str]:
    """
    Groups code lines, attempting to preserve functions and classes together.
    """
    text = section.get("text", "")
    path = section.get("path", "")
    ast_data = section.get("ast", {})
    
    # If file is small enough, return it as a single chunk
    if len(text) < chunk_size * 4:
        return [text]

    # Split code by lines and group them logically
    lines = text.splitlines()
    chunks = []
    current_chunk = []
    current_length = 0
    max_char_len = chunk_size * 4  # Proxy: 1 token = 4 characters

    for line in lines:
        current_chunk.append(line)
        current_length += len(line) + 1
        
        # Split when size limit reached
        if current_length >= max_char_len:
            chunks.append("\n".join(current_chunk))
            # Keep a small line overlap
            current_chunk = current_chunk[-3:] if len(current_chunk) > 3 else []
            current_length = sum(len(l) + 1 for l in current_chunk)

    if current_chunk:
        chunks.append("\n".join(current_chunk))

    return chunks


def chunk_document(doc: NormalizedDocument, chunk_size: int = 800, overlap: int = 100) -> list[Chunk]:
    """
    Chunks a NormalizedDocument.
    Splits section-by-section (e.g., page-by-page, transcript block, code file)
    to maintain contextual boundaries.
    """
    chunks = []

    # If no structured sections are present, chunk the main text block
    sections = doc.sections if doc.sections else [{"type": "prose", "id": 1, "text": doc.text}]

    for idx, sec in enumerate(sections):
        sec_type = sec.get("type", "prose")
        sec_text = sec.get("text", "")
        
        if not sec_text.strip():
            continue

        sec_chunks = []
        if doc.source_type == "github" or sec_type == "code":
            # Code-specific chunking
            sec_chunks = _chunk_code_file(sec, chunk_size)
        else:
            # Prose token-aware chunking
            sec_chunks = _split_text_by_tokens(sec_text, chunk_size, overlap)

        for chunk_idx, text_chunk in enumerate(sec_chunks):
            # Generate unique chunk ID based on document, section index, and chunk index
            chunk_hash_input = f"{doc.source_id}_{idx}_{chunk_idx}_{text_chunk[:20]}"
            chunk_id = hashlib.md5(chunk_hash_input.encode("utf-8")).hexdigest()

            # Compile chunk metadata
            chunk_metadata = {
                "source_id": doc.source_id,
                "source_type": doc.source_type,
                "title": doc.title,
                "url": doc.url,
                "section_type": sec_type,
                "section_id": sec.get("id") or sec.get("path") or idx
            }
            
            # Carry over custom attributes (like channel, published, line range, etc.)
            if "page" in sec:
                chunk_metadata["page"] = sec["page"]
            if "start_seconds" in sec:
                chunk_metadata["start_seconds"] = sec["start_seconds"]
            if "path" in sec:
                chunk_metadata["file_path"] = sec["path"]
                
            # Embed AST definitions if available in code chunks
            if "ast" in sec:
                chunk_metadata["ast_classes"] = sec["ast"].get("classes", [])
                chunk_metadata["ast_functions"] = sec["ast"].get("functions", [])
                chunk_metadata["ast_imports"] = sec["ast"].get("imports", [])

            chunks.append(Chunk(
                chunk_id=chunk_id,
                document_id=doc.source_id,
                text=text_chunk,
                source_type=doc.source_type,
                metadata=chunk_metadata
            ))

    return chunks
