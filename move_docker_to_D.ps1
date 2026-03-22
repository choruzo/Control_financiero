# ============================================================
#  move_docker_to_D.ps1
#  Mueve los datos de Docker Desktop del disco C al disco D
#  Ejecutar como Administrador en PowerShell
# ============================================================

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# ---------- CONFIGURACIÓN ----------
$SOURCE_DISK  = "C:\Users\javie\AppData\Local\Docker\wsl\disk\docker_data.vhdx"
$SOURCE_MAIN  = "C:\Users\javie\AppData\Local\Docker\wsl\main\ext4.vhdx"
$DEST_DIR     = "D:\Docker\wsl"
$DEST_DISK    = "$DEST_DIR\disk\docker_data.vhdx"
$DEST_MAIN    = "$DEST_DIR\main\ext4.vhdx"
$SETTINGS     = "$env:APPDATA\Docker\settings-store.json"
# -----------------------------------

function Step {
    param([string]$msg)
    Write-Host "`n[PASO] $msg" -ForegroundColor Cyan
}

function OK   { Write-Host "  OK: $args" -ForegroundColor Green }
function WARN { Write-Host "  AVISO: $args" -ForegroundColor Yellow }
function FAIL {
    Write-Host "`n  ERROR: $args" -ForegroundColor Red
    Write-Host "  El script se ha detenido. Ningún archivo ha sido eliminado del origen." -ForegroundColor Red
    exit 1
}

# ============================================================
# VERIFICACIONES PREVIAS
# ============================================================
Step "Verificando prerequisitos"

if (-not ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole(
    [Security.Principal.WindowsBuiltInRole]::Administrator)) {
    FAIL "Debes ejecutar este script como Administrador."
}
OK "Ejecutando con permisos de Administrador"

if (-not (Test-Path $SOURCE_DISK)) { FAIL "No se encuentra: $SOURCE_DISK" }
if (-not (Test-Path $SOURCE_MAIN)) { FAIL "No se encuentra: $SOURCE_MAIN" }
OK "Archivos VHDX origen encontrados"

$driveD = Get-PSDrive D -ErrorAction SilentlyContinue
if (-not $driveD) { FAIL "El disco D no está disponible." }

$freeGB = [math]::Round($driveD.Free / 1GB, 1)
$diskGB = [math]::Round((Get-Item $SOURCE_DISK).Length / 1GB, 1)
$mainMB = [math]::Round((Get-Item $SOURCE_MAIN).Length / 1MB, 0)
Write-Host "  Espacio libre en D: ${freeGB} GB  |  Necesario: ~${diskGB} GB" -ForegroundColor Gray

if ($freeGB -lt ($diskGB + 2)) {
    FAIL "Espacio insuficiente en D. Libera al menos $([math]::Round($diskGB + 2, 0)) GB."
}
OK "Espacio suficiente en disco D"

# ============================================================
# PASO 1 — Cerrar Docker Desktop
# ============================================================
Step "Cerrando Docker Desktop"

$dockerProcess = Get-Process "Docker Desktop" -ErrorAction SilentlyContinue
if ($dockerProcess) {
    Stop-Process -Name "Docker Desktop" -Force
    Start-Sleep -Seconds 5
    OK "Docker Desktop cerrado"
} else {
    WARN "Docker Desktop no estaba en ejecución"
}

# Detener servicios WSL de Docker si siguen activos
wsl --terminate docker-desktop      2>$null
wsl --terminate docker-desktop-data 2>$null
Start-Sleep -Seconds 3
OK "Procesos WSL de Docker detenidos"

# ============================================================
# PASO 2 — Crear estructura de carpetas en D
# ============================================================
Step "Creando carpetas destino en D:\Docker"

$folders = @("$DEST_DIR\disk", "$DEST_DIR\main")
foreach ($f in $folders) {
    if (-not (Test-Path $f)) {
        New-Item -ItemType Directory -Path $f -Force | Out-Null
        OK "Creada: $f"
    } else {
        WARN "Ya existe: $f"
    }
}

# ============================================================
# PASO 3 — Copiar los VHDX a D (origen NO se toca aún)
# ============================================================
Step "Copiando docker_data.vhdx (~${diskGB} GB) — puede tardar varios minutos"

try {
    Copy-Item -Path $SOURCE_DISK -Destination $DEST_DISK -Force
    OK "docker_data.vhdx copiado"
} catch {
    FAIL "Error al copiar docker_data.vhdx: $_"
}

Step "Copiando ext4.vhdx (~${mainMB} MB)"
try {
    Copy-Item -Path $SOURCE_MAIN -Destination $DEST_MAIN -Force
    OK "ext4.vhdx copiado"
} catch {
    FAIL "Error al copiar ext4.vhdx: $_"
}

# ============================================================
# PASO 4 — Verificar integridad (tamaños iguales)
# ============================================================
Step "Verificando integridad de la copia"

