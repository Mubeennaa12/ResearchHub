"""
Implements the Web Search retriever branch.
Checks if a web search key (e.g., Tavily) is present; otherwise falls back to a free DuckDuckGo search.
"""

import logging
import requests
from bs4 import BeautifulSoup
from config import settings
from ingestion.web_ingestor import WebIngestor

logger = logging.getLogger(__name__)


class WebSearchAgent:
    def __init__(self, api_key: str = "", top_k: int = 5):
        self.api_key = api_key or settings.web_search_api_key
        self.top_k = top_k or settings.top_k_web
        self.ingestor = WebIngestor()

    def search(self, query: str) -> list[dict]:
        """
        Executes a web search, using Tavily API if configured, otherwise falling back
        to DuckDuckGo HTML search. Returns normalized list of {title, url, snippet}.
        """
        if self.api_key:
            try:
                logger.info(f"Running Tavily web search for query: '{query}'")
                url = "https://api.tavily.com/search"
                payload = {
                    "api_key": self.api_key,
                    "query": query,
                    "max_results": self.top_k,
                    "search_depth": "basic"
                }
                response = requests.post(url, json=payload, timeout=15)
                response.raise_for_status()
                data = response.json()
                results = []
                for result in data.get("results", []):
                    results.append({
                        "title": result.get("title", ""),
                        "url": result.get("url", ""),
                        "snippet": result.get("content", "")
                    })
                return results
            except Exception as e:
                logger.error(f"Tavily web search failed: {e}. Falling back to DuckDuckGo.")

        # Keyless DuckDuckGo scraper fallback
        try:
            logger.info(f"Running free DuckDuckGo web search for query: '{query}'")
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            }
            url = f"https://html.duckduckgo.com/html/?q={requests.utils.quote(query)}"
            response = requests.get(url, headers=headers, timeout=15)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, "html.parser")
            results = []
            
            # DuckDuckGo HTML results are typically structured with 'result__body' divs
            result_bodies = soup.find_all("div", class_="result__body")
            
            for body in result_bodies[:self.top_k]:
                title_elem = body.find("a", class_="result__a")
                snippet_elem = body.find("a", class_="result__snippet")
                
                if title_elem and snippet_elem:
                    results.append({
                        "title": title_elem.get_text().strip(),
                        "url": title_elem.get("href", ""),
                        "snippet": snippet_elem.get_text().strip()
                    })
            return results
        except Exception as e:
            logger.error(f"DuckDuckGo web search fallback failed: {e}")
            return []
