@echo off
setlocal EnableDelayedExpansion
chcp 65001 >nul
REM ============================================================================================
REM  desplegar_reproduccion.bat
REM  Despliega en TU workspace de Databricks el proyecto "Estimacion-desempleo-Colombia-SAE":
REM  esquemas y volumenes (target `reproduccion` del bundle), carga de los datos de entrada
REM  desde datos_reproduccion\*.zip y, opcionalmente, ejecucion del pipeline completo.
REM
REM  REQUISITOS MINIMOS
REM   - Workspace de Databricks con Unity Catalog habilitado y computo serverless para jobs y
REM     notebooks (sirve Free Edition; una cuenta de prueba tambien).
REM   - Permiso CREATE CATALOG en el metastore (o que un administrador cree antes el catalogo
REM     `tesis`).
REM   - Que no exista ya un catalogo llamado `tesis` (o que este vacio): el nombre `tesis` esta
REM     fijo en el codigo y no se puede cambiar.
REM   - Databricks CLI >= 0.250 (esquemas y volumenes como recursos del bundle; probado con
REM     1.22.1). Instalacion: https://docs.databricks.com/dev-tools/cli/install.html
REM   - Windows 10/11 con tar.exe y PowerShell (incluidos), y git (para clonar el repositorio).
REM   - ~1 GB libres en disco (extraccion temporal) y acceso a la red.
REM
REM  USO
REM    desplegar_reproduccion.bat [perfil] [/simular]
REM      perfil    nombre de un perfil de la CLI (por defecto: tesis_repro)
REM      /simular  (o --dry-run) solo muestra los comandos remotos; extrae los zip en local pero
REM                no autentica, no crea nada en Databricks ni sube archivos.
REM ============================================================================================

set "PROF=tesis_repro"
set "SIMULAR=0"
set "CATALOGO=tesis"
set "TMPDIR=%TEMP%\tesis_repro"
set "RAIZ=%~dp0"
set "DATOS=%RAIZ%datos_reproduccion"

:args
if "%~1"=="" goto args_fin
if /i "%~1"=="/simular" set "SIMULAR=1" & shift & goto args
if /i "%~1"=="--dry-run" set "SIMULAR=1" & shift & goto args
set "PROF=%~1"
shift
goto args
:args_fin

set "RUN=databricks"
if "%SIMULAR%"=="1" set "RUN=echo [SIMULACION] databricks"
if "%SIMULAR%"=="1" echo *** MODO SIMULACION: no se ejecuta ningun comando remoto ***

cd /d "%RAIZ%"
if not exist "%DATOS%\MANIFIESTO.csv" (
  echo ERROR: no se encuentra datos_reproduccion\MANIFIESTO.csv. Ejecuta el script desde la raiz del repositorio.
  exit /b 1
)

echo.
echo [1/7] Verificando la Databricks CLI...
databricks --version >nul 2>&1
if errorlevel 1 (
  echo ERROR: no se encontro `databricks`. Instala la CLI: https://docs.databricks.com/dev-tools/cli/install.html
  exit /b 1
)
for /f "delims=" %%v in ('databricks --version') do set "VERSION_CLI=%%v"
echo       !VERSION_CLI!
powershell -NoProfile -Command "$m=[regex]::Match('!VERSION_CLI!','\d+\.\d+\.\d+'); if(-not $m.Success -or [version]$m.Value -lt [version]'0.250.0'){exit 1}"
if errorlevel 1 (
  echo ERROR: se requiere Databricks CLI 0.250 o superior. Actualiza la CLI.
  exit /b 1
)
where tar >nul 2>&1
if errorlevel 1 (
  echo ERROR: no se encontro tar.exe, incluido en Windows 10/11.
  exit /b 1
)

echo.
echo [2/7] Autenticacion en Databricks, perfil %PROF%...
if "%SIMULAR%"=="1" goto auth_sim
databricks current-user me --profile %PROF% >nul 2>&1
if not errorlevel 1 (
  echo       El perfil %PROF% ya es valido; se reutiliza.
  goto auth_fin
)
set "HOST="
set /p "HOST=URL del workspace (ej. https://dbc-xxxx.cloud.databricks.com): "
if "!HOST!"=="" (
  echo ERROR: debes indicar la URL del workspace.
  exit /b 1
)
databricks auth login --host !HOST! --profile %PROF%
if errorlevel 1 (
  echo ERROR: fallo la autenticacion.
  exit /b 1
)
databricks current-user me --profile %PROF% >nul 2>&1
if errorlevel 1 (
  echo ERROR: el perfil %PROF% no quedo valido tras el inicio de sesion.
  exit /b 1
)
goto auth_fin
:auth_sim
echo [SIMULACION] databricks auth login --host ^<URL del workspace^> --profile %PROF%   ^(solo si el perfil no es valido^)
:auth_fin
set "DATABRICKS_CONFIG_PROFILE=%PROF%"

