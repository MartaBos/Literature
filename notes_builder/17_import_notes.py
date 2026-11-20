#!/usr/bin/env python3
"""Import notes that were prepared elsewhere (no Claude usage) together with their paper.

Input : a notes JSON in the page format ({"title", "link", "items": [{type: qa|note, section, q, a, kw,
        info, concl} | {type: note, section, text}]}) and the paper PDF.
Does  : checks and normalises the items (same rules as 01_generate_notes.py), checks the DOI link
        against the PDF's page 1 and Crossref, copies the PDF to papers/<folder>/<filename>, writes
        notes/<folder>/<stem>.json and a notes/catalog.json entry (subcategory, tags, link).
        Because the notes JSON then exists, the weekly job never regenerates notes for this paper.

Usage: python3 -I 17_import_notes.py <notes.json> <paper.pdf> <folder> "<subcategory>" <filename.pdf> \
           [--tags "External notes"] [--shared-by NAME --year YYYY]
"""
import argparse
import datetime as dt
import json
import pathlib
import re
import shutil
import subprocess
import urllib.parse
import urllib.request

HERE = pathlib.Path(__file__).resolve().parent
CFG = json.loads((HERE / "config.json").read_text())
PAPERS = pathlib.Path(CFG["papers_root"])
NOTES = pathlib.Path(CFG["notes_root"])
CATALOG = NOTES / "catalog.json"


def clean(x):
    return re.sub(r"\s+", " ", str(x or "")).strip()


def normalise(items):
    out = []
    for it in items:
        if not isinstance(it, dict):
            continue
        sec = clean(it.get("section")) or "Notes"
        if it.get("type") == "note":
            if clean(it.get("text")):
                out.append({"type": "note", "section": sec, "text": clean(it["text"])})
            continue
        q, a = clean(it.get("q")), clean(it.get("a"))
        if q and a:
            kw = it.get("kw") or []
            kw = [clean(k) for k in (kw if isinstance(kw, list) else [kw]) if clean(k)]
            out.append({"type": "qa", "section": sec, "q": q, "a": a, "kw": kw,
                        "info": clean(it.get("info")), "concl": clean(it.get("concl"))})
    return out


def page1_doi(pdf):
    txt = subprocess.run(["mutool", "draw", "-F", "txt", "-o", "-", str(pdf), "1"],
                         capture_output=True, text=True).stdout
    m = re.search(r"(?:doi\.org/|doi:?\s*)(10\.\d{4,9}/[^\s,;]+)", txt, re.I)
    return m.group(1).rstrip(".)").lower() if m else ""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("notes"); ap.add_argument("pdf"); ap.add_argument("folder")
    ap.add_argument("subcategory"); ap.add_argument("filename")
    ap.add_argument("--tags", default=""); ap.add_argument("--shared-by", default=""); ap.add_argument("--year", default="")
    a = ap.parse_args()

    src = json.loads(pathlib.Path(a.notes).read_text(encoding="utf-8"))
    items = normalise(src.get("items") or [])
    n_qa = sum(i["type"] == "qa" for i in items)
    print(f"notes: {n_qa} questions, {len(items) - n_qa} notes (dropped {len(src.get('items') or []) - len(items)} unusable items)")

    pdf = pathlib.Path(a.pdf)
    if pdf.read_bytes()[:5] != b"%PDF-":
        raise SystemExit("not a PDF: " + str(pdf))
    doi_pdf = page1_doi(pdf)
    doi_notes = re.sub(r"^https?://(dx\.)?doi\.org/", "", src.get("link", "")).lower()
    if doi_pdf and doi_notes and doi_notes.startswith(doi_pdf) and doi_notes != doi_pdf:
        doi_pdf = doi_notes  # DOI wrapped onto the next line on page 1 (e.g. Annual Reviews)
    doi = doi_pdf or doi_notes
    if doi_pdf and doi_notes and doi_pdf != doi_notes:
        print(f"WARNING: DOI in notes ({doi_notes}) differs from PDF page 1 ({doi_pdf}); using the PDF's")
    meta = {}
    for d in dict.fromkeys(x for x in (doi, doi_notes) if x):  # try the PDF's DOI, then the notes' DOI
        try:
            meta = json.loads(urllib.request.urlopen(urllib.request.Request(
                "https://api.crossref.org/works/" + urllib.parse.quote(d),
                headers={"User-Agent": "literature-notes-script/1.0"}), timeout=40).read())["message"]
            doi = d
            break
        except Exception as e:
            print(f"Crossref has no record for {d} ({e})")
    title = clean(re.sub(r"<[^>]+>", "", " ".join(meta.get("title") or []))) or clean(src.get("title"))
    print(f"paper: {title} | https://doi.org/{doi} | {' '.join(meta.get('container-title') or [])} | type {meta.get('type')}")

    dest = PAPERS / a.folder / a.filename
    if not dest.exists():
        shutil.copyfile(pdf, dest)
    stem = dest.stem
    record = {
        "id": clean(src.get("id")) or "_".join(stem.split("_")[:2]),
        "title": title,
        "link": f"https://doi.org/{doi}" if doi else clean(src.get("link")),
        "category": None,
        "note": clean(src.get("note")),
        "source_pdf": str(dest.relative_to(PAPERS.parent)),
        "added": dt.date.today().isoformat(),
        "generated_by": clean(src.get("generated_by")) or "imported",
        "imported_from": str(pathlib.Path(a.notes).resolve()),
        "source_note": clean(src.get("source_note")),
        "items": items,
    }
    out = NOTES / a.folder / f"{stem}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    if out.exists():
        raise SystemExit(f"notes already exist, not overwriting: {out}")
    out.write_text(json.dumps(record, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")

    cat = json.loads(CATALOG.read_text()) if CATALOG.exists() else {}
    key = f"{a.folder}/{stem}"
    entry = {**cat.get(key, {}), "title": title, "category": a.subcategory,
             "link": record["link"], "provided_link": "Drive folder (paper + prepared notes)",
             "preprint_doi": None, "pdf_from": f"Drive, notes imported ({pathlib.Path(a.notes).name})",
             "shared_by": a.shared_by, "shared_year": a.year}
    tags = [t.strip() for t in a.tags.split(",") if t.strip()]
    if tags:
        entry["tags"] = tags
    cat[key] = entry
    CATALOG.write_text(json.dumps(cat, ensure_ascii=False, indent=1) + "\n")
    print(f"wrote {dest}\n      {out}\n      catalog: {key}")


if __name__ == "__main__":
    main()
