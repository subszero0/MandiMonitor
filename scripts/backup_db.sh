#!/usr/bin/env bash
# Nightly SQLite dump with date suffix; keep 30 copies.
set -euo pipefail
BACKUP_DIR="/home/ubuntu/backups"
mkdir -p "$BACKUP_DIR"
FILE="$BACKUP_DIR/db_$(date +%Y-%m-%d).sqlite3"
cp /home/ubuntu/app/dealbot.db "$FILE"
find "$BACKUP_DIR" -type f -mtime +30 -delete