#!/bin/sh
# An on-host consistent backup of this project's database and objects.
# Copy the resulting private directory off-host before calling it disaster recovery.
set -eu
umask 077
cd "$(dirname "$0")"
destination=${1:?Usage: sh backup.sh /absolute/new/backup-directory}
case "$destination" in /*) ;; *) echo 'Use an absolute backup path.' >&2; exit 1;; esac
mkdir -m 700 "$destination"
cp -p .env compose.yaml nginx.conf "$destination/"
docker compose stop projects-gateway projects-api >/dev/null
trap 'docker compose up -d projects-api projects-gateway >/dev/null' EXIT
docker compose exec -T projects-db pg_dump -U geolibre_projects -d geolibre_projects -Fc > "$destination/projects.dump"
docker compose run --rm -T --no-deps --entrypoint python projects-api -c 'import sys,tarfile; t=tarfile.open(fileobj=sys.stdout.buffer,mode="w|"); t.add("/data/objects",arcname="objects"); t.close()' > "$destination/objects.tar"
docker compose images --format json > "$destination/images.json"
test -s "$destination/projects.dump"
test -s "$destination/objects.tar"
chmod -R go-rwx "$destination"
echo "Project backup complete: $destination"
