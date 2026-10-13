<#
.SYNOPSIS
    Incrementa la version del ejecutable y compila main.exe con PyInstaller.

.DESCRIPTION
    Escribe la version en formato AAAA.MM.DD.VV (por ejemplo 2026.10.06.01) en
    los cuatro lugares de version.txt de donde PyInstaller la lee: filevers,
    prodvers, ProductVersion y FileVersion. Mantener las cuatro alineadas evita
    que el .exe muestre un numero ambiguo en sus Propiedades, que fue el
    problema que se corrigio en el commit 18a47f5.

    Si la fecha no cambia, incrementa el ultimo componente (VV) para no repetir
    version al recompilar el mismo dia. Si cambia, reinicia VV en 1.

    Luego compila con PyInstaller usando el mismo comando de compila.bat:
        pyinstaller --clean --version-file=version.txt -F --icon=... main.py
    Se invoca de forma nativa y no via cmd.exe porque el repo esta en un share
    de red y cmd.exe no acepta rutas UNC como directorio actual.

.PARAMETER Build
    Numero de build (VV) a usar. Si se omite, se calcula automaticamente:
    1 para una fecha nueva, o el valor anterior + 1 si la fecha ya es la de hoy.

.PARAMETER Fecha
    Fecha en formato AAAA.MM.DD. Por defecto, la fecha local de hoy.

.PARAMETER SaltarBuild
    Escribe la nueva version pero no compila. Util para revisar el diff.

.PARAMETER WhatIf
    Alias de -SaltarBuild, para dry-run intuitivo.

.EXAMPLE
    .\compilar.ps1
    Escribe 2026.10.06.01 en version.txt y compila.

.EXAMPLE
    .\compilar.ps1 -Build 5 -SaltarBuild
    Escribe 2026.10.06.05 sin compilar, para revisar el diff.

.NOTES
    Requiere PyInstaller 6.21.0 en el PATH:
        python -m pip install pyinstaller

    El .exe generado depende de que plantillas\, certificados\, mysql\ e
    imagenes\ existan junto a el en la maquina destino: main.spec declara
    datas=[], asi que esos recursos NO van empaquetados.
#>

