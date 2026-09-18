# GitHub Launcher and Local Companies Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Publicar una aplicación Windows portable que exporte el CSV oficial de Colppy, separe historiales por empresas configuradas localmente, muestre progreso y avise nuevas versiones desde GitHub Releases.

**Architecture:** `CompanyConfigRepository` administra configuración local con escritura atómica; `CompanyContext` resuelve carpetas e historial por identificador estable. El lector y la aplicación informan progreso mediante callbacks. Un launcher independiente consulta la API pública de Releases y siempre permite abrir la aplicación instalada.

**Tech Stack:** Python 3.12–3.14, Tkinter, SQLite, openpyxl, xlwt, PyInstaller 6, unittest, GitHub Actions.

**Spec:** `docs/superpowers/specs/2026-09-18-github-launcher-companies-design.md`

## Global Constraints

- El repositorio público es `Nico2026-PY/mercadopago-a-colppy`.
- Ningún nombre real de empresa, reporte, base SQLite, salida Colppy o configuración local puede quedar rastreado por Git ni empaquetado en un Release.
- Cada PC conserva historiales independientes.
- La exportación predeterminada replica CSV Windows-1252, punto y coma y CRLF del archivo oficial.
- El launcher solamente avisa y abre el Release; nunca instala ni exige credenciales.
- El chequeo de actualización nunca bloquea el inicio sin conexión.

---

### Task 1: CSV oficial de Colppy

**Files:**
- Modify: `src/mp_colppy/excel_io.py`
- Modify: `src/mp_colppy/app.py`
- Modify: `tests/test_excel_io.py`

**Interfaces:**
- Produces: `export_colppy_csv(movements: Iterable[Movement], output_path: str | Path) -> Path`.
- Preserves: `export_colppy_xlsx` and `export_colppy_xls`.

- [ ] **Step 1: Write the failing test**

