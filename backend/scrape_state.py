"""Scraping sirasinda /api/scrape/status icin thread-safe ilerleme metni."""
import threading
from typing import Any, Dict

_lock = threading.Lock()
_progress: Dict[str, Any] = {
    "phase": "",
    "message": "",
    "articles_processed": 0,
    "current_source": "",
}


def reset_progress() -> None:
    with _lock:
        _progress["phase"] = ""
        _progress["message"] = ""
        _progress["articles_processed"] = 0
        _progress["current_source"] = ""


def set_progress(
    *,
    phase: str = None,
    message: str = None,
    current_source: str = None,
    articles_delta: int = 0,
) -> None:
    with _lock:
        if phase is not None:
            _progress["phase"] = phase
        if message is not None:
            _progress["message"] = message
        if current_source is not None:
            _progress["current_source"] = current_source
        if articles_delta:
            _progress["articles_processed"] = int(_progress["articles_processed"]) + articles_delta


def get_progress() -> Dict[str, Any]:
    with _lock:
        return dict(_progress)
