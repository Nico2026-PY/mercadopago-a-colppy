from __future__ import annotations

from dataclasses import replace
from decimal import Decimal
import os
from pathlib import Path
import subprocess
import sys
import threading
import time
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, ttk
from typing import Callable

from .companies import Company, CompanyConfig, CompanyConfigRepository
from .domain import ParseIssue
from .excel_io import export_colppy_csv
from .history import HistoryRepository
from .paths import AppPaths, resolve_app_paths
from .report_validation import classify_period, detect_company_from_paths, output_filename
from .service import AnalysisResult, ImportService


def format_currency(value: Decimal) -> str:
    negative = value < 0
    absolute = abs(value)
    raw = f"{absolute:,.2f}"
    localized = raw.replace(",", "_").replace(".", ",").replace("_", ".")
    return f"{'-' if negative else ''}$ {localized}"


def adaptive_window_geometry(screen_width: int, screen_height: int) -> str:
    width = min(1160, max(720, screen_width - 80))
    height = min(720, max(600, screen_height - 110))
    x = max(0, (screen_width - width) // 2)
    y = max(0, (screen_height - height) // 2)
    return f"{width}x{height}+{x}+{y}"


def runtime_asset_path(filename: str) -> Path:
    bundle_root = getattr(sys, "_MEIPASS", None)
    if bundle_root is not None:
        return Path(bundle_root) / "assets" / filename
    return Path(__file__).resolve().parents[2] / "assets" / filename


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


def company_names(config: CompanyConfig) -> tuple[str, ...]:
    return tuple(company.name for company in config.companies)


def company_id_for_name(config: CompanyConfig, name: str) -> str | None:
    return next((company.id for company in config.companies if company.name == name), None)


def require_selected_company(config: CompanyConfig) -> Company:
    selected = next(
        (company for company in config.companies if company.id == config.selected_company_id),
        None,
    )
    if selected is None:
        raise ValueError("Seleccioná una empresa antes de continuar")
    return selected


class StartupSplash:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.started_at = time.monotonic()
        self.animation_frame = 0
        self.animation_job: str | None = None
        setattr(root, "_startup_splash_active", True)
        root.withdraw()
        root.overrideredirect(True)
        width, height = 540, 330
        x = max(0, (root.winfo_screenwidth() - width) // 2)
        y = max(0, (root.winfo_screenheight() - height) // 2)
        root.geometry(f"{width}x{height}+{x}+{y}")
        root.configure(bg="#102A49")

        self.canvas = tk.Canvas(root, width=width, height=height, bg="#102A49", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)
        self.canvas.create_rectangle(0, 0, width, 7, fill="#3B82C4", outline="")
        self.canvas.create_oval(220, 40, 320, 140, fill="#EAF4FC", outline="#6FB1E2", width=2)
        self.canvas.create_text(250, 90, text="MP", fill="#17365D", font=("Segoe UI", 15, "bold"))
        self.canvas.create_text(292, 90, text="→", fill="#2F75B5", font=("Segoe UI", 18, "bold"))
        self.canvas.create_text(304, 90, text="C", fill="#17365D", font=("Segoe UI", 15, "bold"))
        self.canvas.create_text(270, 175, text="Mercado Pago a Colppy", fill="#FFFFFF", font=("Segoe UI", 21, "bold"))
        self.canvas.create_text(270, 204, text="Preparando tu espacio de trabajo", fill="#BFD7EA", font=("Segoe UI", 10))
        self.canvas.create_rectangle(65, 240, 475, 250, fill="#284A6B", outline="")
        self.progress_fill = self.canvas.create_rectangle(65, 240, 65, 250, fill="#62B5E5", outline="")
        self.message_item = self.canvas.create_text(65, 278, text="Iniciando...", anchor="w", fill="#E7F2FA", font=("Segoe UI", 9))
        self.percent_item = self.canvas.create_text(475, 278, text="0%", anchor="e", fill="#FFFFFF", font=("Segoe UI", 9, "bold"))
        self.dots = [
            self.canvas.create_oval(252 + index * 14, 301, 258 + index * 14, 307, fill="#496B88", outline="")
            for index in range(3)
        ]
        root.deiconify()
        root.lift()
        self._animate()
        root.update()

    def _animate(self) -> None:
        colors = ("#62B5E5", "#8BC9EE", "#496B88")
        for index, item in enumerate(self.dots):
            self.canvas.itemconfigure(item, fill=colors[(index - self.animation_frame) % len(colors)])
        self.animation_frame = (self.animation_frame + 1) % len(colors)
        self.animation_job = self.root.after(140, self._animate)

    def update(self, value: int, message: str) -> None:
        safe_value = max(0, min(100, value))
        self.canvas.coords(self.progress_fill, 65, 240, 65 + int(410 * safe_value / 100), 250)
        self.canvas.itemconfigure(self.message_item, text=message)
        self.canvas.itemconfigure(self.percent_item, text=f"{safe_value}%")
        self.root.update()

    def close(self) -> None:
        remaining_ms = max(0, 750 - int((time.monotonic() - self.started_at) * 1000))
        if remaining_ms:
            finished = tk.BooleanVar(value=False)
            self.root.after(remaining_ms, lambda: finished.set(True))
            self.root.wait_variable(finished)
        if self.animation_job is not None:
            self.root.after_cancel(self.animation_job)
        self.root.withdraw()
        self.canvas.destroy()
        self.root.overrideredirect(False)
        setattr(self.root, "_startup_splash_active", False)
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        self.root.geometry(adaptive_window_geometry(screen_width, screen_height))
        self.root.minsize(
            min(900, max(720, screen_width - 80)),
            min(600, max(560, screen_height - 110)),
        )
        self.root.deiconify()
        self.root.lift()


class MercadoPagoColppyApp:
    COLORS = {
        "navy": "#17365D",
        "blue": "#2F75B5",
        "light": "#EEF5FB",
        "border": "#D6E1EA",
        "text": "#1F2937",
        "muted": "#64748B",
        "green": "#16803C",
        "red": "#B42318",
        "amber": "#B26A00",
        "white": "#FFFFFF",
    }

    def __init__(
        self,
        root: tk.Tk,
        app_paths: AppPaths | None = None,
        startup_progress: Callable[[int, str], None] | None = None,
    ):
        def startup(value: int, message: str) -> None:
            if startup_progress is not None:
                startup_progress(value, message)

        self.root = root
        startup(10, "Preparando carpetas locales...")
        self.paths = app_paths or resolve_app_paths()
        self.company_repository = CompanyConfigRepository(self.paths.config)
        self.selected_files: list[Path] = []
        self.current_result: AnalysisResult | None = None
        self.last_export_path: Path | None = None
        self.analysis_blocked_reason: str | None = None
        self._validated_selection_key: tuple[tuple[str, ...], str] | None = None

        self._configure_window()
        self._configure_style()
        startup(30, "Leyendo configuración local...")
        self.company_config = self.company_repository.load()
        self._ensure_first_company()
        startup(55, "Preparando la empresa seleccionada...")
        selected_company = require_selected_company(self.company_config)
        self.company_paths = self.paths.for_company(selected_company.id)
        self.history = HistoryRepository(self.company_paths.database, self.company_paths.backups)
        self.service = ImportService(self.history)
        startup(75, "Comprobando el historial...")

        self.company_var = tk.StringVar(value=selected_company.name)
        self.mode_var = tk.StringVar(value="Diario")
        self.status_var = tk.StringVar(value="Seleccioná uno o varios reportes de Mercado Pago.")
        self.analysis_progress_var = tk.DoubleVar(value=0)
        self.analysis_progress_message_var = tk.StringVar(value="Listo para analizar")
        self.summary_vars = {
            "rows": tk.StringVar(value="0"),
            "new": tk.StringVar(value="0"),
            "imported": tk.StringVar(value="0"),
            "review": tk.StringVar(value="0"),
            "duplicates": tk.StringVar(value="0"),
            "net": tk.StringVar(value="$ 0,00"),
        }

        startup(88, "Creando la pantalla principal...")
        self._build_ui()
        startup(100, "Aplicación lista")

    def _ensure_first_company(self) -> None:
        while not self.company_config.companies:
            name = simpledialog.askstring(
                "Configurar empresa",
                "Ingresá el nombre de la primera empresa.\nSe guardará solamente en esta computadora:",
                parent=self.root,
            )
            if name is None:
                raise RuntimeError("Necesitás configurar una empresa para usar la aplicación")
            try:
                self.company_config = self.company_repository.add(name)
            except ValueError as exc:
                messagebox.showerror("Nombre no válido", str(exc), parent=self.root)

    def _configure_window(self) -> None:
        self.root.title("Mercado Pago a Colppy")
        if not bool(getattr(self.root, "_startup_splash_active", False)):
            width = self.root.winfo_screenwidth()
            height = self.root.winfo_screenheight()
            self.root.geometry(adaptive_window_geometry(width, height))
            self.root.minsize(min(900, max(720, width - 80)), min(600, max(560, height - 110)))
        self.root.configure(bg=self.COLORS["white"])

    def _configure_style(self) -> None:
        style = ttk.Style(self.root)
        style.theme_use("clam")
        style.configure("TFrame", background=self.COLORS["white"])
        style.configure("TLabel", background=self.COLORS["white"], foreground=self.COLORS["text"], font=("Segoe UI", 10))
        style.configure("Header.TLabel", font=("Segoe UI", 18, "bold"), foreground=self.COLORS["white"], background=self.COLORS["navy"])
        style.configure("HeaderSub.TLabel", font=("Segoe UI", 10), foreground="#DCE8F2", background=self.COLORS["navy"])
        style.configure("Section.TLabel", font=("Segoe UI", 11, "bold"), foreground=self.COLORS["navy"])
        style.configure("Kpi.TLabel", font=("Segoe UI", 15, "bold"), foreground=self.COLORS["navy"], background=self.COLORS["light"])
        style.configure("KpiName.TLabel", font=("Segoe UI", 9), foreground=self.COLORS["muted"], background=self.COLORS["light"])
        style.configure("Primary.TButton", font=("Segoe UI", 10, "bold"), foreground=self.COLORS["white"], background=self.COLORS["blue"], padding=(14, 8))
        style.map("Primary.TButton", background=[("active", "#265F91"), ("disabled", "#AAB8C4")])
        style.configure("Secondary.TButton", font=("Segoe UI", 10), foreground=self.COLORS["navy"], background=self.COLORS["light"], padding=(12, 8))
        style.map("Secondary.TButton", background=[("active", "#DDEBF7")])
        style.configure("Treeview", font=("Segoe UI", 9), rowheight=26, fieldbackground=self.COLORS["white"], bordercolor=self.COLORS["border"])
        style.configure("Treeview.Heading", font=("Segoe UI", 9, "bold"), foreground=self.COLORS["white"], background=self.COLORS["navy"], padding=(6, 6))
        style.map("Treeview.Heading", background=[("active", self.COLORS["navy"])])
        style.configure("TRadiobutton", font=("Segoe UI", 10), background=self.COLORS["white"])

    def _build_ui(self) -> None:
        header = tk.Frame(self.root, bg=self.COLORS["navy"], height=72)
        header.pack(fill="x")
        header.pack_propagate(False)
        ttk.Label(header, text="Mercado Pago a Colppy", style="Header.TLabel").pack(anchor="w", padx=18, pady=(10, 0))
        ttk.Label(header, text="Seleccioná reportes, revisá los movimientos nuevos y exportá sin duplicados.", style="HeaderSub.TLabel").pack(anchor="w", padx=18)

        body = ttk.Frame(self.root, padding=12)
        body.pack(fill="both", expand=True)

        settings_row = ttk.Frame(body)
        settings_row.pack(fill="x")
        ttk.Label(settings_row, text="Empresa", style="Section.TLabel").pack(side="left", padx=(0, 8))
        self.company_combo = ttk.Combobox(
            settings_row,
            textvariable=self.company_var,
            values=company_names(self.company_config),
            state="readonly",
            width=22,
        )
        self.company_combo.pack(side="left")
        self.company_combo.bind("<<ComboboxSelected>>", self._on_company_selected)
        ttk.Button(settings_row, text="Empresas...", style="Secondary.TButton", command=self._manage_companies).pack(side="left", padx=(6, 24))
        ttk.Label(settings_row, text="Tipo de reporte", style="Section.TLabel").pack(side="left", padx=(0, 10))
        ttk.Radiobutton(settings_row, text="Diario", variable=self.mode_var, value="Diario").pack(side="left")
        ttk.Radiobutton(settings_row, text="Mensual", variable=self.mode_var, value="Mensual").pack(side="left", padx=(8, 0))
        ttk.Button(settings_row, text="Abrir salidas", style="Secondary.TButton", command=self._open_outputs).pack(side="right")

        file_actions = ttk.Frame(body)
        file_actions.pack(fill="x", pady=(7, 0))
        ttk.Button(file_actions, text="Seleccionar archivos", style="Primary.TButton", command=self._select_files).pack(side="left")
        self.analyze_button = ttk.Button(file_actions, text="Analizar", style="Secondary.TButton", command=self._start_analysis, state="disabled")
        self.analyze_button.pack(side="left", padx=8)
        ttk.Button(file_actions, text="Limpiar", style="Secondary.TButton", command=self._clear_selection).pack(side="left")
        ttk.Label(file_actions, text="Formatos admitidos: CSV, XLS y XLSX", foreground=self.COLORS["muted"]).pack(side="right")

        file_frame = ttk.Frame(body)
        file_frame.pack(fill="x", pady=(8, 6))
        ttk.Label(file_frame, text="Archivos seleccionados", style="Section.TLabel").pack(anchor="w", pady=(0, 3))
        self.file_list = tk.Listbox(file_frame, height=2, font=("Segoe UI", 9), relief="solid", borderwidth=1, highlightthickness=0, selectmode="extended")
        self.file_list.pack(fill="x")

        progress_frame = ttk.Frame(body)
        progress_frame.pack(fill="x", pady=(0, 6))
        ttk.Progressbar(progress_frame, variable=self.analysis_progress_var, maximum=100).pack(side="left", fill="x", expand=True)
        ttk.Label(progress_frame, textvariable=self.analysis_progress_message_var, foreground=self.COLORS["muted"]).pack(side="left", padx=(10, 0))

        kpis = ttk.Frame(body)
        kpis.pack(fill="x", pady=(0, 7))
        kpi_definitions = [
            ("Filas leídas", "rows"),
            ("Nuevos", "new"),
            ("Ya importados", "imported"),
            ("Para revisar", "review"),
            ("Duplicados", "duplicates"),
            ("Neto nuevo", "net"),
        ]
        for index, (label, key) in enumerate(kpi_definitions):
            card = tk.Frame(kpis, bg=self.COLORS["light"], highlightbackground=self.COLORS["border"], highlightthickness=1, padx=9, pady=5)
            card.grid(row=0, column=index, sticky="nsew", padx=(0 if index == 0 else 5, 0))
            ttk.Label(card, textvariable=self.summary_vars[key], style="Kpi.TLabel").pack(anchor="w")
            ttk.Label(card, text=label, style="KpiName.TLabel").pack(anchor="w")
            kpis.columnconfigure(index, weight=1)

        notebook = ttk.Notebook(body)
        notebook.pack(fill="both", expand=True)
        preview_tab = ttk.Frame(notebook, padding=8)
        issues_tab = ttk.Frame(notebook, padding=8)
        notebook.add(preview_tab, text="Vista previa para Colppy")
        notebook.add(issues_tab, text="Revisiones y errores")

        self.preview = ttk.Treeview(preview_tab, columns=("date", "concept", "receipt", "amount", "file"), show="headings")
        headings = {
            "date": ("Fecha", 95, "center"),
            "concept": ("Concepto", 520, "w"),
            "receipt": ("Nro. comprobante", 150, "w"),
            "amount": ("Importe", 120, "e"),
            "file": ("Archivo", 190, "w"),
        }
        for key, (text, width, anchor) in headings.items():
            self.preview.heading(key, text=text)
            self.preview.column(key, width=width, minwidth=70, anchor=anchor, stretch=(key in {"concept", "file"}))
        self.preview.tag_configure("positive", foreground=self.COLORS["green"])
        self.preview.tag_configure("negative", foreground=self.COLORS["red"])
        preview_scroll = ttk.Scrollbar(preview_tab, orient="vertical", command=self.preview.yview)
        self.preview.configure(yscrollcommand=preview_scroll.set)
        self.preview.pack(side="left", fill="both", expand=True)
        preview_scroll.pack(side="right", fill="y")

        self.issues = ttk.Treeview(issues_tab, columns=("file", "row", "message"), show="headings")
        self.issues.heading("file", text="Archivo")
        self.issues.heading("row", text="Fila")
        self.issues.heading("message", text="Motivo")
        self.issues.column("file", width=260, anchor="w")
        self.issues.column("row", width=70, anchor="center", stretch=False)
        self.issues.column("message", width=650, anchor="w")
        issue_scroll = ttk.Scrollbar(issues_tab, orient="vertical", command=self.issues.yview)
        self.issues.configure(yscrollcommand=issue_scroll.set)
        self.issues.pack(side="left", fill="both", expand=True)
        issue_scroll.pack(side="right", fill="y")

        actions = ttk.Frame(body)
        actions.pack(fill="x", pady=(7, 0))
        self.export_button = ttk.Button(actions, text="Exportar para Colppy", style="Primary.TButton", command=self._export, state="disabled")
        self.export_button.pack(side="left")
        self.confirm_button = ttk.Button(actions, text="Confirmar importación", style="Secondary.TButton", command=self._confirm_import, state="disabled")
        self.confirm_button.pack(side="left", padx=8)
        ttk.Button(actions, text="Respaldar historial", style="Secondary.TButton", command=self._backup_history).pack(side="left")
        ttk.Label(actions, textvariable=self.status_var, foreground=self.COLORS["muted"], wraplength=430).pack(side="right")

    def _refresh_company_selector(self) -> None:
        self.company_config = self.company_repository.load()
        self.company_combo.configure(values=company_names(self.company_config))
        selected = require_selected_company(self.company_config)
        self.company_var.set(selected.name)

    def _on_company_selected(self, _event: object | None = None) -> None:
        company_id = company_id_for_name(self.company_config, self.company_var.get())
        if company_id is None or company_id == self.company_config.selected_company_id:
            return
        try:
            self._activate_company(company_id, clear_selection=True)
        except Exception as exc:
            messagebox.showerror("No se pudo cambiar de empresa", str(exc), parent=self.root)
            self._refresh_company_selector()

    def _activate_company(self, company_id: str, clear_selection: bool) -> None:
        self.company_config = self.company_repository.select(company_id)
        selected = require_selected_company(self.company_config)
        self.company_paths = self.paths.for_company(selected.id)
        self.history = HistoryRepository(self.company_paths.database, self.company_paths.backups)
        self.service = ImportService(self.history)
        self.company_var.set(selected.name)
        self._validated_selection_key = None
        if clear_selection:
            self._clear_selection()
        self.status_var.set(f"Empresa activa: {selected.name}")

    def _confirm_company_for_files(self, files: list[Path]) -> bool:
        active = require_selected_company(self.company_config)
        key = (tuple(sorted(str(path.resolve()) for path in files)), active.id)
        if self._validated_selection_key == key:
            return True

        detection = detect_company_from_paths(files, self.company_config.companies)
        if detection.status == "mixed":
            messagebox.showerror(
                "Empresas mezcladas",
                "Los archivos seleccionados parecen pertenecer a empresas diferentes.\n\n"
                "Seleccioná solamente archivos de una empresa por vez.",
                parent=self.root,
            )
            return False

        if detection.company_id is not None:
            detected = next(company for company in self.company_config.companies if company.id == detection.company_id)
            if detected.id != active.id:
                change = messagebox.askyesno(
                    "Empresa detectada",
                    f"Los archivos parecen corresponder a {detected.name}, pero está seleccionada {active.name}.\n\n"
                    f"¿Querés cambiar a {detected.name} y continuar?",
                    parent=self.root,
                )
                if not change:
                    return False
                self._activate_company(detected.id, clear_selection=False)
                active = detected
            if detection.status == "partial":
                confirmed = messagebox.askyesno(
                    "Confirmar empresa",
                    f"Algunos nombres de archivo no indican la empresa.\n\n"
                    f"¿Confirmás que todos corresponden a {active.name}?",
                    parent=self.root,
                )
                if not confirmed:
                    return False
        else:
            confirmed = messagebox.askyesno(
                "No se pudo identificar la empresa",
                f"El nombre del archivo no indica ninguna empresa configurada.\n\n"
                f"¿Confirmás que corresponde a {active.name}?",
                parent=self.root,
            )
            if not confirmed:
                return False

        self._validated_selection_key = (
            tuple(sorted(str(path.resolve()) for path in files)),
            require_selected_company(self.company_config).id,
        )
        return True

    def _manage_companies(self) -> None:
        window = tk.Toplevel(self.root)
        window.title("Empresas locales")
        window.geometry("430x330")
        window.minsize(380, 280)
        window.transient(self.root)
        window.grab_set()

        frame = ttk.Frame(window, padding=16)
        frame.pack(fill="both", expand=True)
        ttk.Label(frame, text="Empresas guardadas en esta PC", style="Section.TLabel").pack(anchor="w")
        ttk.Label(frame, text="Cada empresa mantiene su propio historial, salidas y respaldos.", foreground=self.COLORS["muted"]).pack(anchor="w", pady=(3, 10))
        company_list = tk.Listbox(frame, font=("Segoe UI", 10), relief="solid", borderwidth=1, exportselection=False)
        company_list.pack(fill="both", expand=True)

        def refresh_list(select_id: str | None = None) -> None:
            self.company_config = self.company_repository.load()
            company_list.delete(0, tk.END)
            selected_index = 0
            target_id = select_id or self.company_config.selected_company_id
            for index, company in enumerate(self.company_config.companies):
                company_list.insert(tk.END, company.name)
                if company.id == target_id:
                    selected_index = index
            if self.company_config.companies:
                company_list.selection_set(selected_index)
                company_list.see(selected_index)
            self._refresh_company_selector()

        def add_company() -> None:
            name = simpledialog.askstring("Agregar empresa", "Nombre de la empresa:", parent=window)
            if name is None:
                return
            try:
                previous_ids = {company.id for company in self.company_config.companies}
                config = self.company_repository.add(name)
                new_company = next(company for company in config.companies if company.id not in previous_ids)
                refresh_list(new_company.id)
            except ValueError as exc:
                messagebox.showerror("No se pudo agregar", str(exc), parent=window)

        def rename_company() -> None:
            selection = company_list.curselection()
            if not selection:
                messagebox.showinfo("Seleccioná una empresa", "Elegí la empresa que querés renombrar.", parent=window)
                return
            company = self.company_config.companies[selection[0]]
            name = simpledialog.askstring("Renombrar empresa", "Nuevo nombre:", initialvalue=company.name, parent=window)
            if name is None:
                return
            try:
                self.company_repository.rename(company.id, name)
                refresh_list(company.id)
            except ValueError as exc:
                messagebox.showerror("No se pudo renombrar", str(exc), parent=window)

        buttons = ttk.Frame(frame)
        buttons.pack(fill="x", pady=(10, 0))
        ttk.Button(buttons, text="Agregar", style="Primary.TButton", command=add_company).pack(side="left")
        ttk.Button(buttons, text="Renombrar", style="Secondary.TButton", command=rename_company).pack(side="left", padx=8)
        ttk.Button(buttons, text="Cerrar", style="Secondary.TButton", command=window.destroy).pack(side="right")
        refresh_list()

    def _select_files(self) -> None:
        selected = filedialog.askopenfilenames(
            title="Seleccionar reportes de Mercado Pago",
            filetypes=[
                ("Reportes de Mercado Pago", "*.xlsx *.xls *.csv"),
                ("Excel moderno", "*.xlsx"),
                ("Excel 97-2003", "*.xls"),
                ("CSV", "*.csv"),
            ],
        )
        if not selected:
            return
        candidate_files = list(self.selected_files)
        for name in selected:
            path = Path(name)
            if path not in candidate_files:
                candidate_files.append(path)
        if not self._confirm_company_for_files(candidate_files):
            return
        self.selected_files = candidate_files
        self._refresh_file_list()
        self._start_analysis()

    def _refresh_file_list(self) -> None:
        self.file_list.delete(0, tk.END)
        for path in self.selected_files:
            self.file_list.insert(tk.END, str(path))
        self.analyze_button.configure(state="normal" if self.selected_files else "disabled")

    def _clear_selection(self) -> None:
        self.selected_files.clear()
        self.current_result = None
        self.last_export_path = None
        self.analysis_blocked_reason = None
        self._validated_selection_key = None
        self._refresh_file_list()
        self._clear_tables()
        for key, variable in self.summary_vars.items():
            variable.set("$ 0,00" if key == "net" else "0")
        self.export_button.configure(state="disabled")
        self.confirm_button.configure(state="disabled")
        self.status_var.set("Seleccioná uno o varios reportes de Mercado Pago.")
        self.analysis_progress_var.set(0)
        self.analysis_progress_message_var.set("Listo para analizar")

    def _start_analysis(self) -> None:
        if not self.selected_files:
            return
        if not self._confirm_company_for_files(self.selected_files):
            return
        self.status_var.set("Analizando archivos...")
        self.analyze_button.configure(state="disabled")
        self.export_button.configure(state="disabled")
        self.confirm_button.configure(state="disabled")
        self.last_export_path = None
        self.analysis_progress_var.set(0)
        self.analysis_progress_message_var.set("Preparando análisis...")
        files = list(self.selected_files)
        mode = self.mode_var.get()
        threading.Thread(target=self._analyze_worker, args=(files, mode), daemon=True).start()

    def _analyze_worker(self, files: list[Path], mode: str) -> None:
        try:
            result = self.service.analyze(files, mode, progress=self._queue_analysis_progress)
        except Exception as exc:
            self.root.after(0, lambda: self._analysis_failed(exc))
            return
        self.root.after(0, lambda: self._show_analysis(result))

    def _queue_analysis_progress(self, value: int, message: str) -> None:
        self.root.after(0, lambda: self._set_analysis_progress(value, message))

    def _set_analysis_progress(self, value: int, message: str) -> None:
        self.analysis_progress_var.set(max(0, min(100, value)))
        self.analysis_progress_message_var.set(message)

    def _analysis_failed(self, error: Exception) -> None:
        self.analyze_button.configure(state="normal")
        self.status_var.set("No se pudo completar el análisis.")
        self.analysis_progress_message_var.set("El análisis no pudo completarse")
        messagebox.showerror("Error al analizar", str(error))

    def _clear_tables(self) -> None:
        self.preview.delete(*self.preview.get_children())
        self.issues.delete(*self.issues.get_children())

    def _show_analysis(self, result: AnalysisResult) -> None:
        period = classify_period(item.date for item in result.unique_movements)
        self.analysis_blocked_reason = period.error
        if period.error:
            result = replace(
                result,
                issues=[*result.issues, ParseIssue("Selección", 0, period.error)],
            )
            if result.unique_movements:
                messagebox.showerror("Período no válido", period.error, parent=self.root)
        elif period.mode is not None and period.mode != result.mode:
            change = messagebox.askyesno(
                "Tipo de reporte detectado",
                f"Por las fechas, el archivo parece ser {period.mode}, pero elegiste {result.mode}.\n\n"
                f"¿Querés cambiarlo a {period.mode}?\n"
                f"Si elegís No, se mantendrá {result.mode} bajo tu confirmación.",
                parent=self.root,
            )
            if change:
                self.mode_var.set(period.mode)
                result = replace(result, mode=period.mode)

        self.current_result = result
        self._set_analysis_progress(100, "Análisis completado")
        self._clear_tables()
        self.summary_vars["rows"].set(f"{result.total_rows:,}".replace(",", "."))
        self.summary_vars["new"].set(f"{len(result.new_movements):,}".replace(",", "."))
        self.summary_vars["imported"].set(f"{len(result.already_imported):,}".replace(",", "."))
        self.summary_vars["review"].set(f"{len(result.issues):,}".replace(",", "."))
        self.summary_vars["duplicates"].set(f"{result.duplicate_count:,}".replace(",", "."))
        self.summary_vars["net"].set(format_currency(result.net_total))

        for movement in result.new_movements[:2000]:
            tag = "positive" if movement.amount > 0 else "negative"
            self.preview.insert(
                "",
                "end",
                values=(movement.date.strftime("%d-%m-%Y"), movement.concept, movement.receipt, format_currency(movement.amount), movement.source_file),
                tags=(tag,),
            )
        for issue in result.issues[:2000]:
            self.issues.insert("", "end", values=(issue.source_file, issue.row_number, issue.message))

        self.analyze_button.configure(state="normal")
        can_export = bool(result.new_movements) and self.analysis_blocked_reason is None
        self.export_button.configure(state="normal" if can_export else "disabled")
        if self.analysis_blocked_reason:
            self.status_var.set(f"Revisá el período: {self.analysis_blocked_reason}")
        else:
            self.status_var.set(
                f"Análisis listo: {len(result.new_movements)} movimientos nuevos."
                if result.new_movements
                else "No hay movimientos nuevos para importar."
            )

    def _export(self) -> None:
        result = self.current_result
        if result is None or not result.new_movements:
            messagebox.showinfo("Sin movimientos", "No hay movimientos nuevos para exportar.")
            return
        if self.analysis_blocked_reason:
            messagebox.showerror("Revisión pendiente", self.analysis_blocked_reason, parent=self.root)
            return
        start = min(item.date for item in result.unique_movements)
        end = max(item.date for item in result.unique_movements)
        company = require_selected_company(self.company_config)
        output = self.company_paths.outputs / output_filename(company.name, result.mode, start, end)
        try:
            export_colppy_csv(result.new_movements, output)
        except Exception as exc:
            messagebox.showerror("No se pudo exportar", str(exc))
            return
        self.last_export_path = output
        self.confirm_button.configure(state="normal")
        self.status_var.set(f"Archivo generado: {output.name}")
        messagebox.showinfo(
            "Archivo generado",
            f"Se generó:\n{output}\n\nImportalo en Colppy. Cuando Colppy confirme la carga, volvé y presioná Confirmar importación.",
        )

    def _confirm_import(self) -> None:
        result = self.current_result
        if result is None or self.last_export_path is None:
            return
        approved = messagebox.askyesno(
            "Confirmar importación",
            "¿Colppy confirmó correctamente la importación?\n\nSolo presioná Sí si la carga terminó bien. Esto agregará los movimientos al historial local.",
            icon="warning",
        )
        if not approved:
            return
        try:
            batch_id = self.service.confirm_import(result, self.last_export_path)
        except Exception as exc:
            messagebox.showerror("No se pudo confirmar", str(exc))
            return
        self.confirm_button.configure(state="disabled")
        self.export_button.configure(state="disabled")
        self.status_var.set(f"Importación confirmada en el lote {batch_id}.")
        messagebox.showinfo("Historial actualizado", f"Se guardaron {len(result.new_movements)} movimientos en el historial.")
        self._start_analysis()

    def _backup_history(self) -> None:
        try:
            destination = self.history.backup()
        except Exception as exc:
            messagebox.showerror("No se pudo respaldar", str(exc))
            return
        self.status_var.set(f"Respaldo creado: {destination.name}")
        messagebox.showinfo("Respaldo creado", str(destination))

    def _open_outputs(self) -> None:
        try:
            if os.name == "nt":
                os.startfile(self.company_paths.outputs)  # type: ignore[attr-defined]
            elif sys.platform == "darwin":
                subprocess.Popen(["open", str(self.company_paths.outputs)])
            else:
                subprocess.Popen(["xdg-open", str(self.company_paths.outputs)])
        except Exception as exc:
            messagebox.showerror("No se pudo abrir la carpeta", str(exc))


def main() -> None:
    root = tk.Tk()
    apply_window_icon(root)
    splash = StartupSplash(root)
    try:
        MercadoPagoColppyApp(root, startup_progress=splash.update)
    except Exception as exc:
        splash.close()
        messagebox.showerror("No se pudo iniciar", str(exc), parent=root)
        root.destroy()
        return
    splash.close()
    root.mainloop()
