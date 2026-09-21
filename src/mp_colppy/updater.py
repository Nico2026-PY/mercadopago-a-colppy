from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import hmac
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import subprocess
from typing import BinaryIO, Callable
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from uuid import uuid4
from zipfile import BadZipFile, ZipFile, ZipInfo


LATEST_RELEASE_API = "https://api.github.com/repos/Nico2026-PY/mercadopago-a-colppy/releases/latest"
DEFAULT_ARCHIVE_NAME = "MercadoPagoColppy-Windows.zip"
DEFAULT_CHECKSUM_NAME = "SHA256SUMS.txt"
DEFAULT_EXECUTABLE_NAME = "MercadoPagoColppy.exe"
MAX_UNCOMPRESSED_BYTES = 750 * 1024 * 1024


class UpdateError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class ReleaseInfo:
    version: str
    html_url: str


@dataclass(frozen=True, order=True, slots=True)
class Version:
    major: int
    minor: int
    patch: int

    @classmethod
    def parse(cls, value: str) -> "Version":
        try:
            return cls(*parse_version(value))
        except ValueError as exc:
            raise UpdateError(str(exc)) from exc

    def __str__(self) -> str:
        return f"v{self.major}.{self.minor}.{self.patch}"


@dataclass(frozen=True, slots=True)
class InstallableRelease:
    version: Version
    archive_url: str
    checksum_url: str


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


class UpdateClient:
    def __init__(
        self,
        owner: str = "Nico2026-PY",
        repository: str = "mercadopago-a-colppy",
        archive_name: str = DEFAULT_ARCHIVE_NAME,
        checksum_name: str = DEFAULT_CHECKSUM_NAME,
        timeout: float = 8.0,
        opener: Callable[..., BinaryIO] = urlopen,
    ):
        self.owner = owner
        self.repository = repository
        self.archive_name = archive_name
        self.checksum_name = checksum_name
        self.timeout = timeout
        self.opener = opener

    def _open(self, url: str) -> BinaryIO:
        request = Request(
            url,
            headers={
                "Accept": "application/vnd.github+json",
                "User-Agent": "MercadoPagoColppy-Launcher",
                "X-GitHub-Api-Version": "2022-11-28",
            },
        )
        try:
            return self.opener(request, timeout=self.timeout)
        except (HTTPError, URLError, TimeoutError, OSError) as exc:
            raise UpdateError(f"No se pudo conectar con GitHub: {exc}") from exc

    def latest_release(self) -> InstallableRelease:
        url = f"https://api.github.com/repos/{self.owner}/{self.repository}/releases/latest"
        try:
            with self._open(url) as response:
                payload = json.loads(response.read().decode("utf-8"))
            version = Version.parse(str(payload.get("tag_name", "")))
            assets = {
                str(asset.get("name")): str(asset.get("browser_download_url"))
                for asset in payload.get("assets", [])
                if isinstance(asset, dict)
            }
        except (json.JSONDecodeError, UnicodeDecodeError, KeyError, TypeError, UpdateError) as exc:
            if isinstance(exc, UpdateError):
                raise
            raise UpdateError("GitHub devolvió una Release inválida") from exc
        archive_url = assets.get(self.archive_name, "")
        checksum_url = assets.get(self.checksum_name, "")
        if not archive_url or not checksum_url:
            raise UpdateError(
                f"La Release {version} no contiene {self.archive_name} y {self.checksum_name}"
            )
        return InstallableRelease(version, archive_url, checksum_url)

    def download(self, url: str, destination: str | Path) -> Path:
        output = Path(destination)
        output.parent.mkdir(parents=True, exist_ok=True)
        try:
            with self._open(url) as response, output.open("wb") as handle:
                while chunk := response.read(1024 * 256):
                    handle.write(chunk)
        except Exception:
            output.unlink(missing_ok=True)
            raise
        return output

    def download_text(self, url: str) -> str:
        try:
            with self._open(url) as response:
                return response.read().decode("ascii")
        except (UnicodeDecodeError, OSError) as exc:
            raise UpdateError("No se pudo leer el archivo SHA-256") from exc


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def parse_checksum(text: str, expected_filename: str = DEFAULT_ARCHIVE_NAME) -> str:
    for line in text.splitlines():
        match = re.fullmatch(r"\s*([0-9a-fA-F]{64})\s+\*?(.+?)\s*", line)
        if match and Path(match.group(2)).name == expected_filename:
            return match.group(1).lower()
    stripped = text.strip()
    if re.fullmatch(r"[0-9a-fA-F]{64}", stripped):
        return stripped.lower()
    raise UpdateError(f"El archivo SHA-256 no contiene el hash de {expected_filename}")


