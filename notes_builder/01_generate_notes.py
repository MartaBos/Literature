#!/usr/bin/env python3
"""Write Q&A notes (one JSON per paper) for every PDF that has no notes yet.

Scans every subfolder of papers_root (config.json). For a PDF
    papers/<folder>/<name>.pdf
the notes go to
    notes/<folder>/<name>.json
A PDF whose JSON already exists is skipped, so notes are written once and your
own edits to a JSON file are never overwritten.

Notes are written by Claude Code in headless mode (`claude -p`) with only the
Read tool available: it can read the PDF but cannot run commands, edit files or
go online. Its reply (one JSON object) is checked here and saved by this script.

A failed paper gets a log in notes/_failed/ and is retried on the next run.

Usage:
  python3 -I 01_generate_notes.py              # all new PDFs (up to max_new_papers_per_run)
  python3 -I 01_generate_notes.py --dry-run    # only list what would be done
  python3 -I 01_generate_notes.py --only papers/drerio/X.pdf
"""
import argparse
import datetime as dt
import glob
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
CFG = json.loads((HERE / "config.json").read_text())
PAPERS = pathlib.Path(CFG["papers_root"])
NOTES = pathlib.Path(CFG["notes_root"])
TODAY = dt.date.today().isoformat()


def log(*a):
    print(f"[{dt.datetime.now():%H:%M:%S}]", *a, flush=True)


def find_claude():
    """CLAUDE_BIN env var > `claude` on PATH > newest VS Code extension binary."""
    if os.environ.get("CLAUDE_BIN"):
        return os.environ["CLAUDE_BIN"]
    if shutil.which("claude"):
        return shutil.which("claude")
    pat = os.path.expanduser("~/.vscode-server/extensions/anthropic.claude-code-*/resources/native-binary/claude")

    def ver(p):
        m = re.search(r"claude-code-([\d.]+)", p)
        return tuple(int(x) for x in m.group(1).strip(".").split(".")) if m else ()
    hits = sorted(glob.glob(pat), key=ver)
    if not hits:
        sys.exit("Claude Code binary not found (set CLAUDE_BIN in run_weekly.sh)")
    return hits[-1]


def folder_of(pdf):
    return pdf.relative_to(PAPERS).parts[0]


def notes_path(pdf):
    return NOTES / folder_of(pdf) / (pdf.stem + ".json")


def all_pdfs():
    out = []
    for d in sorted(p for p in PAPERS.iterdir() if p.is_dir() and not p.name.startswith((".", "_"))):
        pdfs = sorted(p for p in d.rglob("*") if p.is_file() and p.suffix.lower() == ".pdf")
        stems = {p.stem for p in pdfs}
        txts = sorted(p for p in d.rglob("*.txt") if p.stem not in stems)  # abstract-only sources
        out += sorted(pdfs + txts)
    return out


def doi_from_pdf(pdf):
    """DOI from the PDF's own metadata (more reliable than asking the model)."""
    raw = pdf.read_bytes()
    for pat in (rb"<prism:doi>\s*(10\.\d{4,9}/[^<\s]+)", rb"/doi\s*\((10\.\d{4,9}/[^)\s]+)\)",
                rb"doi:\s*(10\.\d{4,9}/[^<>\"()\s]+)"):
        m = re.search(pat, raw)
        if m:
            return m.group(1).decode("latin-1").rstrip(".")
    return ""


def clean_str(x):
    return re.sub(r"\s+", " ", str(x or "")).strip()


def validate(obj, min_qa=5):
    """Normalise Claude's JSON into the page's item format. Raises ValueError."""
    if not isinstance(obj, dict) or not isinstance(obj.get("items"), list):
        raise ValueError("reply has no 'items' list")
    items = []
    for it in obj["items"]:
        if not isinstance(it, dict):
            continue
        sec = clean_str(it.get("section")) or "Notes"
        if it.get("type") == "note":
            if clean_str(it.get("text")):
                items.append({"type": "note", "section": sec, "text": clean_str(it["text"])})
            continue
        q, a = clean_str(it.get("q")), clean_str(it.get("a"))
        if not q or not a:
            continue
        kw = it.get("kw") or []
        kw = [clean_str(k) for k in (kw if isinstance(kw, list) else [kw]) if clean_str(k)]
        items.append({"type": "qa", "section": sec, "q": q, "a": a, "kw": kw[:4],
                      "info": clean_str(it.get("info")), "concl": clean_str(it.get("concl"))})
    n_qa = sum(i["type"] == "qa" for i in items)
    if n_qa < min_qa:
        raise ValueError(f"only {n_qa} usable questions")
    return items


