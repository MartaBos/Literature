#!/usr/bin/env python3
"""Resolve a list of paper links to DOIs + metadata, and find peer-reviewed versions of preprints.

Input : batches/<batch>_links.txt   (one URL per line, # comments allowed)
Output: batches/<batch>_resolved.json

For each link:
  1. get an identifier from the URL (DOI, bioRxiv DOI, arXiv id, Elsevier PII, X post)
  2. look up metadata (Crossref; bioRxiv API; arXiv API; PubMed for OUP page-style links)
  3. for preprints (bioRxiv / arXiv) look for the peer-reviewed version via
       - the bioRxiv API "published" field
       - Crossref relation "is-preprint-of"
       - arXiv journal_ref / DOI
       - a Crossref title search (same first author, title similarity >= 0.9, journal article)
  4. final_doi = the peer-reviewed DOI when one exists, else the original

Only public scholarly APIs are queried, with DOIs/titles only (no personal details).

Usage: python3 -I 10_resolve_links.py batches/2026-11-17_damir_links.txt
"""
import difflib
import json
import pathlib
import re
import sys
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

UA = {"User-Agent": "literature-notes-script/1.0"}


def get(url, as_json=True, tries=3):
    for i in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=40) as r:
                data = r.read()
            return json.loads(data) if as_json else data.decode("utf-8", "replace")
        except Exception as e:
            err = e
            time.sleep(2 * (i + 1))
    print(f"    ! {url}: {err}", file=sys.stderr)
    return None


def crossref(doi):
    j = get("https://api.crossref.org/works/" + urllib.parse.quote(doi))
    return j["message"] if j else None


def cr_summary(m):
    if not m:
        return {}
    auth = m.get("author") or [{}]
    date = (m.get("issued") or m.get("posted") or {}).get("date-parts", [[None]])[0]
    abstract = re.sub(r"<[^>]+>", " ", m.get("abstract", "") or "")
    return {"doi": m.get("DOI", "").lower(), "title": " ".join(m.get("title") or [""]).strip(),
            "first_author": auth[0].get("family", "") or auth[0].get("name", ""),
            "year": date[0] if date else None,
            "journal": " ".join(m.get("container-title") or []) or m.get("institution", [{}])[0].get("name", "") if m.get("institution") else " ".join(m.get("container-title") or []),
            "type": m.get("type", ""), "abstract": re.sub(r"\s+", " ", abstract).strip()[:1500],
            "published_as": [r["id"].lower() for r in (m.get("relation", {}).get("is-preprint-of") or [])
                             if r.get("id-type") == "doi"]}


def norm(t):
    return re.sub(r"[^a-z0-9 ]", "", re.sub(r"<[^>]+>", "", (t or "").lower()))


def title_search(title, first_author, after_year):
    """Crossref search for a journal article with (almost) the same title and first author."""
    q = urllib.parse.quote(title[:250])
    j = get(f"https://api.crossref.org/works?query.title={q}&filter=type:journal-article&rows=8")
    for it in (j or {}).get("message", {}).get("items", []):
        s = cr_summary(it)
        sim = difflib.SequenceMatcher(None, norm(s["title"]), norm(title)).ratio()
        if sim >= 0.9 and norm(s["first_author"]) == norm(first_author) and (s["year"] or 0) >= (after_year or 0):
            return s["doi"]
    return None


def ident(url):
    u = url.strip()
    if "x.com/" in u or "twitter.com/" in u:
        return "tweet", re.search(r"status/(\d+)", u).group(1)
    if "arxiv.org" in u:
        return "arxiv", re.search(r"(\d{4}\.\d{4,5})", u).group(1)
    m = re.search(r"pii/(S[0-9X]+)", u, re.I) or re.search(r"fulltext/(S[\d-]+\(\d+\)[\dX-]+)", u, re.I)
    if m:
        return "pii", re.sub(r"[-()]", "", m.group(1)).upper()
    m = re.search(r"academic\.oup\.com/(\w+)/article/(\d+)/([\w]+)/(\w+)/(\d+)", u)
    if m and not m.group(4).startswith("msa") and not m.group(4).startswith("gka"):
        return "oup_page", m.groups()
    m = re.search(r"academic\.oup\.com/(\w+)/article/\d+/\w+/(\w+)/", u)
    if m and m.group(1) == "mbe":
        return "doi", "10.1093/molbev/" + m.group(2)
    m = re.search(r"biorxiv\.org/content/(10\.\d+/[\d.]+?)(v\d+)?(\.full|\.abstract)?$", u.split("?")[0].split("#")[0])
    if m:
        return "biorxiv", m.group(1)
    m = re.search(r"nature\.com/articles/([\w.-]+)", u)
    if m:
        return "doi", "10.1038/" + m.group(1).split("?")[0]
    m = re.search(r"(10\.\d{4,9}/[^\s?#]+)", u)
    if m:
        return "doi", m.group(1)
    return "unknown", u


