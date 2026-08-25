#!/usr/bin/env bash
# Nightly VPS-vs-repo drift alarm (deploy audit 2026-08-25)
# Compares app.py content + templates/static file sets and hashes.
# CLEAN exit 0 | DRIFT exit 1 with a dated report (grep the log at any sweep).
set -euo pipefail
cd "$(dirname "$0")/.."
LOG="${DEPLOY_DRIFT_LOG:-$HOME/deploy-drift.log}"
VPS_HOST="${VPS_HOST:-vps}"
VPS_DIR="/docker/kyanite-landing"
STAMP=$(date -u +%Y-%m-%dT%H:%M:%SZ)
TMP=$(mktemp -d); trap 'rm -rf "$TMP"' EXIT

ssh -o ConnectTimeout=10 "$VPS_HOST" \
  "cd $VPS_DIR && md5sum overrides/app.py && find templates static -type f | grep -vE '/\._|\.DS_Store|_backup|/backups/' | sort | xargs md5sum" \
  > "$TMP/vps.md5" 2>/dev/null || { echo "$STAMP PROBE-FAIL cannot hash VPS" >> "$LOG"; exit 2; }

find templates static -type f | grep -vE '/\._|\.DS_Store|_backup|/backups/' | sort | xargs md5 -r > "$TMP/repo.md5"
md5 -r app.py | awk '{print $1"  overrides/app.py"}' >> "$TMP/repo.md5"

python3 - "$TMP/vps.md5" "$TMP/repo.md5" "$STAMP" "$LOG" <<'EOF'
import sys
def load(p):
    d = {}
    for line in open(p):
        parts = line.strip().split(None, 1)
        if len(parts) == 2:
            d[parts[1].lstrip('*').lstrip('./')] = parts[0]
    return d
vps, repo, stamp, log = load(sys.argv[1]), load(sys.argv[2]), sys.argv[3], sys.argv[4]
only_vps = sorted(set(vps) - set(repo))
only_repo = sorted(set(repo) - set(vps))
differ = sorted(f for f in set(vps) & set(repo) if vps[f] != repo[f])
if not (only_vps or only_repo or differ):
    print(f"{stamp} CLEAN repo==live ({len(vps)} files)")
    sys.exit(0)
lines = [f"{stamp} DRIFT vps-only={only_vps} repo-only={only_repo} differing={differ}"]
open(log, 'a').write('\n'.join(lines) + '\n')
print('\n'.join(lines))
sys.exit(1)
EOF