Create a synthetic movement and assert the exact bytes start with the approved Windows-1252 instruction/header rows, use `;`, `\r\n`, `1/9/2026`, and `1234,50` without a thousands separator.

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m unittest tests.test_excel_io.ExcelExportTests.test_exports_official_colppy_csv_bytes -v`

Expected: FAIL because `export_colppy_csv` does not exist.

- [ ] **Step 3: Implement minimal export**

Use `csv.writer(..., delimiter=";", lineterminator="\r\n")`, `encoding="cp1252"`, date components without fixed zero padding, and `format(amount, ".2f").replace(".", ",")`.

- [ ] **Step 4: Make CSV the default UI choice**

Offer CSV, XLSX and XLS in the save dialog, with CSV selected by the suggested filename and routed to the matching exporter.

- [ ] **Step 5: Run tests**

Run: `python -m unittest tests.test_excel_io tests.test_app_helpers -v`

Expected: PASS.

### Task 2: Configuración local de empresas

**Files:**
- Create: `src/mp_colppy/companies.py`
- Create: `tests/test_companies.py`
- Modify: `src/mp_colppy/paths.py`
- Modify: `tests/test_paths.py`

**Interfaces:**
- Produces: `Company(id: str, name: str)`.
- Produces: `CompanyConfig(companies: tuple[Company, ...], selected_company_id: str | None)`.
- Produces: `CompanyConfigRepository.load()`, `.add(name)`, `.rename(company_id, name)`, `.select(company_id)`.
- Produces: `AppPaths.for_company(company_id: str) -> CompanyPaths`.

- [ ] **Step 1: Write failing configuration tests**

Cover empty first load, trimmed unique names, case-insensitive duplicate rejection, stable generated IDs, rename preserving ID, selection persistence and malformed JSON recovery error.

- [ ] **Step 2: Verify RED**

Run: `python -m unittest tests.test_companies -v`

Expected: import failure for the missing module.

- [ ] **Step 3: Implement atomic repository**

Write JSON to `config.json.tmp`, flush and `os.replace`. Validate schema before returning it. Never include default company names.

- [ ] **Step 4: Write failing path-isolation tests**

Assert two company IDs resolve distinct `historial.db`, output and backup paths beneath their allowed roots.

- [ ] **Step 5: Implement company paths and verify**

Run: `python -m unittest tests.test_companies tests.test_paths -v`

Expected: PASS.

### Task 3: Selector y administración de empresas

**Files:**
- Modify: `src/mp_colppy/app.py`
- Create: `tests/test_app_company_helpers.py`

**Interfaces:**
- Consumes: `CompanyConfigRepository`, `AppPaths.for_company`.
- Produces: `switch_company(company_id: str)` behavior that rebuilds `HistoryRepository` and clears transient analysis state.

- [ ] **Step 1: Write failing helper tests**

Extract and test pure validation/mapping helpers for selector labels and required-company state. Assert switching clears selected files, current result and last export.

- [ ] **Step 2: Verify RED**

Run: `python -m unittest tests.test_app_company_helpers -v`

Expected: missing helpers.

- [ ] **Step 3: Implement first-run dialog and selector**

Require a company before analysis, add `Administrar empresas`, allow add/rename, and never expose delete in this version.

- [ ] **Step 4: Implement switching and company-specific output**

On selection, create a repository for that ID and clear preview/state. Save exports under the selected company's output directory.

- [ ] **Step 5: Verify**

Run: `python -m unittest tests.test_app_company_helpers tests.test_service tests.test_history -v`

Expected: PASS.

### Task 4: Progreso de inicio y análisis

**Files:**
- Modify: `src/mp_colppy/excel_io.py`
- Modify: `src/mp_colppy/service.py`
- Modify: `src/mp_colppy/app.py`
- Modify: `main.py`
- Create: `tests/test_progress.py`

**Interfaces:**
- Produces: `ProgressCallback = Callable[[int, str], None]`.
- Extends: `read_mercadopago_files(paths, progress=None)` and `ImportService.analyze(paths, mode, progress=None)`.
- Produces: startup phase sequence ending exactly at 100.

- [ ] **Step 1: Write failing monotonic-progress tests**

Capture callback values while reading synthetic workbooks. Assert first value is at least 0, values never decrease, no value exceeds 100 and the final value is 100.

- [ ] **Step 2: Verify RED**

Run: `python -m unittest tests.test_progress -v`

Expected: current signatures reject `progress`.

- [ ] **Step 3: Implement reader/service progress**

Estimate work from worksheet row counts, report at bounded intervals, and force 100 after all files close. Keep callbacks optional.

- [ ] **Step 4: Implement Tkinter progress UI**

Add a startup splash and a main progress bar. Send worker callbacks through `root.after`; close splash on success or error. Do not sleep to simulate work.

- [ ] **Step 5: Verify**

Run: `python -m unittest tests.test_progress tests.test_excel_io tests.test_service -v`

Expected: PASS.

### Task 5: Versión y launcher de Releases

**Files:**
- Create: `src/mp_colppy/version.py`
- Create: `src/mp_colppy/updater.py`
- Create: `launcher.py`
- Create: `tests/test_updater.py`
- Create: `version.json`

**Interfaces:**
- Produces: `parse_version(value: str) -> tuple[int, ...]`.
- Produces: `ReleaseInfo(version: str, html_url: str)`.
- Produces: `fetch_latest_release(url: str, timeout: float = 4.0) -> ReleaseInfo | None`.
- Produces: `is_newer(installed: str, available: str) -> bool`.

- [ ] **Step 1: Write failing version tests**

Cover `v1.2.0`, equal versions, older versions, invalid tags, a valid GitHub JSON response, timeout and malformed JSON.

- [ ] **Step 2: Verify RED**

Run: `python -m unittest tests.test_updater -v`

Expected: missing module.

- [ ] **Step 3: Implement updater boundary**

Use only `urllib.request`, HTTPS, explicit User-Agent and timeout. Convert all network/parse failures to `None` so startup continues.

- [ ] **Step 4: Implement launcher UI**

Read adjacent `version.json`, check latest Release, offer `Abrir descarga` and `Continuar`, then start adjacent `MercadoPagoColppy.exe`. If the check fails, start immediately.

- [ ] **Step 5: Verify**

Run: `python -m unittest tests.test_updater -v`

Expected: PASS.

### Task 6: Build, Release y barreras de privacidad

**Files:**
- Create: `MercadoPagoColppyLauncher.spec`
- Modify: `MercadoPagoColppy.spec`
- Modify: `.github/workflows/build-windows.yml`
- Modify: `scripts/package_portable.ps1`
- Modify: `CREAR_PORTABLE.bat`
- Modify: `.gitignore`
- Create: `tests/test_release_contract.py`
- Modify: `README.md`
- Modify: `ENTREGA.txt`

**Interfaces:**
- Produces: `release/MercadoPagoColppy-Windows.zip` containing only launcher, app, version and readme.
- Produces: `release/SHA256SUMS.txt`.

- [ ] **Step 1: Write failing release-contract tests**

Assert `version.json` matches `src.mp_colppy.version.__version__`, `.gitignore` covers local roots and sensitive extensions, both spec files exist, and the workflow has `contents: write`, tag trigger, tests, build, package and Release commands.

- [ ] **Step 2: Verify RED**

Run: `python -m unittest tests.test_release_contract -v`

Expected: missing launcher spec or version mismatch.

- [ ] **Step 3: Implement two-executable build and clean packaging**

Compile both specs. Make PowerShell create a staging directory from an explicit allowlist, archive it, generate SHA-256 and fail if forbidden extensions or directories appear.

- [ ] **Step 4: Implement GitHub Actions Release**

Use Python 3.14 on `windows-latest`, run tests, build, package, and use `gh release create`/`gh release upload` with `GITHUB_TOKEN` for `v*` tags. On manual runs, upload the portable as a workflow artifact without creating an untagged Release.

- [ ] **Step 5: Document first install and update flow**

Explain that users download the latest ZIP, extract it outside `Archivos de programa`, always open the launcher, configure companies locally and retain `datos`, `salidas` and `respaldos` during manual updates.

- [ ] **Step 6: Verify**

Run: `python -m unittest tests.test_release_contract tests.test_scripts -v`

Expected: PASS.

### Task 7: Integración, privacidad y publicación

**Files:**
- Modify as required by failing integration checks only.

- [ ] **Step 1: Run the full suite**

Run: `python -m unittest discover -s tests -v`

Expected: all tests PASS with no ResourceWarnings.

- [ ] **Step 2: Validate real reports locally**

Run `scripts/validate_real_files.py` against the five uploaded Mercado Pago workbooks and confirm valid counts remain unchanged. Do not copy their paths or results into public fixtures.

- [ ] **Step 3: Inspect repository privacy**

Run `git status --short`, `git ls-files`, and a forbidden-extension/name scan. Confirm no `.db`, `.xlsx`, `.xls`, imported `.csv`, local `config.json`, actual company names or uploaded paths are tracked.

- [ ] **Step 4: Initialize and commit the public repository state**

Configure `origin` as `https://github.com/Nico2026-PY/mercadopago-a-colppy.git`, create descriptive commits, and push `main` without force. The workflow creates the version tag and release automatically when that version is not already published.

- [ ] **Step 5: Trigger Windows verification**

Run the workflow manually or push a release tag only after the repository is visible and the clean suite passes. Inspect the Windows job and downloadable artifact.

- [ ] **Step 6: Publish the first Release**

Create an annotated semantic-version tag, push it, verify the Release assets and checksum, then report the GitHub URL and installation steps.
