"""
client.py - Resilient client configuration for nba_api.

Integrates curl_cffi with TLS browser impersonation to bypass Akamai bot detection
on stats.nba.com without encountering ConnectionResetError or ReadTimeoutError.
"""

import time
import logging
from typing import Any, Callable, Dict, Optional
from curl_cffi import requests as cr
import nba_api.library.http as nba_http

logger = logging.getLogger(__name__)

DEFAULT_HEADERS: Dict[str, str] = {
    "Host": "stats.nba.com",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.nba.com/",
    "Origin": "https://www.nba.com",
    "x-nba-stats-origin": "stats",
    "x-nba-stats-token": "true",
}

_session: Optional[cr.Session] = None


def get_impersonated_session(impersonate: str = "chrome120") -> cr.Session:
    """Returns a singleton curl_cffi session configured for TLS browser impersonation."""
    global _session
    if _session is None:
        _session = cr.Session(impersonate=impersonate)
        # Update default session headers
        _session.headers.update(DEFAULT_HEADERS)
    return _session


def configure_nba_api_client(impersonate: str = "chrome120", timeout: int = 45) -> None:
    """
    Patches nba_api's internal HTTP module to use curl_cffi session.
    Also injects browser headers and default timeout.
    """
    session = get_impersonated_session(impersonate=impersonate)
    # Monkey-patch requests in nba_api.library.http
    nba_http.requests = session
    logger.info("Configured nba_api with curl_cffi TLS impersonation (%s)", impersonate)


def call_with_retry(
    func: Callable[[], Any],
    max_retries: int = 3,
    initial_delay: float = 1.0,
    backoff_factor: float = 2.0,
    rate_limit_delay: float = 0.6,
) -> Any:
    """
    Executes an nba_api endpoint call with exponential backoff retries and rate limiting.
    """
    delay = initial_delay
    last_exception = None

    for attempt in range(1, max_retries + 1):
        try:
            if rate_limit_delay > 0:
                time.sleep(rate_limit_delay)
            result = func()
            return result
        except Exception as exc:
            last_exception = exc
            exc_str = str(exc).lower()
            # If the response was empty or missing keys, retrying won't change server payload
            is_payload_error = isinstance(exc, KeyError) or "expecting value" in exc_str or "jsondecode" in exc_str or "not found" in exc_str
            if is_payload_error:
                logger.debug("Non-retryable response from NBA stats endpoint: %s", exc)
                raise exc

            logger.warning(
                "Attempt %d/%d failed: %s. Retrying in %.1fs...",
                attempt,
                max_retries,
                exc,
                delay,
            )
            if attempt < max_retries:
                time.sleep(delay)
                delay *= backoff_factor

    raise RuntimeError(
        f"Failed to fetch data from NBA API after {max_retries} attempts."
    ) from last_exception
