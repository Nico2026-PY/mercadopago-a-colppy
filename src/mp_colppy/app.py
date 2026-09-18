from __future__ import annotations

from datetime import date
from decimal import Decimal
import os
from pathlib import Path
import subprocess
import sys
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, ttk
from typing import Callable

from .companies import Company, CompanyConfig, CompanyConfigRepository
from .excel_io import export_colppy_csv, export_colppy_xls, export_colppy_xlsx
from .history import HistoryRepository
from .paths import AppPaths, resolve_app_paths
from .service import AnalysisResult, ImportService


def format_currency(value: Decimal) -> str:
    negative = value < 0
    absolute = abs(value)
    raw = f"{absolute:,.2f}"
    localized = raw.replace(",", "_").replace(".", ",").replace("_", ".")
    return f"{'-' if negative else ''}$ {localized}"


def suggested_filename(mode: str, start: date, end: date, extension: str) -> str:
    suffix = extension if extension.startswith(".") else f".{extension}"
    return f"Colppy_MP_{mode}_{start.isoformat()}_a_{end.isoformat()}{suffix}"


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
        root.title("Iniciando Mercado Pago a Colppy")
        root.geometry("560x300")
        root.configure(bg="#17365D")
        self.frame = tk.Frame(root, bg="#17365D")
        self.frame.place(relx=0, rely=0, relwidth=1, relheight=1)
        tk.Label(
            self.frame,
            text="Mercado Pago a Colppy",
            bg="#17365D",
            fg="#FFFFFF",
            font=("Segoe UI", 21, "bold"),
        ).pack(pady=(70, 8))
        tk.Label(
            self.frame,
            text="Preparando la aplicación",
            bg="#17365D",
            fg="#DCE8F2",
            font=("Segoe UI", 10),
        ).pack()
        self.value = tk.DoubleVar(value=0)
        self.message = tk.StringVar(value="Iniciando...")
        ttk.Progressbar(self.frame, variable=self.value, maximum=100, length=410).pack(pady=(32, 10))
        tk.Label(
            self.frame,
            textvariable=self.message,
            bg="#17365D",
            fg="#FFFFFF",
            font=("Segoe UI", 9),
        ).pack()
        self.frame.lift()
        root.update_idletasks()

    def update(self, value: int, message: str) -> None:
        self.value.set(max(0, min(100, value)))
        self.message.set(message)
        self.frame.lift()
        self.root.update_idletasks()

    def close(self) -> None:
        self.frame.destroy()


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
        self.root.geometry("1180x760")
        self.root.minsize(980, 650)
        self.root.configure(bg=self.COLORS["white"])

    def _configure_style(self) -> None:
        style = ttk.Style(self.root)
        style.theme_use("clam")
        style.configure("TFrame", background=self.COLORS["white"])
        style.configure("TLabel", background=self.COLORS["white"], foreground=self.COLORS["text"], font=("Segoe UI", 10))
        style.configure("Header.TLabel", font=("Segoe UI", 18, "bold"), foreground=self.COLORS["white"], background=self.COLORS["navy"])
        style.configure("HeaderSub.TLabel", font=("Segoe UI", 10), foreground="#DCE8F2", background=self.COLORS["navy"])
        style.configure("Section.TLabel", font=("Segoe UI", 11, "bold"), foreground=self.COLORS["navy"])
        style.configure("Kpi.TLabel", font=("Segoe UI", 17, "bold"), foreground=self.COLORS["navy"], background=self.COLORS["light"])
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
        header = tk.Frame(self.root, bg=self.COLORS["navy"], height=86)
        header.pack(fill="x")
        header.pack_propagate(False)
        ttk.Label(header, text="Mercado Pago a Colppy", style="Header.TLabel").pack(anchor="w", padx=24, pady=(15, 1))
        ttk.Label(header, text="Seleccioná reportes, revisá los movimientos nuevos y exportá sin duplicados.", style="HeaderSub.TLabel").pack(anchor="w", padx=24)

        body = ttk.Frame(self.root, padding=18)
        body.pack(fill="both", expand=True)

        controls = ttk.Frame(body)
        controls.pack(fill="x")
        ttk.Label(controls, text="Empresa", style="Section.TLabel").pack(side="left", padx=(0, 8))
        self.company_combo = ttk.Combobox(
            controls,
            textvariable=self.company_var,
            values=company_names(self.company_config),
            state="readonly",
            width=22,
        )
        self.company_combo.pack(side="left")
        self.company_combo.bind("<<ComboboxSelected>>", self._on_company_selected)
        ttk.Button(controls, text="Empresas...", style="Secondary.TButton", command=self._manage_companies).pack(side="left", padx=(6, 18))
        ttk.Label(controls, text="Tipo de reporte", style="Section.TLabel").pack(side="left", padx=(0, 12))
        ttk.Radiobutton(controls, text="Diario", variable=self.mode_var, value="Diario").pack(side="left")
        ttk.Radiobutton(controls, text="Mensual", variable=self.mode_var, value="Mensual").pack(side="left", padx=(6, 18))
        ttk.Button(controls, text="Seleccionar Excel", style="Primary.TButton", command=self._select_files).pack(side="left")
        self.analyze_button = ttk.Button(controls, text="Analizar", style="Secondary.TButton", command=self._start_analysis, state="disabled")
        self.analyze_button.pack(side="left", padx=8)
        ttk.Button(controls, text="Limpiar", style="Secondary.TButton", command=self._clear_selection).pack(side="left")
        ttk.Button(controls, text="Abrir salidas", style="Secondary.TButton", command=self._open_outputs).pack(side="right")

        file_frame = ttk.Frame(body)
        file_frame.pack(fill="x", pady=(14, 10))
        ttk.Label(file_frame, text="Archivos seleccionados", style="Section.TLabel").pack(anchor="w", pady=(0, 5))
        self.file_list = tk.Listbox(file_frame, height=3, font=("Segoe UI", 9), relief="solid", borderwidth=1, highlightthickness=0, selectmode="extended")
        self.file_list.pack(fill="x")

        progress_frame = ttk.Frame(body)
        progress_frame.pack(fill="x", pady=(0, 10))
        ttk.Progressbar(progress_frame, variable=self.analysis_progress_var, maximum=100).pack(side="left", fill="x", expand=True)
        ttk.Label(progress_frame, textvariable=self.analysis_progress_message_var, foreground=self.COLORS["muted"]).pack(side="left", padx=(10, 0))

        kpis = ttk.Frame(body)
        kpis.pack(fill="x", pady=(0, 12))
        kpi_definitions = [
            ("Filas leídas", "rows"),
            ("Nuevos", "new"),
            ("Ya importados", "imported"),
            ("Para revisar", "review"),
            ("Duplicados", "duplicates"),
            ("Neto nuevo", "net"),
        ]
        for index, (label, key) in enumerate(kpi_definitions):
            card = tk.Frame(kpis, bg=self.COLORS["light"], highlightbackground=self.COLORS["border"], highlightthickness=1, padx=13, pady=8)
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
        actions.pack(fill="x", pady=(12, 0))
        self.export_button = ttk.Button(actions, text="Exportar para Colppy", style="Primary.TButton", command=self._export, state="disabled")
        self.export_button.pack(side="left")
        self.confirm_button = ttk.Button(actions, text="Confirmar importación", style="Secondary.TButton", command=self._confirm_import, state="disabled")
        self.confirm_button.pack(side="left", padx=8)
        ttk.Button(actions, text="Respaldar historial", style="Secondary.TButton", command=self._backup_history).pack(side="left")
        ttk.Label(actions, textvariable=self.status_var, foreground=self.COLORS["muted"]).pack(side="right")

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
            self.company_config = self.company_repository.select(company_id)
            selected = require_selected_company(self.company_config)
            self.company_paths = self.paths.for_company(selected.id)
            self.history = HistoryRepository(self.company_paths.database, self.company_paths.backups)
            self.service = ImportService(self.history)
            self._clear_selection()
            self.status_var.set(f"Empresa activa: {selected.name}")
        except Exception as exc:
            messagebox.showerror("No se pudo cambiar de empresa", str(exc), parent=self.root)
            self._refresh_company_selector()

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
            filetypes=[("Excel de Mercado Pago", "*.xlsx"), ("Todos los archivos", "*.*")],
        )
        if not selected:
            return
        for name in selected:
            path = Path(name)
            if path not in self.selected_files:
                self.selected_files.append(path)
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
        self._refresh_file_list()
        self._clear_tables()
        for key, variable in self.summary_vars.items():
            variable.set("$ 0,00" if key == "net" else "0")
        self.export_button.configure(state="disabled")
        self.confirm_button.configure(state="disabled")
        self.status_var.set("Seleccioná uno o varios reportes de Mercado Pago.")

    def _start_analysis(self) -> None:
        if not self.selected_files:
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
        self.export_button.configure(state="normal" if result.new_movements else "disabled")
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
        start = min(item.date for item in result.new_movements)
        end = max(item.date for item in result.new_movements)
        default_name = suggested_filename(result.mode, start, end, ".csv")
        output_name = filedialog.asksaveasfilename(
            title="Guardar archivo para Colppy",
            initialdir=self.company_paths.outputs,
            initialfile=default_name,
            defaultextension=".csv",
            filetypes=[
                ("CSV oficial de Colppy", "*.csv"),
                ("Excel moderno", "*.xlsx"),
                ("Excel 97-2003", "*.xls"),
            ],
        )
        if not output_name:
            return
        output = Path(output_name)
        try:
            if output.suffix.lower() == ".csv":
                export_colppy_csv(result.new_movements, output)
            elif output.suffix.lower() == ".xls":
                export_colppy_xls(result.new_movements, output)
            else:
                if output.suffix.lower() != ".xlsx":
                    output = output.with_suffix(".xlsx")
                export_colppy_xlsx(result.new_movements, output)
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
