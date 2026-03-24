#!/usr/bin/env sh
# pg-backup.sh — Backup automático de PostgreSQL con rotación
#
# Se ejecuta dentro del contenedor fincontrol-backup vía crond.
# También puede lanzarse manualmente:
#   docker exec fincontrol-backup pg-backup.sh
#
# Variables de entorno (inyectadas por docker-compose):
#   POSTGRES_HOST     — hostname del contenedor postgres
#   POSTGRES_USER     — usuario de la base de datos
#   POSTGRES_DB       — nombre de la base de datos
#   PGPASSWORD        — contraseña (usada automáticamente por pg_dump)
#   BACKUP_KEEP_DAYS  — días de retención (default: 7)

set -e

DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="${BACKUP_DIR:-/backups}"
KEEP_DAYS="${BACKUP_KEEP_DAYS:-7}"
FILENAME="fincontrol_${DATE}.sql.gz"

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Iniciando backup de ${POSTGRES_DB}..."

# Crear directorio si no existe
mkdir -p "${BACKUP_DIR}"

# Ejecutar pg_dump y comprimir con gzip
pg_dump \
    -h "${POSTGRES_HOST}" \
    -U "${POSTGRES_USER}" \
    "${POSTGRES_DB}" \
    | gzip > "${BACKUP_DIR}/${FILENAME}"

SIZE=$(du -sh "${BACKUP_DIR}/${FILENAME}" | cut -f1)
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Backup completado: ${FILENAME} (${SIZE})"

# Rotación: eliminar backups más antiguos que KEEP_DAYS
DELETED=$(find "${BACKUP_DIR}" -name "fincontrol_*.sql.gz" -mtime "+${KEEP_DAYS}" -print)
if [ -n "${DELETED}" ]; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Eliminando backups con más de ${KEEP_DAYS} días:"
    echo "${DELETED}" | while read -r f; do
        echo "  - $(basename "${f}")"
        rm -f "${f}"
    done
fi

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Backups disponibles en ${BACKUP_DIR}:"
ls -lh "${BACKUP_DIR}/fincontrol_*.sql.gz" 2>/dev/null || echo "  (ninguno)"