echo.
echo [3/7] Catalogo `%CATALOGO%`...
if "%SIMULAR%"=="1" goto cat_sim
databricks catalogs get %CATALOGO% --profile %PROF% >nul 2>&1
if not errorlevel 1 (
  echo       El catalogo %CATALOGO% ya existe; se usa tal cual. Debe estar vacio o ser tuyo.
  goto cat_fin
)
set "RAIZ_ALMACEN="
echo       No existe. Free Edition y la mayoria de workspaces usan el almacenamiento por defecto.
set /p "RAIZ_ALMACEN=Ruta de almacenamiento del catalogo (storage root), o Enter para el valor por defecto: "
if "!RAIZ_ALMACEN!"=="" (
  databricks catalogs create %CATALOGO% --profile %PROF%
) else (
  databricks catalogs create %CATALOGO% --storage-root "!RAIZ_ALMACEN!" --profile %PROF%
)
if errorlevel 1 (
  echo ERROR: no se pudo crear el catalogo. Si el metastore exige storage root, indicalo; si no tienes
  echo        CREATE CATALOG, pide a un administrador que cree `%CATALOGO%` y vuelve a ejecutar.
  exit /b 1
)
goto cat_fin
:cat_sim
echo [SIMULACION] databricks catalogs get %CATALOGO% --profile %PROF%
echo [SIMULACION] databricks catalogs create %CATALOGO% [--storage-root ^<ruta^>] --profile %PROF%   ^(solo si no existe^)
:cat_fin

echo.
echo [4/7] Desplegando el bundle (esquemas, volumenes y jobs) con el target reproduccion...
%RUN% bundle deploy -t reproduccion --profile %PROF%
if errorlevel 1 (
  echo ERROR: fallo `databricks bundle deploy`.
  exit /b 1
)

echo.
echo [5/7] Extrayendo y subiendo los datos de entrada...
if exist "%TMPDIR%" rmdir /s /q "%TMPDIR%"
mkdir "%TMPDIR%"
set "N_ZIPS=0"
set "N_ERRORES=0"
for %%F in ("%DATOS%\*.zip") do call :procesar_zip "%%~nxF" "%%~nF"
if not "!N_ERRORES!"=="0" (
  echo ERROR: !N_ERRORES! volumen^(es^) con problemas. Revisa los mensajes anteriores.
  exit /b 1
)
echo       !N_ZIPS! volumenes procesados.

echo.
echo [6/7] Verificacion...
echo       Conteo de archivos por volumen, extraidos vs. MANIFIESTO.csv, mostrado arriba; la subida
echo       usa `fs cp -r`, que aborta ante cualquier error. Contenido de nivel superior en Databricks:
for %%F in ("%DATOS%\*.zip") do call :listar_volumen "%%~nF"

echo.
echo [7/7] Pipeline completo
echo       `pipeline_completo` corre los 6 jobs en orden con los valores por defecto (2018, mes 12,
echo       ventana de 12 meses). Puede tardar MUCHO tiempo (horas) y consume computo serverless.
set "RESP=N"
set /p "RESP=Ejecutar ahora el pipeline completo? (S/N) [N]: "
if /i "!RESP!"=="S" (
  %RUN% bundle run pipeline_completo -t reproduccion --profile %PROF%
  if errorlevel 1 (
    echo ERROR: el pipeline termino con error. Revisa la ejecucion en el workspace.
    exit /b 1
  )
) else (
  echo       Omitido. Para ejecutarlo despues:  databricks bundle run pipeline_completo -t reproduccion --profile %PROF%
)

if exist "%TMPDIR%" rmdir /s /q "%TMPDIR%"
echo.
echo Listo.
exit /b 0

REM -------------------------------------------------------------------------------------------
:procesar_zip
REM %1 = nombre.zip   %2 = nombre sin extension (<esquema>__<volumen>)
set "NOMBRE=%~2"
set "TMP2=!NOMBRE:__=#!"
for /f "tokens=1,2 delims=#" %%a in ("!TMP2!") do (
  set "ESQ=%%a"
  set "VOL=%%b"
)
set "DESTINO_LOCAL=%TMPDIR%\!ESQ!\!VOL!"
mkdir "!DESTINO_LOCAL!" 2>nul
echo   - !ESQ!/!VOL!
tar -xf "%DATOS%\%~1" -C "!DESTINO_LOCAL!"
if errorlevel 1 (
  echo     ERROR al extraer %~1
  set /a N_ERRORES+=1
  exit /b 0
)
set "N_LOCAL=0"
set "N_MANIF=0"
for /f %%c in ('powershell -NoProfile -Command "@(Get-ChildItem -LiteralPath '!DESTINO_LOCAL!' -Recurse -File).Count"') do set "N_LOCAL=%%c"
for /f %%c in ('powershell -NoProfile -Command "@(Import-Csv -LiteralPath '%DATOS%\MANIFIESTO.csv' | Where-Object { $_.zip -eq '%~1' }).Count"') do set "N_MANIF=%%c"
echo     archivos extraidos: !N_LOCAL!  ^|  filas en MANIFIESTO: !N_MANIF!
if not "!N_LOCAL!"=="!N_MANIF!" (
  echo     ERROR: el conteo no coincide con el manifiesto.
  set /a N_ERRORES+=1
  exit /b 0
)
REM `fs cp -r DIR destino` copia el CONTENIDO de DIR dentro de destino, es decir en la raiz del volumen.
%RUN% fs cp -r --overwrite "!DESTINO_LOCAL!" "dbfs:/Volumes/%CATALOGO%/!ESQ!/!VOL!" --profile %PROF%
if errorlevel 1 (
  echo     ERROR al subir !ESQ!/!VOL!
  set /a N_ERRORES+=1
  exit /b 0
)
set /a N_ZIPS+=1
exit /b 0

:listar_volumen
set "NOMBRE=%~1"
set "TMP2=!NOMBRE:__=#!"
for /f "tokens=1,2 delims=#" %%a in ("!TMP2!") do (
  echo   - %%a/%%b
  %RUN% fs ls "dbfs:/Volumes/%CATALOGO%/%%a/%%b" --profile %PROF%
)
exit /b 0
