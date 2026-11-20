#!/usr/bin/env bash
# Check every built notes page: JavaScript syntax (node --check) and the number of papers in DATA.
# Prints "<folder> <n papers>" per page; exit code 1 if any page is broken.
HERE="$(cd "$(dirname "$0")" && pwd)"
PAPERS=$(/usr/bin/python3 -I -c "import json; print(json.load(open('$HERE/config.json'))['papers_root'])")
mkdir -p "$HERE/work"
status=0
for f in "$PAPERS"/*/paper_notes_*.html; do
    /usr/bin/python3 -I - "$f" "$HERE/work/check_page.js" <<'EOF' || status=1
import json, re, sys
s = open(sys.argv[1], encoding="utf-8").read()
open(sys.argv[2], "w", encoding="utf-8").write(re.search(r"<script>(.*)</script>", s, re.S).group(1))
d = json.loads(re.search(r"const DATA = (\{.*?\});\n", s, re.S).group(1))
print(sys.argv[1].split("/")[-2], len(d["papers"]))
EOF
    /usr/bin/node --check "$HERE/work/check_page.js" || { echo "JS ERROR in $f"; status=1; }
done
exit $status
