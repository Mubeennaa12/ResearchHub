"""
Extracts text (and page numbers) from PDF files.
"""

import os
import hashlib
from pypdf import PdfReader
from ingestion.base import BaseIngestor, NormalizedDocument, IngestionError


class PDFIngestor(BaseIngestor):
    source_type = "pdf"

    def can_handle(self, source: str) -> bool:
        return source.lower().endswith(".pdf") or (os.path.isfile(source) and source.lower().endswith(".pdf"))

    def ingest(self, source: str) -> NormalizedDocument:
        if not os.path.exists(source):
            raise IngestionError(f"PDF file not found at: {source}")

        try:
            reader = PdfReader(source)
            sections = []
            full_text_list = []
            
            for i, page in enumerate(reader.pages):
                text = page.extract_text() or ""
                page_num = i + 1
                sections.append({
                    "type": "page",
                    "id": page_num,
                    "text": text.strip()
                })
                full_text_list.append(text)

            full_text = "\n\n".join(full_text_list)
            title = os.path.basename(source)
            source_id = hashlib.md5(source.encode("utf-8")).hexdigest()

            return NormalizedDocument(
                source_id=source_id,
                source_type=self.source_type,
                title=title,
                text=full_text,
                url=None,
                metadata={"file_size": os.path.getsize(source)},
                sections=sections
            )
        except Exception as e:
            raise IngestionError(f"Failed to ingest PDF from {source}: {e}")
