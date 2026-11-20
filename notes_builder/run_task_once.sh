#!/usr/bin/env bash
# Run a one-time code task (tasks/<name>.md) with headless Claude, check the result, keep or roll back.
# Started by a one-time cron line; removes that line itself. Never pushes.
#   - no usage left / Claude error  -> nothing changed, logged
#   - checks fail                   -> all files restored, attempt saved as logs/task_<name>_attempt.patch
#   - checks pass                   -> local git commit (author Marta, no Claude line); not pushed
# Usage: run_task_once.sh tasks/2026-11-25_sort_filter.md
set -uo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
REPO="$(cd "$HERE/.." && pwd)"
TASK="$HERE/${1#$HERE/}"; NAME="$(basename "$TASK" .md)"
mkdir -p "$HERE/logs" "$HERE/work"
exec >>"$HERE/logs/task_${NAME}.log" 2>&1
echo "=== $(date '+%F %T') task $NAME"
remove_cron() { crontab -l 2>/dev/null | grep -v "run_task_once.sh.*${NAME}" | crontab -; echo "cron line removed"; }
[ -f "$HERE/tasks/.${NAME}.done" ] && { echo "already done"; remove_cron; exit 0; }

exec 9>"$HERE/.lock"; flock -w 7200 9 || { echo "lock busy for 2 h, giving up"; remove_cron; exit 1; }

ALLOWED="notes_builder/00_make_template.py notes_builder/02_build_html.py notes_builder/template.html"
BK="$HERE/work/backup_${NAME}"; rm -rf "$BK"; mkdir -p "$BK"
for f in $ALLOWED; do cp -p "$REPO/$f" "$BK/"; done
cd "$REPO"; git status --porcelain > "$BK/status_before.txt"
BEFORE="$("$HERE/check_pages.sh" | sort)"; echo "pages before:"; echo "$BEFORE"

restore() {
    echo "RESTORING: $1"
    git diff > "$HERE/logs/task_${NAME}_attempt.patch" 2>/dev/null
    for f in $ALLOWED; do cp -p "$BK/$(basename "$f")" "$REPO/$f"; done
    # any other tracked file the run changed in notes_builder (should not happen): back to HEAD
    git status --porcelain notes_builder | awk '$1=="M"{print $2}' | while read -r f; do
        case " $ALLOWED " in *" $f "*) ;; *) grep -q " $f\$" "$BK/status_before.txt" || git checkout -- "$f";; esac; done
    (cd "$HERE" && /usr/bin/python3 -I 02_build_html.py >/dev/null)
    remove_cron; exit 1
}

CLAUDE=$(ls -d "$HOME"/.vscode-server/extensions/anthropic.claude-code-*/resources/native-binary/claude 2>/dev/null | sort -V | tail -1)
[ -x "$CLAUDE" ] || { echo "claude binary not found"; remove_cron; exit 1; }
cd "$HERE"
CLAUDE_CODE_MAX_OUTPUT_TOKENS=32000 timeout 5400 "$CLAUDE" -p "$(cat "$TASK")" \
    --tools "Read,Edit,Write,Bash" \
    --allowedTools "Read" "Edit" "Write" "Bash(python3 -I 00_make_template.py)" \
                   "Bash(python3 -I 02_build_html.py)" "Bash(./check_pages.sh)" \
    --strict-mcp-config --no-session-persistence --output-format json \
    < /dev/null > "$HERE/logs/task_${NAME}_claude.json"
rc=$?
RESULT=$(/usr/bin/python3 -I -c "import json,sys; d=json.load(open(sys.argv[1])); print(('ERROR ' if d.get('is_error') else '') + str(d.get('result',''))[:3000]); print('cost', d.get('total_cost_usd'))" "$HERE/logs/task_${NAME}_claude.json" 2>&1)
echo "claude exit $rc:"; echo "$RESULT"
case "$RESULT" in *"hit your"*limit*|*"usage limit"*) restore "no usage left";; esac
[ $rc -ne 0 ] && restore "claude exited with $rc"
[[ "$RESULT" == ERROR* ]] && restore "claude reported an error"

cd "$REPO"
OTHER=$(git status --porcelain notes_builder | grep -v -F -f "$BK/status_before.txt" \
        | grep -v -E "notes_builder/(00_make_template\.py|02_build_html\.py|template\.html|logs/|work/|tasks/)" || true)
[ -n "$OTHER" ] && restore "files outside the allowed ones changed: $OTHER"
(cd "$HERE" && /usr/bin/python3 -I 00_make_template.py && /usr/bin/python3 -I 02_build_html.py) || restore "rebuild failed"
AFTER="$("$HERE/check_pages.sh" | sort)" || restore "page check failed (JS error)"
[ "$BEFORE" == "$AFTER" ] || restore "paper counts changed: before [$BEFORE] after [$AFTER]"
grep -q "pn-sort-" "$HERE/template.html" || restore "sorting code not found in template"
grep -qi "except" "$HERE/template.html" || restore "tag 'except' mode not found in template"
grep -q "Verdana" "$HERE/template.html" || restore "Verdana font option not found in template"

git add $ALLOWED papers/*/paper_notes_*.html "notes_builder/tasks/${NAME}.md"
git commit -q -m "Pages: sorting (author/year), tag filter (only/except) and font choice (Verdana)

Done by the one-time task notes_builder/tasks/${NAME}.md; checked by run_task_once.sh
(rebuild, node --check on every page, paper counts unchanged)." && echo "COMMITTED $(git log --oneline -1)"
touch "$HERE/tasks/.${NAME}.done"; remove_cron
echo "=== $(date '+%F %T') done (not pushed)"
