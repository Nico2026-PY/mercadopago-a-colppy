# Mercado Pago a Colppy

Aplicación portable para convertir reportes de Mercado Pago al formato oficial de importación bancaria de Colppy y evitar duplicados entre archivos diarios y cierres mensuales.

## Uso

1. Descargá y abrí `Launcher.exe`. En el primer inicio descarga e instala automáticamente la aplicación.
2. En el primer inicio, agregá localmente las empresas que vas a administrar.
3. Elegí la empresa y seleccioná `Diario` o `Mensual`.
4. Presioná **Seleccionar archivos** y elegí uno o varios reportes `.csv`, `.xls` o `.xlsx`.
5. Revisá los contadores, la vista previa y la pestaña de errores.
6. Presioná **Exportar para Colppy**. La app genera automáticamente el CSV oficial dentro de la carpeta de salidas de esa empresa.
7. Importá el archivo generado en Colppy.
8. Cuando Colppy confirme correctamente la carga, volvé a la app y presioná **Confirmar importación**.

La confirmación es importante: recién en ese momento el movimiento queda guardado en el historial y deja de aparecer en futuros reportes diarios o mensuales.

La app compara los nombres de archivo con las empresas configuradas. Si detecta otra empresa, ofrece cambiarla; si el nombre no permite identificarla, pide confirmación. Nunca permite mezclar archivos de empresas diferentes. También revisa las fechas: un solo día se reconoce como diario, varios días del mismo mes como mensual y una selección que abarque meses distintos queda bloqueada para revisión.

Los archivos exportados se nombran así:

- Diario: `MP EMPRESA DIARIO DD-MM-AAAA.csv`
- Mensual: `MP EMPRESA MENSUAL MM-AAAA.csv`

El contenido usa exactamente la estructura del CSV de importación de Colppy: campos separados por punto y coma y decimales con coma.

El importe se toma de **VALOR DE LA COMPRA** (campo técnico `TRANSACTION_AMOUNT`), que es el valor original usado para conciliar. El concepto se arma solamente con tipo de operación, sucursal, pagador y CUIT/CUIL. El texto `Pago aprobado` se omite para evitar ruido; los demás tipos, como devoluciones, `PAYOUTS` y reclamos, sí se conservan.

## Datos locales

- `%LOCALAPPDATA%\MercadoPagoColppy\datos\config.json`: empresas configuradas solamente en esa PC.
- `%LOCALAPPDATA%\MercadoPagoColppy\datos\empresas\<id>\historial.db`: movimientos confirmados de cada empresa.
- `%LOCALAPPDATA%\MercadoPagoColppy\salidas\<id>\`: archivos generados para cada empresa.
- `%LOCALAPPDATA%\MercadoPagoColppy\respaldos\<id>\`: copias automáticas del historial de cada empresa.

El launcher mantiene estos datos fuera de las carpetas de cada versión, por lo que una actualización no reemplaza empresas, historiales, salidas ni respaldos.

## Cierre mensual

Seleccioná la empresa y su reporte mensual. La app compara las claves contra el historial de esa empresa y muestra como nuevos solamente los movimientos que todavía no fueron confirmados mediante los reportes diarios.

La clave combina ID, tipo de operación, fecha/hora e importe. Por eso un cobro y su devolución pueden compartir el ID de Mercado Pago sin eliminarse entre sí.

## Generar el ejecutable

### Opción 1: Windows

Con Python 3.12, 3.13 o 3.14 instalado, hacé doble clic en `CREAR_PORTABLE.bat`. El botón detecta automáticamente la versión disponible. Al terminar encontrarás:

- `release\Launcher.exe`: único archivo que se entrega al usuario.
- `release\MercadoPagoColppy-Windows.zip`: paquete descargado automáticamente por el launcher.
- `release\SHA256SUMS.txt`: verificación de integridad del paquete.

### Opción 2: GitHub

Cada actualización de `main` ejecuta las pruebas y genera el release. Si todavía no existe el release correspondiente a `version.json`, el workflow crea automáticamente el tag (por ejemplo, `v1.0.2`) y publica `Launcher.exe`, el paquete interno y su checksum SHA-256. También se puede ejecutar manualmente desde **Actions > Construir portable Windows > Run workflow**.

## Actualizaciones

El launcher muestra una pantalla de inicio mientras consulta el último GitHub Release. En el primer uso descarga, verifica e instala la aplicación. Si luego encuentra una versión más nueva, ofrece instalarla automáticamente. Sin Internet, abre normalmente la versión ya instalada. Nunca sube la configuración, los reportes ni los historiales locales.

## Desarrollo

```powershell
py -3.14 -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
python main.py
```
