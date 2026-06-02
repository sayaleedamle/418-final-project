"""Transcript fetching — thin wrapper around youtube-transcript-api."""

from __future__ import annotations

import re

from youtube_transcript_api import (
    YouTubeTranscriptApi,
    NoTranscriptFound,
    TranscriptsDisabled,
)

_YT_ID_RE = re.compile(r"(?:v=|youtu\.be/|embed/|shorts/)([A-Za-z0-9_-]{11})")
_api = YouTubeTranscriptApi()


class TranscriptFetchError(Exception):
    pass


def extract_video_id(video: str) -> str:
    """Return the 11-char video ID from a URL or bare ID string."""
    m = _YT_ID_RE.search(video)
    return m.group(1) if m else video.strip()


_SENTENCE_ENDINGS = re.compile(r"[.!?]$")
_GAP_THRESHOLD_S = 1.5  # seconds of silence → treat as sentence boundary


def fetch_transcript(video_id: str) -> str:
    """Fetch an English transcript and return it joined as a single string.

    For auto-generated captions (no punctuation), sentence boundaries are
    inferred from timing gaps between segments: a gap ≥ 1.5 s with no
    trailing punctuation causes a period to be appended.
    """
    try:
        tlist = _api.list(video_id)
        try:
            t = tlist.find_manually_created_transcript(["en"])
        except Exception:
            t = tlist.find_generated_transcript(["en"])
        segs = [s for s in t.fetch() if s.text.strip()]
    except (NoTranscriptFound, TranscriptsDisabled) as exc:
        raise TranscriptFetchError(str(exc)) from exc
    except Exception as exc:
        raise TranscriptFetchError(f"Unexpected error fetching transcript: {exc}") from exc

    parts: list[str] = []
    for i, seg in enumerate(segs):
        text = seg.text.strip()
        # Infer sentence boundary from silence gap to next segment
        if i < len(segs) - 1:
            gap = segs[i + 1].start - (seg.start + seg.duration)
            if gap >= _GAP_THRESHOLD_S and not _SENTENCE_ENDINGS.search(text):
                text = text + "."
        parts.append(text)
    return " ".join(parts)
