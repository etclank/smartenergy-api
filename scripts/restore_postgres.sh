#!/bin/sh
set -eu

required_variables="
BACKUP_ENDPOINT
BACKUP_BUCKET
BACKUP_ACCESS_KEY
BACKUP_SECRET_KEY
BACKUP_REGION
BACKUP_OBJECT_KEY
PGHOST
PGPORT
PGUSER
PGPASSWORD
TARGET_DATABASE
CONFIRM_RESTORE
"

for variable in $required_variables; do
  eval "value=\${$variable:-}"
  if [ -z "$value" ]; then
    echo "$variable is required" >&2
    exit 64
  fi
done

case "$BACKUP_ENDPOINT" in
  https://*) ;;
  *) echo "BACKUP_ENDPOINT must use HTTPS" >&2; exit 64 ;;
esac

case "$TARGET_DATABASE" in
  *[!a-zA-Z0-9_]*) echo "TARGET_DATABASE must be a simple PostgreSQL identifier" >&2; exit 64 ;;
esac

if [ "$CONFIRM_RESTORE" != "restore:$TARGET_DATABASE" ]; then
  echo "Set CONFIRM_RESTORE=restore:$TARGET_DATABASE to confirm the clean target" >&2
  exit 64
fi

for command_name in curl psql createdb pg_restore; do
  command -v "$command_name" >/dev/null 2>&1 || {
    echo "$command_name is required" >&2
    exit 69
  }
done

work_directory="$(mktemp -d)"
cleanup() {
  rm -rf "$work_directory"
}
trap cleanup EXIT HUP INT TERM

curl_config="$work_directory/curl.conf"
dump_file="$work_directory/database.dump"
umask 077
{
  printf 'url = "%s/%s/%s"\n' "${BACKUP_ENDPOINT%/}" "$BACKUP_BUCKET" "$BACKUP_OBJECT_KEY"
  printf 'aws-sigv4 = "aws:amz:%s:s3"\n' "$BACKUP_REGION"
  printf 'user = "%s:%s"\n' "$BACKUP_ACCESS_KEY" "$BACKUP_SECRET_KEY"
  printf 'output = "%s"\n' "$dump_file"
  printf 'fail-with-body\nshow-error\nsilent\nconnect-timeout = 15\nmax-time = 300\n'
} > "$curl_config"

curl --config "$curl_config"
test -s "$dump_file"

if psql --dbname=postgres --tuples-only --no-align \
  --command="SELECT 1 FROM pg_database WHERE datname = '$TARGET_DATABASE'" \
  | grep -q '^1$'; then
  echo "Target database already exists; refusing to overwrite it" >&2
  exit 73
fi

createdb --maintenance-db=postgres "$TARGET_DATABASE"
pg_restore --exit-on-error --no-owner --no-privileges \
  --dbname="$TARGET_DATABASE" "$dump_file"

restored_revision="$(
  psql --dbname="$TARGET_DATABASE" --tuples-only --no-align \
    --command='SELECT version_num FROM alembic_version LIMIT 1'
)"
test -n "$restored_revision"
printf 'Restore complete: database=%s alembic_revision=%s\n' \
  "$TARGET_DATABASE" "$restored_revision"