def resolve(url):
    kind, val = ident(url)
    rec = {"link": url, "kind": kind, "input_id": val, "preprint": False}
    if kind == "tweet":
        t = get(f"https://cdn.syndication.twimg.com/tweet-result?id={val}&token=a") or {}
        rec["tweet_text"] = t.get("text", "")
        rec["tweet_author"] = (t.get("user") or {}).get("name", "")
        return rec  # resolved to a paper by hand (see batch assignment file)
    if kind == "pii":
        j = get(f"https://api.crossref.org/works?filter=alternative-id:{val}&rows=2")
        items = (j or {}).get("message", {}).get("items", [])
        val = items[0]["DOI"] if items else None
        kind = "doi"
    if kind == "oup_page":
        jr, vol, iss, page, _ = val
        term = urllib.parse.quote(f"Nucleic Acids Res[ta] AND {vol}[vi] AND {page}[pg]")
        j = get(f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pubmed&retmode=json&term={term}")
        ids = (j or {}).get("esearchresult", {}).get("idlist", [])
        doi = None
        if ids:
            x = get(f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?db=pubmed&retmode=json&id={ids[0]}")
            for a in (x or {}).get("result", {}).get(ids[0], {}).get("articleids", []):
                if a["idtype"] == "doi":
                    doi = a["value"]
        val, kind = doi, "doi"
    if kind == "arxiv":
        xml = get(f"https://export.arxiv.org/api/query?id_list={val}", as_json=False)
        ns = {"a": "http://www.w3.org/2005/Atom", "x": "http://arxiv.org/schemas/atom"}
        e = ET.fromstring(xml).find("a:entry", ns)
        rec.update(preprint=True, title=re.sub(r"\s+", " ", e.findtext("a:title", "", ns)).strip(),
                   first_author=e.find("a:author/a:name", ns).text.split()[-1],
                   year=int(e.findtext("a:published", "", ns)[:4]), journal="arXiv",
                   abstract=re.sub(r"\s+", " ", e.findtext("a:summary", "", ns)).strip()[:1500],
                   doi=f"10.48550/arXiv.{val}")
        pub = e.findtext("x:doi", "", ns)
        rec["published_doi"] = pub.lower() if pub else title_search(rec["title"], rec["first_author"], rec["year"])
    elif kind == "biorxiv":
        b = get(f"https://api.biorxiv.org/details/biorxiv/{val}") or {}
        coll = b.get("collection") or [{}]
        last = coll[-1]
        s = cr_summary(crossref(val))
        rec.update(preprint=True, doi=val.lower(), title=last.get("title") or s.get("title", ""),
                   first_author=(last.get("authors", "").split(",")[0].strip() or s.get("first_author", "")),
                   year=int((last.get("date") or "0000")[:4]) or s.get("year"), journal="bioRxiv",
                   latest_version=int(last.get("version", 1)),
                   abstract=(last.get("abstract") or s.get("abstract", ""))[:1500])
        pub = [c.get("published") for c in coll if c.get("published") not in (None, "", "NA")]
        rec["published_doi"] = (pub[-1].lower() if pub else None) or (s.get("published_as") or [None])[0] \
            or title_search(rec["title"], rec["first_author"], rec["year"])
    elif kind == "doi" and val:
        s = cr_summary(crossref(val))
        rec.update(s)
        if s.get("type") == "posted-content":
            rec["preprint"] = True
            rec["published_doi"] = (s.get("published_as") or [None])[0] or \
                title_search(s["title"], s["first_author"], s["year"])
    rec["final_doi"] = (rec.get("published_doi") or rec.get("doi") or val or "").lower()
    if rec.get("published_doi"):
        p = cr_summary(crossref(rec["published_doi"]))
        rec["published"] = {k: p.get(k) for k in ("title", "first_author", "year", "journal")}
    return rec


def main():
    src = pathlib.Path(sys.argv[1])
    links = [l.strip() for l in src.read_text().splitlines() if l.strip().startswith("http")]
    out = []
    for i, l in enumerate(links, 1):
        print(f"[{i}/{len(links)}] {l}", flush=True)
        r = resolve(l)
        flag = f"  -> PEER-REVIEWED VERSION {r['published_doi']}" if r.get("published_doi") else ""
        print(f"    {r.get('first_author','?')} {r.get('year','?')} | {r.get('journal','')} | {r.get('title', r.get('tweet_text',''))[:90]}{flag}")
        out.append(r)
        time.sleep(0.4)
    dst = src.with_name(src.name.replace("_links.txt", "_resolved.json"))
    dst.write_text(json.dumps(out, ensure_ascii=False, indent=1))
    print("wrote", dst)


if __name__ == "__main__":
    main()