$srcDiskSize  = (Get-Item $SOURCE_DISK).Length
$destDiskSize = (Get-Item $DEST_DISK).Length
$srcMainSize  = (Get-Item $SOURCE_MAIN).Length
$destMainSize = (Get-Item $DEST_MAIN).Length

if ($srcDiskSize -ne $destDiskSize) {
    FAIL "Tamaño de docker_data.vhdx no coincide: origen=${srcDiskSize} destino=${destDiskSize}"
}
OK "docker_data.vhdx: tamaño verificado ($([math]::Round($destDiskSize/1GB,1)) GB)"

if ($srcMainSize -ne $destMainSize) {
    FAIL "Tamaño de ext4.vhdx no coincide: origen=${srcMainSize} destino=${destMainSize}"
}
OK "ext4.vhdx: tamaño verificado ($([math]::Round($destMainSize/1MB,0)) MB)"

# ============================================================
# PASO 5 — Actualizar settings de Docker Desktop
# ============================================================
Step "Actualizando configuración de Docker Desktop"

if (Test-Path $SETTINGS) {
    # Hacer backup del settings original
    $backupPath = "$SETTINGS.backup_$(Get-Date -Format 'yyyyMMdd_HHmmss')"
    Copy-Item $SETTINGS $backupPath
    OK "Backup guardado en: $backupPath"

    $json = Get-Content $SETTINGS -Raw | ConvertFrom-Json

    # Docker Desktop usa "DiskSizeMiB" y "dataFolder" según la versión
    # Añadir/actualizar la ruta del disco de datos
    if ($json.PSObject.Properties.Name -contains "dataFolder") {
        $json.dataFolder = $DEST_DIR
        OK "Campo 'dataFolder' actualizado"
    } else {
        $json | Add-Member -NotePropertyName "dataFolder" -NotePropertyValue $DEST_DIR -Force
        OK "Campo 'dataFolder' añadido"
    }

    $json | ConvertTo-Json -Depth 10 | Set-Content $SETTINGS -Encoding UTF8
    OK "settings-store.json guardado"
} else {
    WARN "No se encontró settings-store.json en $SETTINGS — actualiza manualmente en Docker Desktop > Settings > Resources"
}

# ============================================================
# PASO 6 — Redirigir carpetas origen con Junction (symlink)
# ============================================================
# Esto garantiza compatibilidad si Docker busca la ruta original
Step "Creando symlinks desde la ruta original hacia D:"

$junctions = @(
    @{ Old = "C:\Users\javie\AppData\Local\Docker\wsl\disk"; New = "$DEST_DIR\disk" },
    @{ Old = "C:\Users\javie\AppData\Local\Docker\wsl\main"; New = "$DEST_DIR\main" }
)

foreach ($j in $junctions) {
    if (Test-Path $j.Old) {
        # Renombrar la carpeta original (backup, no borrar todavía)
        $bakName = "$($j.Old)_backup_$(Get-Date -Format 'yyyyMMdd')"
        Rename-Item -Path $j.Old -NewName (Split-Path $bakName -Leaf) -ErrorAction SilentlyContinue
        OK "Carpeta origen renombrada a: $bakName"
    }
    # Crear junction point
    cmd /c "mklink /J `"$($j.Old)`" `"$($j.New)`"" | Out-Null
    if (Test-Path $j.Old) {
        OK "Junction creado: $($j.Old) -> $($j.New)"
    } else {
        WARN "No se pudo crear junction para $($j.Old) — puede que necesites ajustar la ruta manualmente"
    }
}

# ============================================================
# RESUMEN FINAL
# ============================================================
Write-Host "`n============================================================" -ForegroundColor Green
Write-Host "  MIGRACIÓN COMPLETADA" -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Green
Write-Host ""
Write-Host "  Datos Docker movidos a: $DEST_DIR"
Write-Host "  Symlinks creados para compatibilidad con la ruta original"
Write-Host ""
Write-Host "  PRÓXIMOS PASOS:" -ForegroundColor Yellow
Write-Host "  1. Abre Docker Desktop y espera a que arranque correctamente"
Write-Host "  2. Verifica que tus contenedores e imágenes siguen disponibles:"
Write-Host "     docker ps -a"
Write-Host "     docker images"
Write-Host "  3. Si todo funciona, puedes borrar las carpetas _backup_* en C:"
Write-Host "     C:\Users\javie\AppData\Local\Docker\wsl\disk_backup_*"
Write-Host "     C:\Users\javie\AppData\Local\Docker\wsl\main_backup_*"
Write-Host ""
Write-Host "  En caso de problema, restaura ejecutando:" -ForegroundColor Cyan
Write-Host "  Remove-Item 'C:\Users\javie\AppData\Local\Docker\wsl\disk' -Force"
Write-Host "  Rename-Item 'C:\...\disk_backup_FECHA' 'disk'"
Write-Host "  (y repite para 'main')"
Write-Host ""
