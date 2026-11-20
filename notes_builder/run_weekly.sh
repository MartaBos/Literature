#!/usr/bin/env bash
# Weekly literature-notes update: write notes for new PDFs, then rebuild the HTML pages.
# Run by cron every Wednesday at 06:00 (crontab line in README.md). Safe to run by hand.
set -uo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
mkdir -p "$HERE/logs"
exec >>"$HERE/logs/weekly_$(date +%F).log" 2>&1

exec 9>"$HERE/.lock"
flock -n 9 || { echo "$(date '+%F %T') another run is still active, exiting"; exit 0; }

echo "=== $(date '+%F %T') weekly update start"
/usr/bin/python3 -I "$HERE/01_generate_notes.py"; rc1=$?
/usr/bin/python3 -I "$HERE/02_build_html.py";     rc2=$?
echo "=== $(date '+%F %T') done (notes rc=$rc1, html rc=$rc2)"
