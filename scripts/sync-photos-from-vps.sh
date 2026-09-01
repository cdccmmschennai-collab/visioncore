#!/usr/bin/env bash
# One-off backfill of uploaded photo files from the production VPS into the
# local `storage` Docker volume, for rows that already synced at the DB
# level (via app/services/sync_client.py) but whose files never made it
# over — e.g. rows that arrived before the file-sync endpoint existed, or
# while it was 404ing because the VPS was on an older deploy.
#
# This does NOT replace app/services/sync_client.py's own ongoing self-heal
# (backend/app/api/v1/sync.py::/tag-images/{id}/file) — once the VPS is
# redeployed with that endpoint, new gaps fix themselves automatically.
# This script is for backfilling what's missing *right now*, in one pass,
# without waiting on poll cycles.
#
# storage is a Docker *named volume* on both ends (see docker-compose.yml),
# not a host bind-mount, so a plain `rsync host:/path` can't see it without
# root access to Docker's internal volume directory. Instead this pipes a
# tar stream out of the VPS's running container, over ssh, straight into
# the local container's volume.
#
# Usage:
#   VPS_HOST=your.vps.host VPS_SSH_USER=youruser ./scripts/sync-photos-from-vps.sh
#
# Optional overrides:
#   VPS_SSH_PORT       (default 22)
#   SSH_KEY_PATH        (default: your default ssh key / ssh-agent)
#   REMOTE_CONTAINER    (default visioncore-api  -- the backend container name on the VPS)
#   LOCAL_CONTAINER     (default visioncore-api  -- the backend container name locally)
#   REMOTE_STORAGE_PATH (default /data/storage   -- STORAGE_DIR inside the container)
#   DRY_RUN=1           (list what would be copied without copying)

set -euo pipefail

# Git Bash (MSYS) on Windows rewrites any argument that starts with '/' into
# a Windows path before handing it to a non-MSYS binary like docker.exe --
# which mangles the in-container paths below (/data/storage, etc). This
# opts out of that rewriting; it's a no-op on Linux/macOS.
export MSYS_NO_PATHCONV=1
export MSYS2_ARG_CONV_EXCL='*'

: "${VPS_HOST:?Set VPS_HOST to your VPS hostname or IP}"
: "${VPS_SSH_USER:?Set VPS_SSH_USER to your SSH login user on the VPS}"
VPS_SSH_PORT="${VPS_SSH_PORT:-22}"
REMOTE_CONTAINER="${REMOTE_CONTAINER:-visioncore-api}"
LOCAL_CONTAINER="${LOCAL_CONTAINER:-visioncore-api}"
REMOTE_STORAGE_PATH="${REMOTE_STORAGE_PATH:-/data/storage}"
SSH_OPTS=(-p "$VPS_SSH_PORT")
[ -n "${SSH_KEY_PATH:-}" ] && SSH_OPTS+=(-i "$SSH_KEY_PATH")

STAGE_DIR="$(mktemp -d)"
trap 'rm -rf "$STAGE_DIR"' EXIT

echo "==> Verifying local container '$LOCAL_CONTAINER' is running..."
docker inspect -f '{{.State.Running}}' "$LOCAL_CONTAINER" >/dev/null

echo "==> Verifying remote container '$REMOTE_CONTAINER' is reachable on $VPS_HOST..."
ssh "${SSH_OPTS[@]}" "$VPS_SSH_USER@$VPS_HOST" \
  "docker inspect -f '{{.State.Running}}' '$REMOTE_CONTAINER'"

if [ "${DRY_RUN:-0}" = "1" ]; then
  echo "==> DRY RUN: listing remote files under $REMOTE_STORAGE_PATH"
  ssh "${SSH_OPTS[@]}" "$VPS_SSH_USER@$VPS_HOST" \
    "docker exec '$REMOTE_CONTAINER' find '$REMOTE_STORAGE_PATH' -type f" | wc -l
  exit 0
fi

echo "==> Streaming $REMOTE_STORAGE_PATH from the VPS into a local staging dir..."
ssh "${SSH_OPTS[@]}" "$VPS_SSH_USER@$VPS_HOST" \
  "docker exec '$REMOTE_CONTAINER' tar -cf - -C '$REMOTE_STORAGE_PATH' ." \
  | tar -xf - -C "$STAGE_DIR"

BEFORE=$(docker exec "$LOCAL_CONTAINER" sh -c "find /data/storage -type f | wc -l")

echo "==> Copying only files not already present locally into the '$LOCAL_CONTAINER' volume..."
# tar --skip-old-files (GNU tar, present in the backend's python:slim image)
# never overwrites a file that already exists locally, so a locally-created
# upload always wins over anything with the same name pulled from the VPS.
tar -cf - -C "$STAGE_DIR" . | docker exec -i "$LOCAL_CONTAINER" \
  tar --skip-old-files -xf - -C /data/storage

AFTER=$(docker exec "$LOCAL_CONTAINER" sh -c "find /data/storage -type f | wc -l")

echo "==> Done. Local file count: $BEFORE -> $AFTER"
echo "    Re-run with DRY_RUN=1 any time to check for new gaps without copying."
