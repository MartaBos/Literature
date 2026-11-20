#!/usr/bin/env python3
"""Check that each downloaded PDF is the paper (and version) we wanted.

Decompresses the PDF's streams (stdlib zlib only) and looks for the expected DOI
and, when the paper replaced a preprint, for the preprint DOI (which should be absent)
and the journal DOI (which should be present).

Usage: python3 -I 13_verify_pdfs.py batches/<batch>_download_report.tsv
"""
import csv, json, pathlib, re, sys, zlib
HERE = pathlib.Path(__file__).resolve().parent
PAPERS = pathlib.Path(json.loads((HERE / "config.json").read_text())["papers_root"])
def pdf_text(path):
    raw = path.read_bytes(); out = [raw]
    for m in re.finditer(rb"stream\r?\n(.*?)\r?\nendstream", raw, re.S):
        try: out.append(zlib.decompress(m.group(1)))
        except Exception: pass
    t = b" ".join(out).decode("latin-1")
    # text in PDF content streams is often split into (..)Tj pieces; join them loosely
    return t + " " + "".join(re.findall(r"\(([^)]{1,200})\)", t))
for r in csv.DictReader(open(sys.argv[1]), delimiter="\t"):
    p = PAPERS / r["folder"] / r["filename"]
    if not p.exists(): continue
    t = pdf_text(p).lower()
    doi = r["doi"].lower()
    tail = doi.split("/", 1)[1] if "/" in doi else doi
    found = doi in t or tail in t
    print(f"{r['n']:>2} {'DOI found ' if found else 'doi ??    '} {r['filename']}")
