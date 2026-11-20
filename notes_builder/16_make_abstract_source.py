#!/usr/bin/env python3
"""Make a text source for a paper whose full text is not accessible.

Collects the publicly available information (PubMed record: title, authors, journal,
structured abstract, keywords, MeSH terms; Crossref abstract if PubMed has none or it differs)
and writes  papers/<folder>/<stem>.txt  with a header saying it is NOT the full paper.
01_generate_notes.py then writes (fewer) notes from it, and the page shows the catalog's
"source_note" so it is clear the notes are not from the full text.

Usage: python3 -I 16_make_abstract_source.py <folder> <stem> <doi>
"""
import json
import pathlib
import re
import sys
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

HERE = pathlib.Path(__file__).resolve().parent
CFG = json.loads((HERE / "config.json").read_text())
PAPERS = pathlib.Path(CFG["papers_root"])
CATALOG = pathlib.Path(CFG["notes_root"]) / "catalog.json"
UA = {"User-Agent": "literature-notes-script/1.0"}


def get(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
        return r.read().decode("utf-8", "replace")


def text(el):
    return re.sub(r"\s+", " ", "".join(el.itertext())).strip() if el is not None else ""


folder, stem, doi = sys.argv[1:4]
ids = json.loads(get("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pubmed&retmode=json&term="
                     + urllib.parse.quote(f"{doi}[doi]")))["esearchresult"]["idlist"]
lines = ["PUBLICLY AVAILABLE INFORMATION ONLY - NOT THE FULL PAPER",
         "(the full text was not accessible; this is the abstract and metadata from PubMed/Crossref)", ""]
abstract_pm = ""
if ids:
    art = ET.fromstring(get(f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=pubmed&id={ids[0]}&retmode=xml"))
    a = art.find(".//Article")
    authors = [f"{x.findtext('LastName', '')} {x.findtext('Initials', '')}".strip() for x in a.findall(".//Author")]
    lines += [f"Title: {text(a.find('ArticleTitle'))}",
              f"Authors: {', '.join(authors[:12])}{' et al.' if len(authors) > 12 else ''}",
              f"Journal: {text(a.find('Journal/Title'))} ({a.findtext('Journal/JournalIssue/PubDate/Year', '')})",
              f"DOI: {doi}   PMID: {ids[0]}", "", "ABSTRACT"]
    for sec in a.findall(".//Abstract/AbstractText"):
        label = sec.get("Label")
        lines.append((f"{label}: " if label else "") + text(sec))
        abstract_pm += text(sec)
    kws = [text(k) for k in art.findall(".//KeywordList/Keyword")]
    mesh = [text(m.find("DescriptorName")) for m in art.findall(".//MeshHeading")]
    if kws:
        lines += ["", "Keywords: " + "; ".join(kws)]
    if mesh:
        lines += ["MeSH terms: " + "; ".join(mesh)]
cr = json.loads(get("https://api.crossref.org/works/" + urllib.parse.quote(doi)))["message"]
cr_abs = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", cr.get("abstract", "") or "")).strip()
if cr_abs and cr_abs[:80] not in abstract_pm:
    lines += ["", "ABSTRACT (publisher, via Crossref)", cr_abs]
if not ids:
    lines += [f"Title: {' '.join(cr.get('title') or [])}", f"DOI: {doi}"]

out = PAPERS / folder / f"{stem}.txt"
out.write_text("\n".join(lines) + "\n", encoding="utf-8")
cat = json.loads(CATALOG.read_text())
cat.setdefault(f"{folder}/{stem}", {})["source_note"] = (
    "Not the full paper: no access to the full text, so these notes are based only on the publicly "
    "available abstract and metadata (PubMed). Details from the main text and figures are missing.")
cat[f"{folder}/{stem}"]["pdf_from"] = "no PDF (abstract source, 16_make_abstract_source.py)"
CATALOG.write_text(json.dumps(cat, ensure_ascii=False, indent=1) + "\n")
print(f"wrote {out} ({len(lines)} lines)")
