#!/usr/bin/env python3
"""Download the papers of a batch into their folders and record them in notes/catalog.json.

Inputs : batches/<batch>_resolved.json   (from 10_resolve_links.py)
         batches/<batch>_assign.tsv      (folder / subcategory / file name, decided by hand)
Outputs: papers/<folder>/<filename>      (the PDF; the peer-reviewed version when one exists)
         notes/catalog.json              (per paper: subcategory, shared by, DOI link, preprint DOI)
         batches/<batch>_download_report.tsv

PDF sources tried, in order, for the final (peer-reviewed if available) DOI:
  1. PubMed Central open-data bucket on AWS (official PMC copy, no bot wall)
  2. bioRxiv / arXiv for preprints that have no journal version
  3. the publisher (nature.com, Springer/BMC)
  4. OpenAlex open-access locations (published or accepted version only)
A download only counts when the file starts with %PDF. Existing files are never overwritten.

Usage: python3 -I 11_download_papers.py 2026-11-17_damir --shared-by Damir --year 2026
"""
import argparse
import csv
import datetime as dt
import json
import pathlib
import re
import time
import urllib.parse
import urllib.request

HERE = pathlib.Path(__file__).resolve().parent
CFG = json.loads((HERE / "config.json").read_text())
PAPERS = pathlib.Path(CFG["papers_root"])
CATALOG = pathlib.Path(CFG["notes_root"]) / "catalog.json"
UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) literature-notes-script/1.0"}


def fetch(url, binary=True):
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=90) as r:
            data = r.read()
        return data if binary else data.decode("utf-8", "replace")
    except Exception:
        return None


def pmc_pdf_urls(doi):
    j = fetch("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pmc&retmode=json&retmax=12&term="
              + urllib.parse.quote(f"{doi}[doi]"), binary=False)
    ids = json.loads(j)["esearchresult"]["idlist"] if j else []
    urls = []
    for uid in ids[:12]:  # the search also returns papers that cite the DOI; check them all
        lst = fetch(f"https://pmc-oa-opendata.s3.amazonaws.com/?list-type=2&prefix=PMC{uid}.", binary=False) or ""
        keys = re.findall(r"<Key>(PMC\d+\.(\d+)/PMC\d+\.\d+\.pdf)</Key>", lst)
        keys.sort(key=lambda k: int(k[1]))
        for k in reversed(keys):
            # PMC also returns the *preprint* record for a journal DOI; accept only an exact DOI match
            meta = fetch(f"https://pmc-oa-opendata.s3.amazonaws.com/{k[0][:-4]}.json", binary=False)
            if meta and json.loads(meta).get("doi", "").lower() == doi.lower():
                urls.append(f"https://pmc-oa-opendata.s3.amazonaws.com/{k[0]}")
    return urls


def openalex_pdf_urls(doi, allow_preprint):
    j = fetch("https://api.openalex.org/works/doi:" + urllib.parse.quote(doi), binary=False)
    if not j:
        return []
    w = json.loads(j)
    ok = {"publishedVersion", "acceptedVersion"} | ({"submittedVersion"} if allow_preprint else set())
    return [l["pdf_url"] for l in w.get("locations", []) if l.get("pdf_url") and l.get("version") in ok]


