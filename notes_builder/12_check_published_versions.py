#!/usr/bin/env python3
"""Second check for peer-reviewed versions of preprints in a resolved batch.

For every preprint in batches/<batch>_resolved.json, search
  * PubMed (title words, excluding the Preprint publication type)
  * OpenAlex (title search; lists journal/proceedings versions)
and print candidates with the same first author for manual confirmation.
Also searches for any extra titles given on the command line (e.g. papers announced on X).

Usage: python3 -I 12_check_published_versions.py batches/<batch>_resolved.json ["extra title" ...]
"""
import json, re, sys, time, urllib.parse, urllib.request
UA = {"User-Agent": "literature-notes-script/1.0"}
def get(url):
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=40) as r:
            return json.loads(r.read())
    except Exception as e:
        print("   !", e); return {}
def words(t, n=10):
    w = [x for x in re.findall(r"[A-Za-z0-9-]+", t) if len(x) > 3][:n]
    return " AND ".join(f"{x}[ti]" for x in w)
def pubmed(title):
    term = urllib.parse.quote(f"({words(title)}) NOT preprint[pt]")
    ids = get(f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pubmed&retmode=json&retmax=5&term={term}").get("esearchresult", {}).get("idlist", [])
    if not ids: return []
    s = get(f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?db=pubmed&retmode=json&id={','.join(ids)}").get("result", {})
    return [(s[i].get("sortfirstauthor"), s[i].get("fulljournalname"), s[i].get("pubdate"), s[i].get("title"),
             next((a["value"] for a in s[i].get("articleids", []) if a["idtype"] == "doi"), "")) for i in ids]
def openalex(title):
    q = urllib.parse.quote(re.sub(r"[^\w\s-]", " ", title)[:200])
    r = get(f"https://api.openalex.org/works?search={q}&per-page=6").get("results", [])
    out = []
    for w in r:
        src = ((w.get("primary_location") or {}).get("source") or {}).get("display_name")
        au = (w.get("authorships") or [{}])[0].get("author", {}).get("display_name", "")
        out.append((au, src, w.get("publication_year"), w.get("title"), w.get("doi"), w.get("type")))
    return out
batch = json.load(open(sys.argv[1]))
targets = [(r["first_author"], r["title"]) for r in batch if r.get("preprint")] + [("", t) for t in sys.argv[2:]]
for fa, t in targets:
    print(f"\n### {fa} | {t[:100]}")
    for c in pubmed(t): print("  PubMed  :", c)
    for c in openalex(t):
        if c[1] not in ("bioRxiv", "arXiv (Cornell University)", None) or not fa: print("  OpenAlex:", c)
    time.sleep(0.5)
