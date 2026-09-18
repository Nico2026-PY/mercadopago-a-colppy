# Mercado Pago a Colppy Portable Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Construir una aplicación portable de Windows que transforme reportes de Mercado Pago, evite duplicados mediante historial local y exporte el formato Colppy.

**Architecture:** Núcleo desacoplado de la interfaz: lectura/escritura Excel, reglas de dominio, historial SQLite y servicio de aplicación. Tkinter consume el servicio y PyInstaller produce el portable.

**Tech Stack:** Python 3.12, Tkinter, sqlite3, openpyxl, xlwt, PyInstaller, unittest.

**Spec:** `docs/superpowers/specs/2026-09-17-mercadopago-colppy-portable-design.md`

## Global Constraints

- Debe funcionar en Windows 10/11 de 64 bits sin instalación ni permisos administrativos.
- El historial se guarda fuera del ejecutable, en `datos/historial.db`.
- No confirmar movimientos automáticamente al exportar.
- La clave es ID + tipo + fecha/hora original + importe neto a dos decimales.
- La salida conserva las dos filas del modelo Colppy.
- La aplicación debe procesar archivos `.xlsx` de Mercado Pago con encabezados visibles en español o códigos técnicos conocidos.

---

### Task 1: Reglas de dominio y lectura Excel

**Files:**
- Create: `tests/test_domain.py`
- Create: `tests/test_excel_io.py`
- Create: `src/mp_colppy/domain.py`
- Create: `src/mp_colppy/excel_io.py`
- Create: `src/mp_colppy/__init__.py`

**Interfaces:**
- Produces: `Movement`, `ParseIssue`, `normalize_row(row, source_file)`, `read_mercadopago_files(paths)`.

- [ ] Escribir pruebas que exijan clave compuesta, sufijos de comprobante, concepto sin vacíos y lectura de encabezados españoles.
- [ ] Ejecutar `python -m unittest tests.test_domain tests.test_excel_io -v` y comprobar que falla porque faltan los módulos.
- [ ] Implementar modelos, alias de columnas, parseo de fecha/importe y lectura con openpyxl.
- [ ] Repetir las pruebas hasta obtener cero fallos.

### Task 2: Historial SQLite y servicio

**Files:**
- Create: `tests/test_history.py`
- Create: `tests/test_service.py`
- Create: `src/mp_colppy/history.py`
- Create: `src/mp_colppy/service.py`

**Interfaces:**
- Consumes: `Movement`, `read_mercadopago_files`.
- Produces: `HistoryRepository`, `AnalysisResult`, `ImportService.analyze`, `ImportService.confirm_import`.

- [ ] Escribir pruebas para crear la base, confirmar lotes, excluir claves importadas y deduplicar selecciones.
- [ ] Ejecutar las pruebas y confirmar fallos por funciones faltantes.
- [ ] Implementar el esquema SQLite, respaldos, análisis y confirmación transaccional.
- [ ] Ejecutar todas las pruebas y corregir únicamente la implementación.

### Task 3: Exportación Colppy

**Files:**
- Modify: `tests/test_excel_io.py`
- Modify: `src/mp_colppy/excel_io.py`

**Interfaces:**
- Consumes: secuencia de `Movement`.
- Produces: `export_colppy_xlsx(movements, path)` y `export_colppy_xls(movements, path)`.

- [ ] Añadir pruebas que verifiquen instrucciones, encabezados, fechas, importes negativos y orden cronológico.
- [ ] Ejecutar la prueba específica y observar el fallo esperado.
- [ ] Implementar exportación `.xlsx`; implementar `.xls` mediante `xlwt` con error claro si falta la dependencia.
- [ ] Ejecutar la suite completa.

### Task 4: Interfaz portable

**Files:**
- Create: `src/mp_colppy/paths.py`
- Create: `src/mp_colppy/app.py`
- Create: `main.py`
- Create: `tests/test_paths.py`

**Interfaces:**
- Consumes: `ImportService`, exportadores y rutas portables.
- Produces: ventana `MercadoPagoColppyApp` y `main()`.

- [ ] Escribir pruebas de rutas para ejecución fuente y modo congelado.
- [ ] Ejecutarlas y comprobar el fallo por módulo ausente.
- [ ] Implementar rutas, ventana, selección múltiple, resumen, vista previa, exportación y confirmación.
- [ ] Ejecutar pruebas e importar `src.mp_colppy.app` sin abrir una ventana.

### Task 5: Empaquetado Windows y documentación

**Files:**
- Create: `requirements.txt`
- Create: `MercadoPagoColppy.spec`
- Create: `CREAR_PORTABLE.bat`
- Create: `.github/workflows/build-windows.yml`
- Create: `README.md`
- Create: `scripts/validate_real_files.py`

**Interfaces:**
- Consumes: aplicación verificada.
- Produces: proceso reproducible que genera `MercadoPagoColppy.exe` y ZIP portable.

- [ ] Definir dependencias con versiones compatibles con Python 3.12.
- [ ] Crear configuración PyInstaller sin consola y con recursos necesarios.
- [ ] Crear script de un clic y workflow de Windows que ejecuten pruebas antes de compilar.
- [ ] Documentar uso, confirmación segura y ubicación del historial.
- [ ] Validar los cinco reportes reales con `scripts/validate_real_files.py`.

### Task 6: Verificación y entrega

**Files:**
- Create: `ENTREGA.txt`

**Interfaces:**
- Consumes: todo el proyecto.
- Produces: ZIP entregable y evidencia de verificación.

- [ ] Ejecutar `python -m unittest discover -s tests -v`.
- [ ] Ejecutar `python -m compileall -q src main.py`.
- [ ] Ejecutar la validación real y revisar conteos, errores y duplicados.
- [ ] Empaquetar el proyecto sin archivos temporales ni datos reales del usuario.
- [ ] Guardar el ZIP final y reportar la limitación: el `.exe` se genera en Windows con el BAT o workflow incluido.

