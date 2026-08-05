"""
Pulls transcript timelines for YouTube video URLs using youtube-transcript-api.
"""

import re
import hashlib
from youtube_transcript_api import YouTubeTranscriptApi
from ingestion.base import BaseIngestor, NormalizedDocument, IngestionError


class YouTubeIngestor(BaseIngestor):
    source_type = "youtube"

    def can_handle(self, source: str) -> bool:
        return "youtube.com" in source.lower() or "youtu.be" in source.lower()

    def _extract_video_id(self, url: str) -> str:
        """
        Extracts the 11-character video ID from a YouTube link.
        """
        patterns = [
            r"(?:v=|\/embed\/|\/v\/|youtu\.be\/|\/watch\?v=|\/watch\?.+&v=)([^#\&\?]{11})",
            r"youtube\.com\/shorts\/([^#\&\?]{11})"
        ]
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        raise ValueError(f"Could not extract video ID from URL: {url}")

    def ingest(self, source: str) -> NormalizedDocument:
        try:
            video_id = self._extract_video_id(source)
        except Exception as e:
            raise IngestionError(str(e))

        try:
            # Fetch transcript list
            transcript_list = YouTubeTranscriptApi.get_transcript(video_id, languages=["en", "en-US"])
        except Exception as e:
            raise IngestionError(f"Failed to fetch transcript for video ID {video_id}: {e}")

        # Segment transcript list into ~45-second windows
        sections = []
        current_text_segments = []
        current_start = 0.0
        segment_duration_limit = 45.0

        for item in transcript_list:
            text = item.get("text", "").strip()
            start = item.get("start", 0.0)
            
            if not current_text_segments:
                current_start = start
            
            current_text_segments.append(text)
            
            # If current item's end time exceeds limit threshold from segment start, finalize section
            if start - current_start >= segment_duration_limit:
                sections.append({
                    "type": "transcript",
                    "start_seconds": round(current_start, 1),
                    "text": " ".join(current_text_segments)
                })
                current_text_segments = []

        # Catch remaining segments
        if current_text_segments:
            sections.append({
                "type": "transcript",
                "start_seconds": round(current_start, 1),
                "text": " ".join(current_text_segments)
            })

        # Rebuild full transcript text
        full_text = "\n".join([f"[{sec['start_seconds']}s]: {sec['text']}" for sec in sections])
        title = f"YouTube Video: {video_id}"
        source_id = hashlib.md5(source.encode("utf-8")).hexdigest()

        return NormalizedDocument(
            source_id=source_id,
            source_type=self.source_type,
            title=title,
            text=full_text,
            url=source,
            metadata={"video_id": video_id},
            sections=sections
        )
