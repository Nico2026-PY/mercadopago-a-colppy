@echo off
setlocal
cd /d "%~dp0"

echo ========================================
echo Mercado Pago a Colppy - Crear portable
echo ========================================

set "PYTHON_LAUNCHER="

py -3.14 --version >nul 2>nul
if not errorlevel 1 set "PYTHON_LAUNCHER=py -3.14"

if not defined PYTHON_LAUNCHER (
  py -3.13 --version >nul 2>nul
  if not errorlevel 1 set "PYTHON_LAUNCHER=py -3.13"
)

if not defined PYTHON_LAUNCHER (
  py -3.12 --version >nul 2>nul
  if not errorlevel 1 set "PYTHON_LAUNCHER=py -3.12"
)

if not defined PYTHON_LAUNCHER (
  echo No se encontro Python 3.12, 3.13 o 3.14.
  echo Instala Python desde python.org y marca Add Python to PATH.
  pause
  exit /b 1
)

echo Usando:
%PYTHON_LAUNCHER% --version

if not exist ".venv-build\Scripts\python.exe" (
  %PYTHON_LAUNCHER% -m venv .venv-build
  if errorlevel 1 goto :error
)

call ".venv-build\Scripts\activate.bat"
python -m pip install --upgrade pip
if errorlevel 1 goto :error
python -m pip install -r requirements.txt
if errorlevel 1 goto :error

python -m unittest discover -s tests -v
if errorlevel 1 goto :error

python -m PyInstaller --noconfirm --clean MercadoPagoColppy.spec
if errorlevel 1 goto :error
python -m PyInstaller --noconfirm --clean MercadoPagoColppyLauncher.spec
if errorlevel 1 goto :error

powershell -NoProfile -ExecutionPolicy Bypass -File scripts\package_portable.ps1
if errorlevel 1 goto :error

echo.
echo Portable creado en release\MercadoPagoColppy-Windows.zip
pause
exit /b 0

:error
echo.
echo No se pudo crear el portable. Revisa el mensaje anterior.
pause
exit /b 1
