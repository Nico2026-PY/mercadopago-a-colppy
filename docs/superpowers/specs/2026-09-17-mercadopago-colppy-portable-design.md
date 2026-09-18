# Mercado Pago a Colppy Portable — Diseño

## Objetivo

Crear una aplicación de escritorio portable para Windows que transforme uno o varios reportes de Mercado Pago al formato de importación bancaria de Colppy, recuerde los movimientos confirmados y evite duplicarlos cuando se alternan reportes diarios y cierres mensuales.

## Usuario y entorno

- Usuario principal: administración de Corralón Pitty.
- Sistema objetivo: Windows 10/11 de 64 bits.
- Uso: desde una carpeta copiable, sin instalación, Node ni permisos administrativos.
- Ubicación recomendada: Escritorio, Documentos o una carpeta de trabajo con permiso de escritura.

## Flujo

1. El usuario selecciona uno o varios archivos `.xlsx` descargados de Mercado Pago.
2. Indica `Diario` o `Mensual`; el procesamiento es idéntico, pero el modo queda registrado en el lote.
3. La app valida columnas, fechas, importes e identificadores.
4. Compara cada movimiento contra el historial local SQLite.
5. Muestra nuevos, ya importados, duplicados del archivo, filas para revisar, entradas, salidas y neto.
6. Exporta únicamente movimientos nuevos y válidos al formato Colppy.
7. El usuario importa el archivo en Colppy.
8. Recién después de la confirmación de Colppy, pulsa `Confirmar importación`; la app guarda las claves en el historial.

## Reglas de transformación

- Fecha: `FECHA DE ORIGEN`.
- Importe: `MONTO NETO DE LA OPERACIÓN QUE IMPACTÓ TU DINERO`.
- Comprobante: `ID DE OPERACIÓN EN MERCADO PAGO`, con sufijos `-DEV`, `-REC` o `-PAYOUT` según el tipo.
- Concepto: tipo de operación, pagador, banco, medio de pago y local; se omiten valores vacíos y se limita a 255 caracteres.
- Clave única: ID + tipo + fecha/hora original + importe neto con dos decimales.
- Tipos reconocidos: `Pago aprobado`, `PAYOUTS`, `Devolución de dinero`, `Reclamo`.
- Una clave exacta repetida entre archivos seleccionados se conserva una sola vez y se informa como duplicada.
- Un mismo ID con distinto tipo, fecha o importe representa movimientos diferentes.

## Salida Colppy

La exportación conserva las dos primeras filas del modelo recibido:

1. Indicaciones de obligatoriedad/formato.
2. Encabezados `Fecha`, `Concepto`, `Nro. Comprobante`, `Importe`.

Se ofrecerá `.xlsx` siempre y `.xls` cuando la dependencia `xlwt` esté instalada. El portable de Windows incluirá ambas dependencias.

## Historial

- Base: `datos/historial.db` junto al ejecutable.
- Tablas: lotes de importación y movimientos confirmados.
- Antes de confirmar un lote se crea una copia de seguridad en `respaldos/`.
- La app nunca marca movimientos como importados automáticamente al exportar.

## Interfaz

Ventana única, clara y apta para uso administrativo:

- selector de modo diario/mensual;
- botón para elegir varios Excel;
- lista de archivos seleccionados;
- tarjetas de resumen;
- tabla de vista previa;
- panel de errores/revisiones;
- botones `Exportar para Colppy`, `Confirmar importación` y `Respaldar historial`;
- barra de estado con mensajes directos.

## Arquitectura

- `domain.py`: normalización, reglas y modelos.
- `excel_io.py`: lectura de Mercado Pago y escritura Colppy.
- `history.py`: persistencia SQLite y respaldos.
- `service.py`: análisis, deduplicación y confirmación.
- `app.py`: interfaz Tkinter.
- `paths.py`: rutas portables.
- `main.py`: punto de entrada.

## Empaquetado

- `CREAR_PORTABLE.bat`: crea entorno, instala dependencias, ejecuta pruebas y genera el ejecutable con PyInstaller.
- GitHub Actions compila en Windows y publica un artefacto ZIP.
- El ZIP portable contiene el `.exe`, `datos`, `salidas`, `respaldos` y un instructivo.

## Verificación

- Pruebas unitarias con `unittest` para claves, comprobantes, concepto, validación, deduplicación, historial y exportación.
- Prueba integral con los cinco reportes reales de febrero a junio de 2026.
- Verificación de que los 13 ID repetidos por devolución/reclamo no se eliminen indebidamente.
- Importación del proyecto, compilación de bytecode y ejecución de pruebas sin interfaz gráfica.

