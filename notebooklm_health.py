"""
NotebookLM health check utility for the Legal Research project.
Verifies that NotebookLM endpoints are reachable and responding within acceptable latency.
"""

import sys
import time
import urllib.request
import urllib.error
from dataclasses import dataclass
from typing import Optional


NOTEBOOKLM_URL = "https://notebooklm.google.com"
TIMEOUT_SECONDS = 10
MAX_ACCEPTABLE_LATENCY_MS = 3000


@dataclass
class HealthResult:
    url: str
    reachable: bool
    status_code: Optional[int]
    latency_ms: Optional[float]
    error: Optional[str]

    @property
    def healthy(self) -> bool:
        return (
            self.reachable
            and self.status_code is not None
            and self.status_code < 500
            and self.latency_ms is not None
            and self.latency_ms <= MAX_ACCEPTABLE_LATENCY_MS
        )


def check_endpoint(url: str, timeout: int = TIMEOUT_SECONDS) -> HealthResult:
    start = time.monotonic()
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "LegalResearch-HealthCheck/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as response:
            latency_ms = (time.monotonic() - start) * 1000
            return HealthResult(
                url=url,
                reachable=True,
                status_code=response.status,
                latency_ms=round(latency_ms, 1),
                error=None,
            )
    except urllib.error.HTTPError as e:
        latency_ms = (time.monotonic() - start) * 1000
        return HealthResult(
            url=url,
            reachable=True,
            status_code=e.code,
            latency_ms=round(latency_ms, 1),
            error=str(e.reason),
        )
    except urllib.error.URLError as e:
        return HealthResult(
            url=url,
            reachable=False,
            status_code=None,
            latency_ms=None,
            error=str(e.reason),
        )
    except Exception as e:  # noqa: BLE001
        return HealthResult(
            url=url,
            reachable=False,
            status_code=None,
            latency_ms=None,
            error=str(e),
        )


def run_health_check() -> int:
    print("NotebookLM Health Check")
    print("=" * 40)

    result = check_endpoint(NOTEBOOKLM_URL)

    status_label = "HEALTHY" if result.healthy else "UNHEALTHY"
    print(f"URL          : {result.url}")
    print(f"Status       : {status_label}")
    print(f"Reachable    : {result.reachable}")
    print(f"HTTP code    : {result.status_code if result.status_code is not None else 'N/A'}")
    print(f"Latency      : {f'{result.latency_ms} ms' if result.latency_ms is not None else 'N/A'}")
    if result.error:
        print(f"Error        : {result.error}")
    print("=" * 40)
    print(f"Result       : {'PASS' if result.healthy else 'FAIL'}")

    return 0 if result.healthy else 1


if __name__ == "__main__":
    sys.exit(run_health_check())
