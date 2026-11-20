#!/usr/bin/env python3
"""Add already-downloaded PDFs (e.g. from a shared Drive folder) to the literature + catalog.

Input : batches/<batch>_assign.tsv  columns: source, folder, subcategory, filename, doi, tags
        source files in batches/<batch>_files/
Output: papers/<folder>/<filename>  (copied; never overwritten)
        notes/catalog.json entries  (title from Crossref, subcategory, tags, shared by, DOI link)

Usage: python3 -I 15_add_local_pdfs.py <batch> --shared-by Damir --year 2026
"""
import argparse, csv, json, pathlib, re, shutil, urllib.parse, urllib.request
HERE = pathlib.Path(__file__).resolve().parent
CFG = json.loads((HERE / "config.json").read_text())
PAPERS = pathlib.Path(CFG["papers_root"]); CATALOG = pathlib.Path(CFG["notes_root"]) / "catalog.json"
ap = argparse.ArgumentParser(); ap.add_argument("batch"); ap.add_argument("--shared-by", default=""); ap.add_argument("--year", default="")
a = ap.parse_args()
catalog = json.loads(CATALOG.read_text()) if CATALOG.exists() else {}
rows = csv.DictReader((l for l in open(HERE / "batches" / f"{a.batch}_assign.tsv") if not l.startswith("#")), delimiter="\t")
for r in rows:
    src = HERE / "batches" / f"{a.batch}_files" / r["source"]
    dest = PAPERS / r["folder"] / r["filename"]
    if src.read_bytes()[:5] != b"%PDF-":
        print("not a PDF, skipped:", src); continue
    status = "already there" if dest.exists() else "copied"
    if not dest.exists():
        shutil.copyfile(src, dest)
    title = ""
    try:
        req = urllib.request.Request("https://api.crossref.org/works/" + urllib.parse.quote(r["doi"]),
                                     headers={"User-Agent": "literature-notes-script/1.0"})
        title = " ".join(json.loads(urllib.request.urlopen(req, timeout=40).read())["message"].get("title") or [])
    except Exception:
        pass
    key = f"{r['folder']}/{dest.stem}"
    prev = catalog.get(key, {})
    new = {"title": re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", title)).strip() or prev.get("title", ""),
           "category": r["subcategory"], "shared_by": a.shared_by or prev.get("shared_by", ""),
           "shared_year": a.year or prev.get("shared_year", ""),
           "link": prev.get("link_override") or prev.get("link") or (f"https://doi.org/{r['doi']}" if r["doi"] else ""),
           "pdf_from": f"Google Drive ({a.batch})"}
    tags = [t.strip() for t in (r.get("tags") or "").split(",") if t.strip()]
    if tags:
        new["tags"] = tags
    # keep earlier fields (provided link, preprint DOI, batch, tags, source notes) and update the rest
    catalog[key] = {**{"provided_link": "Google Drive folder (shared)", "preprint_doi": None, "batch": a.batch}, **prev, **new}
    print(f"{status:14} {key}")
CATALOG.write_text(json.dumps(catalog, ensure_ascii=False, indent=1) + "\n")