def verify_sha256(path: str | Path, expected_hash: str) -> None:
    expected = expected_hash.strip().lower()
    if not re.fullmatch(r"[0-9a-f]{64}", expected):
        raise UpdateError("El SHA-256 publicado no es válido")
    if not hmac.compare_digest(sha256_file(path), expected):
        raise UpdateError("La verificación SHA-256 del paquete falló")


def _safe_member_path(name: str) -> PurePosixPath:
    member = PurePosixPath(name.replace("\\", "/"))
    first = member.parts[0] if member.parts else ""
    if not member.parts or member.is_absolute() or ".." in member.parts or ":" in first:
        raise UpdateError(f"El ZIP contiene una ruta insegura: {name}")
    return member


def safe_extract_zip(archive_path: str | Path, destination: str | Path) -> Path:
    destination_path = Path(destination)
    destination_path.mkdir(parents=True, exist_ok=True)
    try:
        with ZipFile(archive_path) as archive:
            infos = archive.infolist()
            if sum(info.file_size for info in infos) > MAX_UNCOMPRESSED_BYTES:
                raise UpdateError("El paquete descomprimido supera el tamaño permitido")
            validated: list[tuple[ZipInfo, PurePosixPath]] = []
            for info in infos:
                member = _safe_member_path(info.filename)
                if stat.S_ISLNK(info.external_attr >> 16):
                    raise UpdateError(f"El ZIP contiene un enlace no permitido: {info.filename}")
                validated.append((info, member))
            for info, member in validated:
                target = destination_path.joinpath(*member.parts)
                if info.is_dir():
                    target.mkdir(parents=True, exist_ok=True)
                    continue
                target.parent.mkdir(parents=True, exist_ok=True)
                with archive.open(info) as source, target.open("wb") as output:
                    shutil.copyfileobj(source, output)
    except BadZipFile as exc:
        raise UpdateError("El paquete descargado no es un ZIP válido") from exc
    return destination_path


def read_current_manifest(root: str | Path) -> dict[str, str] | None:
    manifest_path = Path(root) / "current.json"
    if not manifest_path.exists():
        return None
    try:
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
        version = str(payload["version"])
        executable = str(payload["executable"])
        Version.parse(version)
        return {"version": version, "executable": executable}
    except (OSError, json.JSONDecodeError, KeyError, TypeError, UpdateError) as exc:
        raise UpdateError("La instalación local tiene un manifiesto inválido") from exc


def current_version(root: str | Path) -> Version | None:
    manifest = read_current_manifest(root)
    return Version.parse(manifest["version"]) if manifest else None


def install_release(
    archive_path: str | Path,
    version: str | Version,
    expected_hash: str,
    root: str | Path,
    executable_name: str = DEFAULT_EXECUTABLE_NAME,
) -> Path:
    app_root = Path(root).resolve()
    app_root.mkdir(parents=True, exist_ok=True)
    parsed_version = version if isinstance(version, Version) else Version.parse(version)
    verify_sha256(archive_path, expected_hash)
    versions = app_root / "versions"
    versions.mkdir(parents=True, exist_ok=True)
    target = versions / str(parsed_version)
    executable = target / executable_name

    if target.exists():
        if not executable.is_file():
            raise UpdateError(f"La versión existente no contiene {executable_name}")
    else:
        temporary = versions / f".install-{parsed_version}-{uuid4().hex}"
        try:
            safe_extract_zip(archive_path, temporary)
            if not (temporary / executable_name).is_file():
                raise UpdateError(f"El paquete no contiene {executable_name}")
            os.replace(temporary, target)
        finally:
            if temporary.exists():
                shutil.rmtree(temporary, ignore_errors=True)

    manifest = {
        "version": str(parsed_version),
        "executable": str(executable),
        "installed_at": datetime.now(timezone.utc).isoformat(),
    }
    manifest_temp = app_root / "current.json.tmp"
    manifest_temp.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    os.replace(manifest_temp, app_root / "current.json")
    return executable


def launch_current(root: str | Path) -> subprocess.Popen[bytes]:
    app_root = Path(root).resolve()
    manifest = read_current_manifest(app_root)
    if not manifest:
        raise UpdateError("Todavía no hay una versión instalada")
    executable = Path(manifest["executable"]).resolve()
    try:
        executable.relative_to(app_root / "versions")
    except ValueError as exc:
        raise UpdateError("El manifiesto apunta fuera de la instalación") from exc
    if not executable.is_file():
        raise UpdateError("No se encontró la aplicación instalada")
    environment = os.environ.copy()
    environment["MP_COLPPY_HOME"] = str(app_root)
    try:
        return subprocess.Popen([str(executable)], cwd=executable.parent, env=environment)
    except OSError as exc:
        raise UpdateError(f"No se pudo abrir la aplicación: {exc}") from exc
