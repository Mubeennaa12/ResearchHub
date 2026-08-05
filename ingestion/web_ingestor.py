"""
Ingests generic web pages, cleaning boilerplate to retrieve core article text.
"""

import hashlib
import requests
from bs4 import BeautifulSoup
from ingestion.base import BaseIngestor, NormalizedDocument, IngestionError


class WebIngestor(BaseIngestor):
    source_type = "web"

    def can_handle(self, source: str) -> bool:
        return source.startswith("http://") or source.startswith("https://")

    def ingest(self, source: str) -> NormalizedDocument:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        try:
            response = requests.get(source, headers=headers, timeout=20)
            response.raise_for_status()
        except Exception as e:
            raise IngestionError(f"Failed to fetch URL {source}: {e}")

        try:
            soup = BeautifulSoup(response.text, "html.parser")

            # Remove standard boilerplate tags
            for s in soup(["script", "style", "nav", "footer", "header", "noscript"]):
                s.decompose()

            # Extract title
            title_tag = soup.find("title")
            title = title_tag.get_text().strip() if title_tag else source

            # Try to grab meta descriptions/author where possible
            author = ""
            author_meta = soup.find("meta", attrs={"name": "author"}) or soup.find("meta", attrs={"property": "article:author"})
            if author_meta:
                author = author_meta.get("content", "").strip()

            # Extract text content
            text = soup.get_text()
            lines = (line.strip() for line in text.splitlines())
            # break multi-headlines into a line each, gap-clean
            chunks = (phrase for line in lines for phrase in line.split("  "))
            clean_text = "\n".join(chunk for chunk in chunks if chunk)

            source_id = hashlib.md5(source.encode("utf-8")).hexdigest()

            # For web pages, the page is one large section
            sections = [{
                "type": "webpage",
                "id": 1,
                "text": clean_text
            }]

            authors_list = [author] if author else []

            return NormalizedDocument(
                source_id=source_id,
                source_type=self.source_type,
                title=title,
                text=clean_text,
                url=source,
                authors=authors_list,
                metadata={"status_code": response.status_code},
                sections=sections
            )
        except Exception as e:
            raise IngestionError(f"Failed to parse web page {source}: {e}")