[CmdletBinding()]
param(
    [int]$Build,
    [string]$Fecha,
    [switch]$SaltarBuild,
    [switch]$WhatIf
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$raiz = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $raiz

$versionFile = Join-Path $raiz 'version.txt'

if (-not (Test-Path $versionFile)) {
    throw "No se encontro version.txt en $raiz"
}

# --- Fecha objetivo -------------------------------------------------------
if ($Fecha) {
    $fechaObj = [datetime]::ParseExact($Fecha, 'yyyy.MM.dd', $null)
} else {
    $fechaObj = Get-Date
}
$anio = $fechaObj.ToString('yyyy')
$mes = $fechaObj.ToString('MM')
$dia = $fechaObj.ToString('dd')

# --- Leer version actual --------------------------------------------------
$contenido = Get-Content -Path $versionFile -Raw

$regexFilevers = 'filevers=\(\s*\d+\s*,\s*\d+\s*,\s*\d+\s*,\s*(\d+)\s*\)'
$regexProdvers = 'prodvers=\(\s*\d+\s*,\s*\d+\s*,\s*\d+\s*,\s*\d+\s*\)'
$regexFechaFijo = '\d{4}\s*,\s*\d{1,2}\s*,\s*\d{1,2}\s*,\s*\d+'
$regexProductVersion = "(ProductVersion',\s*u')[\d.]+(')"
$regexFileVersion = "(FileVersion',\s*u')[\d.]+(')"

$anterior = $null
if ($contenido -match $regexFilevers) {
    $anterior = $Matches[1]
}
# Solo la parte fecha (A.M.D) para comparar contra la fecha objetivo. Se
# normaliza a puntos porque filevers la escribe PyInstaller con comas.
$fechaActualIso = $null
if ($contenido -match $regexFechaFijo) {
    $partes = $Matches[0] -split ',' | ForEach-Object { $_.Trim() }
    $fechaActualIso = '{0}.{1:D2}.{2:D2}' -f [int]$partes[0], [int]$partes[1], [int]$partes[2]
}

# --- Determinar VV --------------------------------------------------------
$fechaIso = "$anio.$mes.$dia"
if ($PSBoundParameters.ContainsKey('Build')) {
    $vv = $Build
} elseif ($fechaActualIso -eq $fechaIso -and $anterior) {
    # Misma fecha que la del archivo: incrementar el build del dia.
    $vv = [int]$anterior + 1
} else {
    $vv = 1
}

if ($vv -lt 0 -or $vv -gt 999) {
    throw "Numero de build invalido: $vv (debe estar entre 0 y 999)"
}

$versionTexto = "$anio.$mes.$dia.{0:D2}" -f $vv
# OJO: filevers/prodvers se evalua como Python. Un entero con cero inicial
# ("06") es SyntaxError en Python 3 y PyInstaller aborta con
# "Failed to deserialize VSVersionInfo from text-based representation!".
# Por eso mes y dia van SIN padding en la tupla, aunque en el texto de
# ProductVersion/FileVersion si lleven (ahi son strings y el padding es correcto).
$tupla = '{0}, {1}, {2}, {3}' -f [int]$anio, [int]$mes, [int]$dia, $vv
Write-Host "Version destino: $versionTexto  (filevers/prodvers = ($tupla))"

# --- Reescribir version.txt ------------------------------------------------
$nuevo = $contenido
$nuevo = [regex]::Replace($nuevo, $regexFilevers, "filevers=($tupla)")
$nuevo = [regex]::Replace($nuevo, $regexProdvers, "prodvers=($tupla)")
$nuevo = [regex]::Replace($nuevo, $regexProductVersion, "`${1}$versionTexto`${2}")
$nuevo = [regex]::Replace($nuevo, $regexFileVersion, "`${1}$versionTexto`${2}")

if ($nuevo -eq $contenido) {
    throw 'version.txt no cambio. Revisar el formato del archivo.'
}

# Preservar CRLF: el archivo ya es CRLF y version.txt lo lee PyInstaller.
$nuevo = [regex]::Replace($nuevo, "(?<!`r)`n", "`r`n")

$utf8SinBom = New-Object System.Text.UTF8Encoding($false)
[System.IO.File]::WriteAllText($versionFile, $nuevo, $utf8SinBom)
Write-Host "version.txt actualizado." -ForegroundColor Green

# --- Verificar que las cuatro versiones coincidan -------------------------
# --- Verificar que version.txt sea parseable y coherente -------------------
# El chequeo tiene que compilar el archivo, no solo comparar con regex:
# version.txt se evalua como Python, y un entero con cero inicial ("06") es
# SyntaxError que hace fallar a PyInstaller.
$verificacion = @"
import ast, re, sys
ruta = r'$versionFile'
src = open(ruta, encoding='utf-8').read()
try:
    ast.parse(src)
except SyntaxError as e:
    sys.exit('version.txt no es Python valido (linea %s): %s' % (e.lineno, e.msg))

fv = re.search(r'filevers=\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\)', src)
pv = re.search(r'prodvers=\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\)', src)
pv_s = re.search(r"ProductVersion',\s*u'([\d.]+)'", src)
fv_s = re.search(r"FileVersion',\s*u'([\d.]+)'", src)
if not all([fv, pv, pv_s, fv_s]):
    sys.exit('version.txt: no se encontraron los cuatro campos')
ft = tuple(int(x) for x in fv.groups())
pt = tuple(int(x) for x in pv.groups())
pst = tuple(int(x) for x in pv_s.group(1).split('.'))
fst = tuple(int(x) for x in fv_s.group(1).split('.'))
if not (ft == pt == pst == fst):
    sys.exit('version.txt: versiones divergentes %s %s %s %s' % (ft, pt, pst, fst))
print('OK: version.txt compila y las cuatro versiones coinciden en ' + pv_s.group(1))
"@

$verificacion | python -
if ($LASTEXITCODE -ne 0) {
    throw 'version.txt quedo inconsistente. Revisar el archivo.'
}

if ($SaltarBuild -or $WhatIf) {
    Write-Host 'SaltarBuild: no se compilo. Revisar el diff de version.txt.' -ForegroundColor Yellow
    exit 0
}

# --- Limpiar build/ --------------------------------------------------------
# El share de red (\\pc-oscar\...) deja los directorios con el atributo
# ReadOnly de Windows. shutil.rmtree() termina en os.rmdir(), y en Windows un
# directorio ReadOnly no se borra aunque no este protegido: falla con
# "PermissionError: [WinError 5] Acceso denegado" sobre build\main\localpycs.
# Por eso hay que quitar el atributo antes de borrar, y no alcanzar a que lo
# haga el --clean de PyInstaller.
function Quitar-SoloLectura {
    param([string]$Ruta)
    if (-not (Test-Path $Ruta)) { return }
    $bandera = [IO.FileAttributes]::ReadOnly
    Get-ChildItem -LiteralPath $Ruta -Recurse -Force -ErrorAction SilentlyContinue |
        ForEach-Object {
            if ($_.Attributes -band $bandera) {
                try { $_.Attributes = $_.Attributes -band (-bnot $bandera) } catch { }
            }
        }
    $raizItem = Get-Item -LiteralPath $Ruta -Force
    if ($raizItem.Attributes -band $bandera) {
        try { $raizItem.Attributes = $raizItem.Attributes -band (-bnot $bandera) } catch { }
    }
}

$dirBuild = Join-Path $raiz 'build'
if (Test-Path $dirBuild) {
    Write-Host 'Limpiando build\ (quitando atributo ReadOnly)...' -ForegroundColor DarkGray
    Quitar-SoloLectura -Ruta $dirBuild
    Remove-Item -LiteralPath $dirBuild -Recurse -Force -ErrorAction SilentlyContinue
    if (Test-Path $dirBuild) {
        # Segundo intento: puede quedar un handle abierto (AV, explorador).
        Start-Sleep -Seconds 2
        Quitar-SoloLectura -Ruta $dirBuild
        Remove-Item -LiteralPath $dirBuild -Recurse -Force -ErrorAction SilentlyContinue
    }
    if (Test-Path $dirBuild) {
        Write-Warning "No se pudo eliminar por completo $dirBuild. Si el build falla con WinError 5, cerrar el antivirus o el explorador que lo este bloqueando y reintentar."
    }
}

# --- Compilar --------------------------------------------------------------
# Se invoca PyInstaller de forma nativa y NO via cmd.exe / compila.bat.
# Razon: el repo esta en un share de red. cmd.exe no acepta una ruta UNC como
# directorio actual, cae a C:\Windows, y PyInstaller se niega a correr desde
# ahi ("Do not run pyinstaller from C:\Windows"). Cuando el .ps1 se lanza desde
# el UNC eso rompe el build; desde la unidad mapeada (X:) podria funcionar, pero
# depender de como se invoque es fragil. PowerShell y Python si manejan UNC.
# El comando es el mismo de compila.bat:
#     pyinstaller --clean --version-file=version.txt -F --icon=... main.py
if (-not (Get-Command pyinstaller -ErrorAction SilentlyContinue)) {
    throw 'pyinstaller no esta en el PATH. Instalar con: python -m pip install pyinstaller'
}
$icono = Join-Path $raiz 'imagenes\logo.ico'
if (-not (Test-Path $icono)) {
    throw "No se encontro el icono en $icono"
}

$logBuild = Join-Path $env:TEMP 'compilar_pyinstaller.log'
Write-Host 'Compilando con PyInstaller (onefile)...' -ForegroundColor Cyan
Write-Host "  log: $logBuild"

Push-Location $raiz
try {
    # PyInstaller registra sus INFO por stderr. Con ErrorActionPreference='Stop'
    # PowerShell aborta en la primera linea, asi que se relaja la preferencia
    # durante el build y el resultado se evalua por $LASTEXITCODE.
    $ErrorActionPreference = 'Continue'
    $lineas = & pyinstaller --clean --version-file=version.txt -F --icon=imagenes\logo.ico main.py *>&1
    $codigo = $LASTEXITCODE
    $ErrorActionPreference = 'Stop'
} finally {
    Pop-Location
}

# Log en UTF-8 (Tee-Object escribe UTF-16 en Windows PowerShell, que despues
# no se puede grepear) y solo con la salida de PyInstaller, sin el adorno de
# "NativeCommandError" que PowerShell envuelve alrededor de cada linea de stderr.
$utf8 = New-Object System.Text.UTF8Encoding($false)
$limpio = @()
foreach ($l in $lineas) {
    $s = "$l"
    if ($s -match '^\s*\+\s') { continue }        # eco de la linea de codigo
    if ($s -match 'CategoryInfo|FullyQualifiedErrorId|^\s*at |NotSpecified') { continue }
    # OJO: en Windows PowerShell 5.1 el escape "`e" no existe y se interpreta
    # como la letra 'e' literal, lo que borra todas las 'e' de cada linea.
    # Para quitar secuencias de escape se usa el caracter por su codigo.
    $esc = [string][char]27
    $s = ($s -replace $esc, '').TrimEnd()
    if ($s -ne '') { $limpio += $s }
}
[System.IO.File]::WriteAllLines($logBuild, [string[]]$limpio, $utf8)
$limpio | ForEach-Object { Write-Host $_ }

if ($codigo -ne 0) {
    Write-Host ''
    Write-Host "Ultimas lineas del build:" -ForegroundColor Red
    Get-Content $logBuild -Tail 30 -ErrorAction SilentlyContinue |
        ForEach-Object { Write-Host "  $_" }
    throw "pyinstaller devolvio codigo $codigo"
}

$exe = Join-Path $raiz 'dist\main.exe'
if (-not (Test-Path $exe)) {
    throw 'El build termino sin error pero no genero dist\main.exe'
}

# --- Verificar la version embebida en el .exe -------------------------------
# Si el build se completo pero la version no quedo escrita, el .exe muestra un
# numero equivocado en Propiedades. Se avisa, pero no se corta el build.
$versionReal = $null
try {
    $info0 = Get-Item $exe
    $versionReal = $info0.VersionInfo.ProductVersion
} catch { }
if ($versionReal) {
    $esperada = ($versionTexto -replace '\.', ',')
    if ($versionReal -ne $esperada -and $versionReal -ne $versionTexto) {
        Write-Warning "La version embebida en main.exe es '$versionReal' y se esperaba '$esperada'."
    } else {
        Write-Host "Version embebida en main.exe: $versionReal"
    }
}

$info = Get-Item $exe
Write-Host ''
Write-Host ("main.exe generado: {0:N1} MB, {1}" -f ($info.Length / 1MB), $info.LastWriteTime) -ForegroundColor Green
Write-Host "Version declarada en version.txt: $versionTexto"
Write-Host 'Recordar: el .exe necesita plantillas\, certificados\, mysql\ e imagenes\ junto a el.'
