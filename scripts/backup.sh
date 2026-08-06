#!/bin/bash
# Nightly backup: MariaDB dump + uploads archive. Adjust the paths/creds to
# your deployment, then add to cron, e.g.:
#   30 3 * * * /path/to/scripts/backup.sh >> /path/to/backup.log 2>&1
set -euo pipefail

COMPOSE_DIR="${COMPOSE_DIR:-/opt/ctfd}"      # dir containing docker-compose.yml
BACKUP_DIR="${BACKUP_DIR:-$COMPOSE_DIR/backup/archive}"
DB_NAME="${DB_NAME:-ctfd}"
DB_USER="${DB_USER:-root}"
DB_PASS="${DB_PASS:-ctfd}"                   # prefer sourcing from your .env
RETENTION_DAYS="${RETENTION_DAYS:-14}"
STAMP="$(date +%Y%m%d-%H%M%S)"

mkdir -p "$BACKUP_DIR"
cd "$COMPOSE_DIR"

docker compose exec -T db mariadb-dump \
  -u"$DB_USER" -p"$DB_PASS" \
  --single-transaction --quick --routines --events \
  "$DB_NAME" | gzip > "$BACKUP_DIR/ctfd-db-$STAMP.sql.gz"

if ! zcat "$BACKUP_DIR/ctfd-db-$STAMP.sql.gz" | tail -1 | grep -q "Dump completed"; then
  echo "[$STAMP] ERROR: DB dump did not complete" >&2
  exit 1
fi

tar -czf "$BACKUP_DIR/ctfd-uploads-$STAMP.tar.gz" -C "$COMPOSE_DIR/.data/CTFd" uploads

find "$BACKUP_DIR" -name 'ctfd-*.gz' -mtime "+$RETENTION_DAYS" -delete
echo "[$STAMP] OK db=$(du -h "$BACKUP_DIR/ctfd-db-$STAMP.sql.gz" | cut -f1) uploads=$(du -h "$BACKUP_DIR/ctfd-uploads-$STAMP.tar.gz" | cut -f1)"
# Recommended: copy $BACKUP_DIR off-server (rsync / object storage).
