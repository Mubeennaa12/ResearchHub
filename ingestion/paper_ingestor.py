"""
Ingests academic research papers (e.g. arXiv), fetching metadata from the arXiv API and downloading/parsing the paper PDF.
"""

import re
import os
import shutil
import tempfile
import hashlib
import requests
from bs4 import BeautifulSoup
from ingestion.base import BaseIngestor, NormalizedDocument, IngestionError
from ingestion.pdf_ingestor import PDFIngestor


class PaperIngestor(BaseIngestor):
    source_type = "paper"

    def __init__(self):
        self.pdf_ingestor = PDFIngestor()

    def can_handle(self, source: str) -> bool:
        return "arxiv.org" in source.lower()

    def _extract_arxiv_id(self, url: str) -> str:
        """Extracts the arXiv ID (e.g. '2103.00020' or 'hep-th/0201111') from the URL."""
        match = re.search(r"arxiv\.org/(?:abs|pdf)/([a-zA-Z\-]+(?:\.[a-zA-Z\-]+)?/\d{7}|\d{4}\.\d{4,5})", url)
        if not match:
            raise ValueError(f"Could not extract arXiv ID from URL: {url}")
        return match.group(1)

    def ingest(self, source: str) -> NormalizedDocument:
        try:
            arxiv_id = self._extract_arxiv_id(source)
        except Exception as e:
            raise IngestionError(str(e))

        # Query arXiv API for metadata
        metadata_url = f"http://export.arxiv.org/api/query?id_list={arxiv_id}"
        try:
            response = requests.get(metadata_url, timeout=15)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "xml")
            
            entry = soup.find("entry")
            if not entry or entry.find("title") is None:
                raise ValueError("Entry not found in arXiv response")

            title = entry.find("title").get_text().strip().replace("\n", " ")
            abstract = entry.find("summary").get_text().strip()
            published_str = entry.find("published").get_text().strip()
            
            authors = [author.find("name").get_text().strip() for author in entry.find_all("author")]
        except Exception as e:
            raise IngestionError(f"Failed to fetch metadata from arXiv API: {e}")

        # Download paper PDF
        pdf_url = f"https://arxiv.org/pdf/{arxiv_id}.pdf"
        temp_dir = tempfile.mkdtemp(prefix="arxiv_pdf_")
        temp_pdf_path = os.path.join(temp_dir, f"{arxiv_id}.pdf")
        
        try:
            pdf_response = requests.get(pdf_url, stream=True, timeout=30)
            pdf_response.raise_for_status()
            with open(temp_pdf_path, "wb") as f:
                shutil.copyfileobj(pdf_response.raw, f)
        except Exception as e:
            shutil.rmtree(temp_dir, ignore_errors=True)
            raise IngestionError(f"Failed to download PDF from {pdf_url}: {e}")

        # Parse downloaded PDF using PDFIngestor
        try:
            pdf_doc = self.pdf_ingestor.ingest(temp_pdf_path)
        except Exception as e:
            raise IngestionError(f"Failed to parse paper PDF: {e}")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

        source_id = hashlib.md5(source.encode("utf-8")).hexdigest()

        # Combine abstract with page-by-page sections
        paper_sections = [{
            "type": "abstract",
            "id": 0,
            "text": abstract
        }] + pdf_doc.sections

        full_text = f"Title: {title}\nAuthors: {', '.join(authors)}\nAbstract:\n{abstract}\n\nFull Content:\n{pdf_doc.text}"

        return NormalizedDocument(
            source_id=source_id,
            source_type=self.source_type,
            title=title,
            text=full_text,
            url=source,
            authors=authors,
            metadata={
                "arxiv_id": arxiv_id,
                "published_at": published_str,
                "abstract": abstract
            },
            sections=paper_sections
        )