def paper_id(obj, pdf):
    pid = re.sub(r"[^A-Za-z0-9_-]", "", clean_str(obj.get("id")).replace(" ", "_"))
    if not re.match(r"^[A-Za-z-]+_\d{4}[a-z]?$", pid):  # fall back to the file name
        pid = "_".join(pdf.stem.split("_")[:2])
    return pid


def extract_json(text):
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip())
    a, b = text.find("{"), text.rfind("}")
    if a < 0 or b < a:
        raise ValueError("no JSON object in reply")
    return json.loads(text[a:b + 1])


MAX_PDF_BYTES = 18_000_000  # Claude's Read tool opens whole PDFs only up to ~20 MB


def text_copy(pdf):
    """Plain text of a large PDF (big figures make some papers 25-70 MB), via mutool."""
    out = HERE / "work" / "text" / (pdf.stem + ".txt")
    out.parent.mkdir(parents=True, exist_ok=True)
    if not out.exists() or out.stat().st_mtime < pdf.stat().st_mtime:
        subprocess.run(["mutool", "draw", "-F", "txt", "-o", str(out), str(pdf)],
                       capture_output=True, check=True)
    return out


def run_claude(claude, pdf):
    prompt = (HERE / "prompt.md").read_text()
    cat_entry = (json.loads((NOTES / "catalog.json").read_text()) if (NOTES / "catalog.json").exists() else {}
                 ).get(f"{folder_of(pdf)}/{pdf.stem}", {})
    if pdf.suffix.lower() == ".txt" and cat_entry.get("fulltext_txt"):
        prompt = prompt.replace("{{PDF_PATH}}", str(pdf)) + (
            "\n\nNote: this file is the full text of the article from PubMed Central (no PDF was available). "
            "Read the whole file with the Read tool (use offset/limit for long files); figures are not included.")
        add_dir = pdf.parent
    elif pdf.suffix.lower() == ".txt":
        prompt = prompt.replace("{{PDF_PATH}}", str(pdf)) + (
            "\n\nImportant: this file is NOT the full paper, only its publicly available abstract and "
            "metadata (the full text was not accessible). Write only what this text supports: about 5 to 12 "
            "items, all in section \"Abstract\" (keywords may go in kw). Do not add details from memory.")
        add_dir = pdf.parent
    elif pdf.stat().st_size > MAX_PDF_BYTES:
        src = text_copy(pdf)
        prompt = prompt.replace("{{PDF_PATH}}", str(src)) + (
            "\n\nNote: the file above is the plain text extracted from the paper's PDF "
            f"({pdf.name}), because the PDF itself is too large to open. Read the whole text file "
            "with the Read tool (use offset/limit for long files); figures are not included.")
        add_dir = src.parent
    else:
        prompt = prompt.replace("{{PDF_PATH}}", str(pdf))
        add_dir = pdf.parent
    if cat_entry.get("prompt_extra"):  # per-paper extra instruction from catalog.json
        prompt += "\n\nAdditional instruction for this paper: " + cat_entry["prompt_extra"]
    cmd = [claude, "-p", prompt,
           "--tools", "Read", "--allowedTools", "Read",
           "--strict-mcp-config", "--no-session-persistence",
           "--output-format", "json", "--add-dir", str(add_dir)]
    if CFG.get("claude_model"):
        cmd += ["--model", CFG["claude_model"]]
    work = HERE / "work"
    work.mkdir(exist_ok=True)
    env = dict(os.environ, CLAUDE_CODE_MAX_OUTPUT_TOKENS="32000")  # long papers -> long JSON reply
    return subprocess.run(cmd, cwd=work, stdin=subprocess.DEVNULL, capture_output=True,
                          text=True, timeout=CFG["timeout_minutes"] * 60, env=env)


USAGE_LIMIT_HIT = False  # set when Claude reports the plan's usage limit; remaining papers wait


