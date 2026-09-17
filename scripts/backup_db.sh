#!/bin/bash
BACKUP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/backups"
mkdir -p "$BACKUP_DIR"

TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="$BACKUP_DIR/gtopagos_backup_$TIMESTAMP.sql.gz"

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Iniciando respaldo de base de datos..."

docker exec gtopagos_db pg_dump -U postgres gtopagos | gzip > "$BACKUP_FILE"

if [ $? -eq 0 ] && [ -s "$BACKUP_FILE" ]; then
    SIZE=$(ls -lh "$BACKUP_FILE" | awk '{print $5}')
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Respaldo completado con exito: $BACKUP_FILE ($SIZE)"
    find "$BACKUP_DIR" -name "gtopagos_backup_*.sql.gz" -mtime +14 -delete
else
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ERROR al generar el respaldo de la base de datos."
    rm -f "$BACKUP_FILE"
    exit 1
fi