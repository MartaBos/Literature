#!/usr/bin/env python3
"""Download the PDFs of a publicly shared Google Drive folder and identify each paper.

Lists the folder through Drive's public embedded view (no login, works for
"anyone with the link" folders), downloads every PDF into <outdir>, reads the DOI
from the PDF (metadata, then page-1 text via `mutool`) and looks the DOI up in Crossref.
Prints a TSV skeleton to fill in as batches/<batch>_assign.tsv.

Downloaded files are untrusted data: they go into their own folder and are only read.

Usage: python3 -I 14_fetch_drive_folder.py <drive_folder_id> <outdir>
"""
import html
import json
import pathlib
import re
import subprocess
import sys
import time
import urllib.parse
import urllib.request

UA = {"User-Agent": "Mozilla/5.0 literature-notes-script/1.0"}


def get(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=120) as r:
        return r.read()


def find_doi(pdf):
    """DOI printed on page 1 first (PDF metadata can be wrong: Silva 2023 carried another paper's DOI),
    then page 2, then the PDF metadata."""
    for pages in ("1", "2"):
        txt = subprocess.run(["mutool", "draw", "-F", "txt", "-o", "-", str(pdf), pages],
                             capture_output=True, text=True).stdout
        m = re.search(r"(?:doi\.org/|doi:?\s*)(10\.\d{4,9}/[^\s,;]+)", txt, re.I)
        if m:
            return m.group(1).rstrip(".)")
    raw = pdf.read_bytes()
    for pat in (rb"<prism:doi>\s*(10\.\d{4,9}/[^<\s]+)", rb"/doi\s*\((10\.\d{4,9}/[^)\s]+)\)"):
        m = re.search(pat, raw)
        if m:
            return m.group(1).decode("latin-1")
    return ""


def list_folder(folder_id, prefix=""):
    """(file_id, relative name) for every file, going into subfolders (first version missed them)."""
    page = get(f"https://drive.google.com/embeddedfolderview?id={folder_id}").decode("utf-8", "replace")
    out = []
    for kind, fid, name in re.findall(
            r'href="https://drive\.google\.com/(file/d|drive/folders)/([\w-]+)[^"]*".*?class="flip-entry-title">([^<]+)<',
            page, re.S):
        name = html.unescape(name).strip()
        if kind == "drive/folders":
            out += list_folder(fid, prefix + name + "/")
        else:
            out.append((fid, prefix + name))
    return out


def main():
    folder_id, outdir = sys.argv[1], pathlib.Path(sys.argv[2])
    outdir.mkdir(parents=True, exist_ok=True)
    items = list_folder(folder_id)
    print("drive_file\tdoi\tfirst_author\tyear\tjournal\ttitle")
    for fid, name in items:
        dest = outdir / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        if not dest.exists():
            data = get(f"https://drive.google.com/uc?export=download&id={fid}")
            if data[:5] != b"%PDF-":
                print(f"{name}\tNOT A PDF (download page?)")
                continue
            dest.write_bytes(data)
        doi = find_doi(dest)
        meta = {}
        if doi:
            try:
                meta = json.loads(get("https://api.crossref.org/works/" + urllib.parse.quote(doi)))["message"]
            except Exception:
                pass
        au = (meta.get("author") or [{}])[0].get("family", "")
        yr = ((meta.get("issued") or {}).get("date-parts") or [[""]])[0][0]
        jr = " ".join(meta.get("container-title") or [])
        ti = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", " ".join(meta.get("title") or [])))
        print(f"{name}\t{doi}\t{au}\t{yr}\t{jr}\t{ti}")
        time.sleep(0.5)


if __name__ == "__main__":
    main()
