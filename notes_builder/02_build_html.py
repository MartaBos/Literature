#!/usr/bin/env python3
"""Build one "Paper notes" HTML page per literature subfolder.

For every subfolder of papers_root (config.json; folders starting with _ or . are skipped)
this writes
    papers/<folder>/paper_notes_<folder>.html
from template.html plus
  * every notes/<folder>/*.json            papers with notes
  * every PDF in the folder without JSON   listed as "no notes yet"
  * every notes/catalog.json entry for this folder whose PDF is not there yet
                                           listed as "PDF missing" (with the file name to save it as)

Per paper, the subcategory (coloured group) is taken from, in order:
  "category" in the paper's JSON (hand edit) > catalog.json > the folder default in config.json.
"Shared by" and the preprint link come from catalog.json.
Only reads; safe to re-run at any time.

Usage: python3 -I 02_build_html.py
"""
import datetime as dt
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
CFG = json.loads((HERE / "config.json").read_text())
PAPERS = pathlib.Path(CFG["papers_root"])
NOTES = pathlib.Path(CFG["notes_root"])
TEMPLATE = (HERE / "template.html").read_text(encoding="utf-8")
CATALOG = json.loads((NOTES / "catalog.json").read_text()) if (NOTES / "catalog.json").exists() else {}
COMMENTS = json.loads((NOTES / "comments.json").read_text()) if (NOTES / "comments.json").exists() else {}


def folder_info(name):
    f = CFG["folders"].get(name, {})
    label = f.get("label") or name.replace("_", " ").capitalize()
    subcats = f.get("subcategories") or {}
    return label, f.get("category") or next(iter(subcats), label), subcats


def extras(folder, stem):
    c = CATALOG.get(f"{folder}/{stem}", {})
    shared = " · ".join(x for x in (c.get("shared_by"), str(c.get("shared_year") or "")) if x)
    pre = c.get("preprint_doi")
    return c, {"shared": shared, "preprint": f"https://doi.org/{pre}" if pre else "",
               "tags": c.get("tags") or [], "source_note": c.get("source_note", "")}


def build(folder):
    label, default_cat, subcats = folder_info(folder.name)
    papers, seen_ids, seen_stems = [], set(), set()

    def add(p):
        pid, n = p["id"], 2
        while p["id"] in seen_ids:          # keep ids unique (they key the "known" progress)
            p["id"] = f"{pid}_{n}"
            n += 1
        seen_ids.add(p["id"])
        papers.append(p)

    noted = []
    for jf in sorted((NOTES / folder.name).glob("*.json")):
        try:
            r = json.loads(jf.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            print(f"  skipping unreadable {jf}: {e}", file=sys.stderr)
            continue
        r["_stem"] = jf.stem
        seen_stems.add(jf.stem)
        noted.append(r)
    noted.sort(key=lambda r: (r.get("added", ""), r.get("id", "")), reverse=True)  # newest first
    for r in noted:
        c, ex = extras(folder.name, r["_stem"])
        add({"id": r.get("id") or "paper", "title": r.get("title", ""),
             "category": r.get("category") or c.get("category") or default_cat,
             "link": c.get("link") or r.get("link", ""), "note": r.get("note", ""),
             "source_pdf": r.get("source_pdf", ""), "items": r.get("items", []),
             "key": f"{folder.name}/{r['_stem']}", **ex})

    pending = []
    pdf_stems = set()
    srcs = sorted(p for p in folder.rglob("*") if p.is_file() and p.suffix.lower() == ".pdf")
    srcs += sorted(p for p in folder.rglob("*.txt") if p.stem not in {s.stem for s in srcs})  # abstract-only
    for pdf in srcs:
        pdf_stems.add(pdf.stem)
        if pdf.stem not in seen_stems:
            pending.append((pdf.stem, {"source_pdf": str(pdf.relative_to(PAPERS.parent))}))
    for key in sorted(CATALOG):
        f, stem = key.split("/", 1)
        if f == folder.name and stem not in pdf_stems and stem not in seen_stems:
            pending.append((stem, {"missing_pdf": f"papers/{f}/{stem}.pdf"}))
    for stem, more in pending:
        c, ex = extras(folder.name, stem)
        add({"id": "_".join(stem.split("_")[:2]), "title": c.get("title") or stem.replace("_", " "),
             "category": c.get("category") or default_cat, "link": c.get("link", ""), "note": "",
             "items": [], "key": f"{folder.name}/{stem}", **ex, **more})

    papers.sort(key=lambda p: "Important" not in p.get("tags", []))  # important papers first (stable)
    keys = {**CFG["categories"], **subcats}
    used = {p["category"] for p in papers}
    legend = list(subcats) + sorted(used - set(subcats))
    data = {"page": {"label": label, "folder": folder.name, "updated": dt.date.today().isoformat()},
            "legend": legend,
            "catKeys": {c: keys.get(c, "gen") for c in legend},
            "papers": papers,
            # last saved "My comments" (read-only when the page is opened as a file; live via serve_notes.py)
            "comments": {k: v for k, v in COMMENTS.items() if k.startswith(folder.name + "/")}}
    blob = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")  # safe inside <script>
    html = (TEMPLATE.replace("/*__DATA__*/null", blob)
            .replace("__PAGE_TITLE__", f"Paper notes · {label}")
            .replace("__PAGE_LABEL__", label))
    out = folder / CFG["html_name"].format(folder=folder.name)
    tmp = out.with_suffix(".html.tmp")
    tmp.write_text(html, encoding="utf-8")
    tmp.replace(out)
    out.chmod(0o600)  # pages embed your comments; abacus2 is shared
    nq = sum(i.get("type") == "qa" for p in papers for i in p["items"])
    nmiss = sum(bool(p.get("missing_pdf")) for p in papers)
    print(f"{out}: {len(papers)} papers ({len(noted)} with notes, {nmiss} PDF missing), {nq} questions")


def main():
    for folder in sorted(p for p in PAPERS.iterdir() if p.is_dir() and not p.name.startswith((".", "_"))):
        build(folder)


if __name__ == "__main__":
    main()
