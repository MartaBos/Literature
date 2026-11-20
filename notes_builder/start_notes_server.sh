#!/usr/bin/env bash
# Start the paper-notes server (if it is not running yet) and print the link to open.
# Also run at boot by cron (@reboot). Stop: kill "$(cat .server.pid)".
HERE="$(cd "$(dirname "$0")" && pwd)"
PORT=$(/usr/bin/python3 -I -c "import json; print(json.load(open('$HERE/config.json')).get('server_port', 21060))")
mkdir -p "$HERE/logs"
if ! (exec 3<>/dev/tcp/127.0.0.1/$PORT) 2>/dev/null; then
    nohup /usr/bin/python3 -I "$HERE/serve_notes.py" >> "$HERE/logs/server.log" 2>&1 &
    sleep 1
fi
echo "Paper notes: http://localhost:$PORT/?t=$(cat "$HERE/.server_token")"
echo "(VS Code: Ports tab -> Forward a Port -> $PORT, then open the link in Simple Browser or your browser)"
