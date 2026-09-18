from __future__ import annotations

import json
from pathlib import Path
from queue import Empty, Queue
import subprocess
import sys
import threading
import tkinter as tk
from tkinter import messagebox
import webbrowser

from src.mp_colppy.updater import LATEST_RELEASE_API, fetch_latest_release, is_newer


def application_directory() -> Path:
    if bool(getattr(sys, "frozen", False)):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def runtime_asset_path(filename: str) -> Path:
    bundle_root = getattr(sys, "_MEIPASS", None)
    if bundle_root is not None:
        return Path(bundle_root) / "assets" / filename
    return Path(__file__).resolve().parent / "assets" / filename


def apply_window_icon(root: tk.Tk) -> None:
    icon_path = runtime_asset_path("app-icon.png")
    if not icon_path.is_file():
        return
    try:
        icon = tk.PhotoImage(file=str(icon_path))
        root.iconphoto(True, icon)
        setattr(root, "_app_icon", icon)
    except tk.TclError:
        return


class LauncherSplash:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.frame = 0
        self.job: str | None = None
        root.withdraw()
        root.overrideredirect(True)
        width, height = 470, 250
        x = max(0, (root.winfo_screenwidth() - width) // 2)
        y = max(0, (root.winfo_screenheight() - height) // 2)
        root.geometry(f"{width}x{height}+{x}+{y}")
        self.canvas = tk.Canvas(root, width=width, height=height, bg="#102A49", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)
        self.canvas.create_rectangle(0, 0, width, 6, fill="#3B82C4", outline="")
        self.canvas.create_oval(190, 28, 280, 118, fill="#EAF4FC", outline="#6FB1E2", width=2)
        self.canvas.create_text(218, 73, text="MP", fill="#17365D", font=("Segoe UI", 13, "bold"))
        self.canvas.create_text(251, 73, text="→", fill="#2F75B5", font=("Segoe UI", 16, "bold"))
        self.canvas.create_text(266, 73, text="C", fill="#17365D", font=("Segoe UI", 13, "bold"))
        self.canvas.create_text(235, 149, text="Mercado Pago a Colppy", fill="#FFFFFF", font=("Segoe UI", 18, "bold"))
        self.message = self.canvas.create_text(
            235,
            181,
            text="Buscando actualizaciones seguras...",
            fill="#BFD7EA",
            font=("Segoe UI", 9),
        )
        self.canvas.create_rectangle(55, 211, 415, 219, fill="#284A6B", outline="")
        self.bar = self.canvas.create_rectangle(55, 211, 145, 219, fill="#62B5E5", outline="")
        root.deiconify()
        root.lift()
        self._animate()

    def _animate(self) -> None:
        track_width = 360
        segment_width = 90
        position = (self.frame * 9) % (track_width + segment_width) - segment_width
        left = 55 + max(0, position)
        right = 55 + min(track_width, position + segment_width)
        self.canvas.coords(self.bar, left, 211, max(left, right), 219)
        self.frame += 1
        self.job = self.root.after(45, self._animate)

    def set_message(self, message: str) -> None:
        self.canvas.itemconfigure(self.message, text=message)

    def close(self) -> None:
        if self.job is not None:
            self.root.after_cancel(self.job)
        self.root.withdraw()
        self.canvas.destroy()
        self.root.overrideredirect(False)


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
    apply_window_icon(root)
    splash = LauncherSplash(root)
    base = application_directory()
    try:
        installed = read_installed_version(base)
    except Exception:
        installed = "0.0.0"
    releases: Queue[object] = Queue(maxsize=1)

    def check_update() -> None:
        releases.put(fetch_latest_release(LATEST_RELEASE_API))

    def finish_startup() -> None:
        try:
            release = releases.get_nowait()
        except Empty:
            root.after(80, finish_startup)
            return

        splash.set_message("Abriendo la aplicación...")
        root.update_idletasks()
        splash.close()
        if release is not None:
            try:
                update_available = is_newer(installed, release.version)  # type: ignore[attr-defined]
            except (ValueError, AttributeError):
                update_available = False
            if update_available:
                open_download = messagebox.askyesno(
                    "Actualización disponible",
                    f"Tenés instalada la versión {installed} y está disponible la {release.version}.\n\n"  # type: ignore[attr-defined]
                    "¿Querés abrir la página de descarga?\n\n"
                    "Si elegís No, se abrirá la versión instalada.",
                    parent=root,
                )
                if open_download:
                    webbrowser.open(release.html_url)  # type: ignore[attr-defined]
        try:
            start_application(base)
        except Exception as exc:
            messagebox.showerror("No se pudo abrir", str(exc), parent=root)
        finally:
            root.destroy()

    threading.Thread(target=check_update, daemon=True).start()
    root.after(80, finish_startup)
    root.mainloop()


if __name__ == "__main__":
    main()
