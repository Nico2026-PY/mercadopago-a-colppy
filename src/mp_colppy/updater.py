from __future__ import annotations

from dataclasses import dataclass
import json
import re
from typing import Callable
from urllib.error import URLError
from urllib.request import Request, urlopen


LATEST_RELEASE_API = "https://api.github.com/repos/Nico2026-PY/mercadopago-a-colppy/releases/latest"


@dataclass(frozen=True, slots=True)
class ReleaseInfo:
    version: str
    html_url: str


def parse_version(value: str) -> tuple[int, int, int]:
    match = re.fullmatch(r"v?(\d+)\.(\d+)\.(\d+)", value.strip())
    if match is None:
        raise ValueError(f"Versión no válida: {value}")
    return tuple(int(part) for part in match.groups())  # type: ignore[return-value]


def is_newer(installed: str, available: str) -> bool:
    return parse_version(available) > parse_version(installed)


def fetch_latest_release(
    url: str = LATEST_RELEASE_API,
    timeout: float = 4.0,
    opener: Callable[..., object] = urlopen,
) -> ReleaseInfo | None:
    if not url.startswith("https://"):
        return None
    request = Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "MercadoPagoColppy-Launcher",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    try:
        with opener(request, timeout=timeout) as response:  # type: ignore[attr-defined]
            payload = json.loads(response.read().decode("utf-8"))
        tag = payload["tag_name"]
        html_url = payload["html_url"]
        if not isinstance(tag, str) or not isinstance(html_url, str) or not html_url.startswith("https://"):
            return None
        version = ".".join(str(part) for part in parse_version(tag))
        return ReleaseInfo(version, html_url)
    except (URLError, TimeoutError, OSError, json.JSONDecodeError, KeyError, TypeError, ValueError, UnicodeDecodeError):
        return None
