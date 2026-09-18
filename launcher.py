from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tkinter as tk
from tkinter import messagebox
import webbrowser

from src.mp_colppy.updater import LATEST_RELEASE_API, fetch_latest_release, is_newer


def application_directory() -> Path:
    if bool(getattr(sys, "frozen", False)):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def read_installed_version(base: Path) -> str:
    payload = json.loads((base / "version.json").read_text(encoding="utf-8"))
    version = payload.get("version")
    if not isinstance(version, str):
        raise ValueError("version.json no contiene una versión válida")
    return version


def start_application(base: Path) -> None:
    if bool(getattr(sys, "frozen", False)):
        command = [str(base / "MercadoPagoColppy.exe")]
    else:
        command = [sys.executable, str(base / "main.py")]
    if not Path(command[-1]).exists():
        raise FileNotFoundError(f"No se encontró la aplicación: {command[-1]}")
    subprocess.Popen(command, cwd=base)


def main() -> None:
    root = tk.Tk()
    root.withdraw()
    base = application_directory()
    try:
        installed = read_installed_version(base)
    except Exception:
        installed = "0.0.0"

    release = fetch_latest_release(LATEST_RELEASE_API)
    if release is not None:
        try:
            update_available = is_newer(installed, release.version)
        except ValueError:
            update_available = False
        if update_available:
            open_download = messagebox.askyesno(
                "Actualización disponible",
                f"Tenés instalada la versión {installed} y está disponible la {release.version}.\n\n"
                "¿Querés abrir la página de descarga?\n\n"
                "Si elegís No, se abrirá la versión instalada.",
                parent=root,
            )
            if open_download:
                webbrowser.open(release.html_url)

    try:
        start_application(base)
    except Exception as exc:
        messagebox.showerror("No se pudo abrir", str(exc), parent=root)
    finally:
        root.destroy()


if __name__ == "__main__":
    main()