def process(claude, pdf):
    global USAGE_LIMIT_HIT
    out_path = notes_path(pdf)
    if USAGE_LIMIT_HIT:
        log(f"skipped (usage limit reached, next run): {pdf.relative_to(PAPERS)}")
        return False
    log(f"writing notes: {pdf.relative_to(PAPERS)}")
    proc = None
    try:
        proc = run_claude(claude, pdf)
        wrapper = json.loads(proc.stdout)
        if wrapper.get("is_error"):
            raise ValueError(f"claude error: {wrapper.get('result')}")
        obj = extract_json(wrapper["result"])
        full_txt = (json.loads((NOTES / "catalog.json").read_text()).get(f"{folder_of(pdf)}/{pdf.stem}", {})
                    .get("fulltext_txt") if (NOTES / "catalog.json").exists() else False)
        items = validate(obj, min_qa=3 if pdf.suffix.lower() == ".txt" and not full_txt else 5)
    except Exception as e:  # keep a record and retry next week
        if re.search(r"hit your .*limit|usage limit|rate limit", str(e), re.I):
            USAGE_LIMIT_HIT = True
            log(f"  USAGE LIMIT reached ({e}); stopping, the rest is retried next run")
            return False
        fail_dir = NOTES / "_failed"
        fail_dir.mkdir(parents=True, exist_ok=True)
        flog = fail_dir / f"{folder_of(pdf)}__{pdf.stem}__{TODAY}.log"
        flog.write_text(f"pdf: {pdf}\nerror: {e!r}\n\n--- stdout ---\n{getattr(proc, 'stdout', '')}"
                        f"\n\n--- stderr ---\n{getattr(proc, 'stderr', '')}\n")
        log(f"  FAILED ({e}); details in {flog}")
        return False

    doi = doi_from_pdf(pdf) or clean_str(obj.get("doi"))
    catalog = json.loads((NOTES / "catalog.json").read_text()) if (NOTES / "catalog.json").exists() else {}
    cat = catalog.get(f"{folder_of(pdf)}/{pdf.stem}", {})
    record = {
        "id": paper_id(obj, pdf),
        "title": clean_str(obj.get("title")) or cat.get("title") or pdf.stem,
        "link": cat.get("link") or (f"https://doi.org/{doi}" if doi else ""),
        "category": None,   # null = folder default from config.json; set a name to override
        "note": "",         # your own one-line opinion, shown under the title
        "source_pdf": str(pdf.relative_to(PAPERS.parent)),
        "added": TODAY,
        "generated_by": f"claude -p ({CFG.get('claude_model') or 'default model'})",
        "source_note": cat.get("source_note", ""),
        "items": items,
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = out_path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(record, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    tmp.replace(out_path)
    n_qa = sum(i["type"] == "qa" for i in items)
    log(f"  ok: {record['id']}, {n_qa} questions, cost ${wrapper.get('total_cost_usd', 0):.2f} -> {out_path}")
    return True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--only", help="one PDF path")
    ap.add_argument("--limit", type=int, help="max papers this run (0 = all); default from config.json")
    ap.add_argument("--jobs", type=int, default=1, help="papers processed in parallel (default 1)")
    args = ap.parse_args()

    pdfs = [pathlib.Path(args.only).resolve()] if args.only else all_pdfs()
    todo = [p for p in pdfs if not notes_path(p).exists()]
    catalog = json.loads((NOTES / "catalog.json").read_text()) if (NOTES / "catalog.json").exists() else {}
    todo.sort(key=lambda p: "Important" not in catalog.get(f"{folder_of(p)}/{p.stem}", {}).get("tags", []))
    log(f"{len(pdfs)} PDFs in {PAPERS}, {len(todo)} without notes")
    limit = args.limit if args.limit is not None else CFG.get("max_new_papers_per_run")
    limit = limit or len(todo)
    if len(todo) > limit:
        log(f"  doing the first {limit} this run; the rest wait for the next run")
        todo = todo[:limit]
    if args.dry_run:
        for p in todo:
            print("  would process:", p.relative_to(PAPERS))
        return 0
    if not todo:
        return 0
    claude = find_claude()
    log(f"using {claude}")
    if args.jobs > 1:
        from concurrent.futures import ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=args.jobs) as ex:
            ok = sum(ex.map(lambda p: process(claude, p), todo))
    else:
        ok = sum(process(claude, p) for p in todo)
    log(f"done: {ok}/{len(todo)} papers got notes")
    return 0 if ok == len(todo) else 1


if __name__ == "__main__":
    sys.exit(main())
