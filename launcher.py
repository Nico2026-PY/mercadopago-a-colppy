from __future__ import annotations

import logging
import os
from pathlib import Path
import sys
import tempfile
import threading
import tkinter as tk
from tkinter import messagebox, ttk

from src.mp_colppy.updater import (
    UpdateClient,
    UpdateError,
    current_version,
    install_release,
    launch_current,
    parse_checksum,
)


def bundled_path(filename: str) -> Path:
    root = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    return root / filename


def local_app_root() -> Path:
    base = os.environ.get("LOCALAPPDATA", "").strip()
    if not base:
        base = str(Path.home() / "AppData" / "Local")
    return Path(base) / "MercadoPagoColppy"


class LauncherApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.app_root = local_app_root()
        self.app_root.mkdir(parents=True, exist_ok=True)
        self.temp_root = self.app_root / "temp"
        self.temp_root.mkdir(exist_ok=True)
        logging.basicConfig(
            filename=self.app_root / "launcher.log",
            level=logging.INFO,
            format="%(asctime)s %(levelname)s %(message)s",
            encoding="utf-8",
        )
        self.status = tk.StringVar(value="Preparando el launcher…")
        self._configure_window()
        self._build_ui()
        threading.Thread(target=self._run, daemon=True).start()

    def _configure_window(self) -> None:
        self.root.title("Mercado Pago a Colppy")
        self.root.geometry("480x250")
        self.root.resizable(False, False)
        self.root.configure(bg="#17365D")
        icon = bundled_path("assets/app-icon.ico")
        if os.name == "nt" and icon.exists():
            try:
                self.root.iconbitmap(str(icon))
            except tk.TclError:
                pass

    def _build_ui(self) -> None:
        panel = tk.Frame(self.root, bg="#17365D", padx=36, pady=28)
        panel.pack(fill="both", expand=True)
        tk.Label(
            panel,
            text="Mercado Pago a Colppy",
            bg="#17365D",
            fg="white",
            font=("Segoe UI", 18, "bold"),
        ).pack(pady=(8, 8))
        tk.Label(
            panel,
            textvariable=self.status,
            bg="#17365D",
            fg="#DCE8F2",
            font=("Segoe UI", 10),
            wraplength=390,
        ).pack(pady=(0, 18))
        self.progress = ttk.Progressbar(panel, mode="indeterminate", length=350)
        self.progress.pack()
        self.progress.start(12)

    def _set_status(self, message: str) -> None:
        self.root.after(0, self.status.set, message)

    def _ask_update(self, version: str) -> bool:
        result: list[bool] = []
        ready = threading.Event()

        def ask() -> None:
            result.append(
                messagebox.askyesno(
                    "Actualización disponible",
                    f"Está disponible la versión {version}.\n\n¿Querés instalarla ahora?",
                    parent=self.root,
                )
            )
            ready.set()

        self.root.after(0, ask)
        ready.wait()
        return result[0]

    def _launch_installed(self) -> None:
        try:
            launch_current(self.app_root)
        except UpdateError:
            logging.exception("No se pudo abrir la aplicación instalada")
            raise
        self._set_status("Abriendo la aplicación…")
        self.root.after(500, self.root.destroy)

    def _run(self) -> None:
        try:
            installed = current_version(self.app_root)
            self._set_status("Buscando actualizaciones…")
            client = UpdateClient()
            try:
                release = client.latest_release()
            except Exception:
                logging.exception("No se pudo comprobar la actualización")
                if installed is None:
                    raise
                self._set_status("Sin conexión. Abriendo la versión instalada…")
                self._launch_installed()
                return

            if installed is not None and release.version <= installed:
                self._launch_installed()
                return
            if installed is not None and not self._ask_update(str(release.version)):
                self._launch_installed()
                return

            self._set_status(f"Descargando {release.version}…")
            with tempfile.TemporaryDirectory(prefix="update-", dir=self.temp_root) as temporary:
                archive = Path(temporary) / client.archive_name
                client.download(release.archive_url, archive)
                checksum = parse_checksum(client.download_text(release.checksum_url), client.archive_name)
                self._set_status("Verificando e instalando…")
                install_release(archive, release.version, checksum, self.app_root)
            logging.info("Versión %s instalada", release.version)
            self._launch_installed()
        except Exception as exc:
            logging.exception("El launcher no pudo continuar")
            error_detail = str(exc)

            def show_error() -> None:
                self.progress.stop()
                self.status.set("No se pudo instalar la aplicación.")
                messagebox.showerror(
                    "No se pudo abrir",
                    "No hay una versión instalada y no se pudo descargar.\n\n"
                    f"Detalle: {error_detail}\n\nRevisá tu conexión e intentá nuevamente.",
                    parent=self.root,
                )

            self.root.after(0, show_error)


def main() -> None:
    root = tk.Tk()
    LauncherApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
