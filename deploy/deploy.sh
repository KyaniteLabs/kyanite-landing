#!/usr/bin/env bash
# Kyanite landing deploy — repo truth -> Hetzner VPS (deploy audit 2026-08-25)
# Usage: deploy.sh [--dry-run] [--health-only]
# Law: repo is TRUTH after the 08-25 fold-back; live-patching the VPS without
# a commit is the drift class that ate this site twice (lazy-media.js Jul 17,
# orphaned posts Aug 25). Edit the repo, run this, never sed the VPS.
set -euo pipefail
cd "$(dirname "$0")/.."

VPS_HOST="${VPS_HOST:-vps}"
VPS_DIR="/docker/kyanite-landing"
CONTAINER="kyanite-landing"
DRY=0; [[ "${1:-}" == "--dry-run" ]] && DRY=1
HEALTH_ONLY=0; [[ "${1:-}" == "--health-only" ]] && HEALTH_ONLY=1

health() {
  local i
  for i in 1 2 3 4 5; do
    if curl -sf -o /dev/null --max-time 10 https://kyanitelabs.tech; then
      echo "HEALTH OK (attempt $i)"; return 0
    fi
    sleep 3
  done
  echo "HEALTH FAIL — https://kyanitelabs.tech not answering after restart"; return 1
}

if [[ $HEALTH_ONLY == 1 ]]; then health; exit $?; fi

RSYNC_DRY=(); [[ $DRY == 1 ]] && RSYNC_DRY=(--dry-run)

# app.py deploys into the overrides volume mount; templates/static into the tree
rsync -a --delete \
  --exclude '.git' --exclude '._*' --exclude '.DS_Store' \
  --exclude 'backups' --exclude '_backup*' --exclude 'deploy' \
  "${RSYNC_DRY[@]}" \
  -e ssh ./templates ./static "$VPS_HOST:$VPS_DIR/"
rsync -a "${RSYNC_DRY[@]}" -e ssh ./app.py "$VPS_HOST:$VPS_DIR/overrides/app.py"

if [[ $DRY == 1 ]]; then
  echo "DRY RUN complete — no restart, no changes"
  exit 0
fi

ssh "$VPS_HOST" "docker restart $CONTAINER" >/dev/null
echo "restarted $CONTAINER at $(date -u +%Y-%m-%dT%H:%M:%SZ)"
health
