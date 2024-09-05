#!/bin/bash
BACKUP_DIR="/path/to/backup/dir"
TIMESTAMP=$(date +"%F")
BACKUP_NAME="mongo_backup_$TIMESTAMP"

# Команда для создания бэкапа
docker exec mongo mongodump --archive="$BACKUP_DIR/$BACKUP_NAME.archive" --gzip

# Удаление бэкапов старше 7 дней
find $BACKUP_DIR -type f -name "*.archive" -mtime +7 -exec rm {} \;