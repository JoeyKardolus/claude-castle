#!/bin/bash
# Creates Nextcloud's database inside the shared postgres container.
#
# The postgres image runs every script in /docker-entrypoint-initdb.d/ ONCE,
# on the very first boot of an empty data volume (docker-compose.yml mounts
# this file there). The main database (for notulen) is created by the image
# itself from POSTGRES_DB; this script adds a second database + user so
# Nextcloud gets its own, separate credentials.
#
# Runs INSIDE the postgres container, where the NEXTCLOUD_DB_* variables are
# set by docker-compose.yml. If you ever wipe the postgres volume, this runs
# again on the next start — nothing else to do.
set -euo pipefail

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
	CREATE USER "$NEXTCLOUD_DB_USER" WITH PASSWORD '$NEXTCLOUD_DB_PASSWORD';
	CREATE DATABASE "$NEXTCLOUD_DB_NAME" OWNER "$NEXTCLOUD_DB_USER";
EOSQL

echo "created nextcloud database '$NEXTCLOUD_DB_NAME' owned by '$NEXTCLOUD_DB_USER'"