def candidate_urls(doi, rec):
    d = doi.lower()
    urls = pmc_pdf_urls(d)
    if d.startswith(("10.64898/", "10.1101/")) and rec.get("preprint") and not rec.get("published_doi"):
        if rec.get("latest_version"):
            urls.append(f"https://www.biorxiv.org/content/{d}v{rec['latest_version']}.full.pdf")
        urls += [f"https://www.biorxiv.org/content/{d}v{v}.full.pdf" for v in (3, 2, 1)]  # newest that exists
    if d.startswith("10.48550/arxiv."):
        urls.append("https://arxiv.org/pdf/" + d.split("arxiv.")[1])
    if d.startswith("10.52202/"):  # NeurIPS proceedings: PDF link from the proceedings landing page
        j = fetch("https://api.openalex.org/works/doi:" + urllib.parse.quote(d), binary=False)
        for loc in (json.loads(j).get("locations", []) if j else []):
            lp = loc.get("landing_page_url") or ""
            if "proceedings.neurips.cc" in lp or "papers.nips.cc" in lp:
                page = fetch(lp, binary=False) or ""
                urls += ["https://proceedings.neurips.cc" + h if h.startswith("/") else h
                         for h in re.findall(r'href="([^"]+Paper[^"]*\.pdf)"', page)]
    if d.startswith("10.1038/"):
        urls.append(f"https://www.nature.com/articles/{d.split('/', 1)[1]}.pdf")
    if d.startswith("10.1186/"):
        urls.append(f"https://link.springer.com/content/pdf/{d}.pdf")
    is_preprint_doi = d.startswith(("10.64898/", "10.1101/", "10.48550/"))
    urls += [u for u in openalex_pdf_urls(d, allow_preprint=is_preprint_doi)
             if is_preprint_doi or "arxiv.org" not in u and "biorxiv.org" not in u]
    seen = set()
    return [u for u in urls if not (u in seen or seen.add(u))]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("batch")
    ap.add_argument("--shared-by", default="")
    ap.add_argument("--year", default=str(dt.date.today().year))
    a = ap.parse_args()

    resolved = json.loads((HERE / "batches" / f"{a.batch}_resolved.json").read_text())
    rows = [r for r in csv.DictReader((l for l in open(HERE / "batches" / f"{a.batch}_assign.tsv")
                                       if not l.startswith("#")), delimiter="\t")]
    catalog = json.loads(CATALOG.read_text()) if CATALOG.exists() else {}
    report = []
    for row in rows:
        rec = resolved[int(row["n"]) - 1]
        doi = (row.get("doi_override") or rec.get("final_doi") or "").strip().lower()
        dest = PAPERS / row["folder"] / row["filename"]
        key = f"{row['folder']}/{dest.stem}"
        prev = catalog.get(key) or {}
        replaced_preprint = bool(rec.get("preprint")) and doi != (rec.get("doi") or "").lower()
        title = (rec.get("published") or {}).get("title") or rec.get("title") or ""
        if replaced_preprint and not rec.get("published") and not doi.startswith("10.52202/"):
            cr = fetch("https://api.crossref.org/works/" + urllib.parse.quote(doi), binary=False)
            title = " ".join(json.loads(cr)["message"].get("title") or [title]) if cr else title
        catalog[key] = {
            "title": re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", title)).strip() or prev.get("title", ""),
            "category": row["subcategory"],
            "shared_by": a.shared_by, "shared_year": a.year,
            "link": prev.get("link_override") or (f"https://doi.org/{doi}" if doi else rec["link"]),
            "provided_link": rec["link"],
            "preprint_doi": rec.get("doi") if replaced_preprint else None,
            "batch": a.batch,
        }
        if prev.get("link_override"):  # hand-set link survives re-runs
            catalog[key]["link_override"] = prev["link_override"]
        if dest.exists():
            status, src = "already there", ""
        else:
            status, src = "NOT DOWNLOADED", ""
            for u in candidate_urls(doi, rec) if doi else []:
                data = fetch(u)
                if data and data[:5] == b"%PDF-" and len(data) > 30_000:
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    dest.write_bytes(data)
                    status, src = "downloaded", u
                    break
                time.sleep(0.5)
        print(f"{row['n']:>2} {status:15} {key}  {src}")
        report.append([row["n"], status, row["folder"], row["filename"], doi, src, rec["link"]])
        time.sleep(0.3)

    CATALOG.parent.mkdir(parents=True, exist_ok=True)
    CATALOG.write_text(json.dumps(catalog, ensure_ascii=False, indent=1) + "\n")
    with open(HERE / "batches" / f"{a.batch}_download_report.tsv", "w") as f:
        f.write("n\tstatus\tfolder\tfilename\tdoi\tsource\tprovided_link\n")
        for r in report:
            f.write("\t".join(map(str, r)) + "\n")
    print(f"\n{sum(r[1] == 'downloaded' for r in report)} downloaded, "
          f"{sum(r[1] == 'already there' for r in report)} already there, "
          f"{sum(r[1] == 'NOT DOWNLOADED' for r in report)} need a manual download")


if __name__ == "__main__":
    main()
