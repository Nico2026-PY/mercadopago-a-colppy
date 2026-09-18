# Mercado Pago a Colppy: empresas locales, launcher y GitHub Releases

## Objetivo

Convertir la aplicación portable existente en una aplicación distribuible desde un repositorio público de GitHub, con empresas configuradas únicamente en cada computadora, historiales separados por empresa, exportación compatible con el CSV oficial de Colppy, aviso de nuevas versiones y progreso visible durante el inicio y el análisis.

## Decisiones aprobadas

- El repositorio será público: `Nico2026-PY/mercadopago-a-colppy`.
- El código y los ejecutables no contendrán nombres reales de empresas ni datos operativos.
- Cada computadora conservará su propia configuración y sus propios historiales. No habrá sincronización entre computadoras.
- Los nombres de empresas se cargarán localmente la primera vez que se use la aplicación.
- El launcher solamente avisará que existe una versión nueva y ofrecerá abrir la página del Release. No instalará actualizaciones sin intervención del usuario.
- Los nombres de los archivos de Mercado Pago no determinarán la empresa, el período ni el modo. El usuario seleccionará la empresa y el modo antes de procesarlos.

## Datos locales y privacidad

La aplicación creará esta estructura junto a los ejecutables:

```text
datos/
  config.json
  empresas/
    <company-id>/
      historial.db
salidas/
  <company-id>/
respaldos/
  <company-id>/
```

`config.json` guardará una lista de objetos `{id, name}` y el identificador de la empresa seleccionada. El identificador será estable e independiente del nombre, para que renombrar una empresa no cambie su historial.

Los directorios `datos`, `salidas`, `respaldos`, entornos virtuales, bases SQLite, reportes de origen y archivos exportados quedarán excluidos de Git mediante `.gitignore`. El workflow de Release construirá los ejecutables desde un checkout limpio y empaquetará solamente archivos permitidos.

## Empresas

En el primer inicio, la aplicación mostrará un diálogo para crear al menos una empresa. La ventana principal tendrá un selector de empresa y una acción para administrar la lista local.

Al cambiar de empresa se limpiará la selección de reportes, la vista previa y el estado de exportación. Cada análisis consultará únicamente el historial SQLite de la empresa seleccionada. La aplicación no intentará deducir la empresa desde el nombre del archivo.

La eliminación de una empresa no formará parte de esta versión, para impedir pérdidas accidentales. Se permitirá agregar y renombrar empresas.

## Formato Colppy

El CSV entregado por el usuario define el contrato principal de exportación:

- Codificación: Windows-1252, compatible con el archivo de referencia.
- Separador: punto y coma.
- Terminación de línea: CRLF.
- Primera fila:
  - `Campo obligatorio                                               Formato dd-mm-aaaa`
  - `Campo obligatorio`
  - vacío
  - `Campo obligatorio                                               Numérico 2 (dos) decimales con valor negativo para los débitos`
- Segunda fila: `Fecha;Concepto;Nro. Comprobante;Importe`.
- Fecha: día/mes/año sin ceros obligatorios.
- Importe: dos decimales, coma decimal, sin separador de miles y signo negativo para débitos.

La exportación CSV será la opción predeterminada. Las exportaciones XLSX y XLS existentes permanecerán disponibles como alternativas. Las pruebas usarán datos sintéticos; el CSV real recibido no se copiará al repositorio.

## Progreso y experiencia de uso

La aplicación tendrá una pantalla de inicio compacta con el nombre del producto, mensaje de etapa y barra de 0 a 100 %. El progreso representará etapas reales: resolución de carpetas, lectura de configuración, preparación de historiales, creación de interfaz y finalización. No se agregará una demora artificial.

Durante el análisis de Excel, la ventana principal mostrará una barra determinada de 0 a 100 %. El lector informará progreso por archivo y por filas cuando el tamaño de la hoja esté disponible. La interfaz seguirá procesando en un hilo de trabajo y las actualizaciones visuales se enviarán al hilo de Tkinter.

Si una fase falla, la pantalla de carga se cerrará y se mostrará un error legible, sin dejar una ventana bloqueada.

## Launcher y control de versiones

El paquete incluirá:

```text
MercadoPagoColppyLauncher.exe
MercadoPagoColppy.exe
version.json
LEEME.txt
```

El launcher consultará `https://api.github.com/repos/Nico2026-PY/mercadopago-a-colppy/releases/latest` con HTTPS, encabezado `User-Agent` y timeout breve. Comparará la versión instalada de `version.json` con el tag remoto.

- Sin conexión, con límite de GitHub o respuesta inválida: abrirá la aplicación normalmente.
- Sin actualización: abrirá la aplicación.
- Con actualización: mostrará versión instalada y disponible, y ofrecerá `Abrir descarga` o `Continuar con esta versión`.

El launcher no usará tokens ni almacenará credenciales.

## Compilación y Releases

GitHub Actions se ejecutará manualmente y al publicar un tag `v*`. En `windows-latest` con Python 3.14:

1. instalará dependencias;
2. ejecutará todas las pruebas;
3. compilará aplicación y launcher con PyInstaller;
4. armará un ZIP portable limpio;
5. generará SHA-256;
6. creará el GitHub Release y adjuntará ambos archivos.

El workflow tendrá permiso `contents: write`. La versión del código, `version.json` y el tag deberán coincidir; una prueba impedirá publicar si divergen.

## Manejo de errores

- Un archivo sin las columnas requeridas de Mercado Pago se mostrará en `Revisiones y errores` y no se exportará como movimiento válido.
- Una empresa no seleccionada bloqueará análisis y exportación con una indicación concreta.
- Un fallo al guardar configuración preservará el archivo anterior mediante escritura temporal y reemplazo atómico.
- La confirmación del historial seguirá ocurriendo solamente después de que el usuario confirme que Colppy importó correctamente.
- El chequeo de actualizaciones nunca impedirá abrir la aplicación.

## Verificación

- Pruebas unitarias para configuración local, separación de historiales, cambio de empresa, versión y respuestas del updater.
- Prueba byte a byte del CSV Colppy sintético contra el contrato del archivo oficial.
- Pruebas de progreso monotónico entre 0 y 100.
- Suite completa en Linux y Windows mediante GitHub Actions.
- Validación de los reportes reales disponible únicamente en el entorno local; esos archivos no se incluirán ni se registrarán en Git.
- Inspección del ZIP final para confirmar que no contiene bases, reportes, salidas ni configuración local.
