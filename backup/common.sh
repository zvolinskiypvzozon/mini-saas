# Общие настройки для backup.sh, restore.sh и verify.sh (подключается через source).

: "${POSTGRES_USER:?POSTGRES_USER is not set}"
: "${POSTGRES_PASSWORD:?POSTGRES_PASSWORD is not set}"
: "${POSTGRES_DB:?POSTGRES_DB is not set}"
: "${S3_ENDPOINT:?S3_ENDPOINT is not set}"
: "${S3_ACCESS_KEY:?S3_ACCESS_KEY is not set}"
: "${S3_SECRET_KEY:?S3_SECRET_KEY is not set}"

BACKUP_BUCKET="${BACKUP_BUCKET:-backups}"
BACKUP_KEEP_DAYS="${BACKUP_KEEP_DAYS:-7}"

# pg_dump, pg_restore, psql берут подключение из переменных PG*
export PGHOST="${PGHOST:-db}"
export PGUSER="$POSTGRES_USER"
export PGPASSWORD="$POSTGRES_PASSWORD"
export PGOPTIONS="-c client_min_messages=warning"

# mc берёт адрес и ключи хранилища из MC_HOST_<alias>: s3/... = это хранилище
export MC_HOST_s3="${S3_ENDPOINT%%://*}://${S3_ACCESS_KEY}:${S3_SECRET_KEY}@${S3_ENDPOINT#*://}"

BACKUP_PREFIX="s3/${BACKUP_BUCKET}/${POSTGRES_DB}"

latest_backup() {
  mc ls "${BACKUP_PREFIX}/" | awk '{print $NF}' | grep '\.dump$' | sort | tail -1
}
