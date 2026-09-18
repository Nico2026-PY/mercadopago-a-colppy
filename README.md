# Mercado Pago a Colppy

Aplicación portable para convertir reportes de Mercado Pago al formato oficial de importación bancaria de Colppy y evitar duplicados entre archivos diarios y cierres mensuales.

## Uso

1. Abrí `MercadoPagoColppyLauncher.exe`.
2. En el primer inicio, agregá localmente las empresas que vas a administrar.
3. Elegí la empresa y seleccioná `Diario` o `Mensual`.
4. Presioná **Seleccionar Excel** y elegí uno o varios reportes `.xlsx`.
5. Revisá los contadores, la vista previa y la pestaña de errores.
6. Presioná **Exportar para Colppy**. La opción predeterminada genera el CSV oficial.
7. Importá el archivo generado en Colppy.
8. Cuando Colppy confirme correctamente la carga, volvé a la app y presioná **Confirmar importación**.

La confirmación es importante: recién en ese momento el movimiento queda guardado en el historial y deja de aparecer en futuros reportes diarios o mensuales.

## Carpetas portables

- `datos/config.json`: empresas configuradas solamente en esa PC.
- `datos/empresas/<id>/historial.db`: movimientos confirmados de cada empresa.
- `salidas/<id>/`: archivos generados para cada empresa.
- `respaldos/<id>/`: copias automáticas del historial de cada empresa.

Podés copiar la carpeta completa a otra computadora. Cada PC conserva su propia configuración e historial. No la ubiques dentro de `Archivos de programa`, porque Windows puede impedir que guarde el historial. Usá Escritorio, Documentos o una carpeta de trabajo.

## Cierre mensual

Seleccioná la empresa y su reporte mensual. La app compara las claves contra el historial de esa empresa y muestra como nuevos solamente los movimientos que todavía no fueron confirmados mediante los reportes diarios.

La clave combina ID, tipo de operación, fecha/hora e importe. Por eso un cobro y su devolución pueden compartir el ID de Mercado Pago sin eliminarse entre sí.

## Generar el ejecutable

### Opción 1: Windows

Con Python 3.12, 3.13 o 3.14 instalado, hacé doble clic en `CREAR_PORTABLE.bat`. El botón detecta automáticamente la versión disponible. Al terminar encontrarás:

`release\MercadoPagoColppy-Windows.zip`

### Opción 2: GitHub

Cada actualización de `main` ejecuta las pruebas y genera el portable. Si todavía no existe el release correspondiente a `version.json`, el workflow crea automáticamente el tag (por ejemplo, `v1.0.0`) y publica el ZIP junto con su checksum SHA-256. También se puede ejecutar manualmente desde **Actions > Construir portable Windows > Run workflow**.

## Actualizaciones

El launcher consulta el último GitHub Release. Si encuentra una versión más nueva, avisa y permite abrir la página de descarga. Sin Internet, abre normalmente la versión instalada. Nunca sube la configuración ni los historiales locales.

Al actualizar, reemplazá únicamente los ejecutables y `version.json`; conservá siempre las carpetas `datos`, `salidas` y `respaldos`.

## Desarrollo

```powershell
py -3.14 -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
python main.py
```
