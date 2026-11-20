# Literature paper-notes pages

One flashcard-style "Paper notes" HTML page per literature subfolder, updated
automatically every **Wednesday at 04:00** (server time, Europe/Zagreb).

```
~/literature/
├── papers/<folder>/*.pdf                         ← drop new papers here
├── papers/<folder>/paper_notes_<folder>.html     ← the page for that folder (open in a browser)
├── papers/_superseded_preprints/                 ← preprints replaced by their peer-reviewed version (kept, ignored)
├── notes/<folder>/<pdf name>.json                ← notes for one paper (editable)
├── notes/catalog.json                            ← per paper: subcategory, shared by, DOI link, preprint DOI
├── notes/_failed/*.log                           ← papers whose notes failed (retried next week)
└── notes_builder/                                ← this folder: scripts, template, logs, batches/
```

Each page groups its papers into coloured **subcategories** (set per folder in
`config.json` → `folders.<folder>.subcategories`). The paper header shows the
subcategory, **"Shared by Damir · 2026"** for papers from a shared batch, "Open paper"
(peer-reviewed DOI) and, when the paper replaced a preprint, a "Preprint" link.
Papers that are catalogued but whose PDF is not downloaded yet show as **"PDF missing"**
with the exact file name to save the PDF as.

## What happens each Wednesday

`run_weekly.sh` (started by cron) runs:

1. **`01_generate_notes.py`**: finds every PDF under `papers/` with no JSON in
   `notes/` yet. For each one it runs Claude Code headless (`claude -p`, Read tool
   only, so it can read the PDF but cannot run commands, edit files or go online)
   with `prompt.md`. Claude reads the paper and returns section-by-section Q&A notes
   in the same format as the hand-written notes (section / question / answer /
   keywords / additional information / main conclusion). The script checks the
   reply and saves it as `notes/<folder>/<pdf name>.json`. The DOI link comes
   from the PDF's own metadata. At most `max_new_papers_per_run` (15) papers per week.
2. **`02_build_html.py`**: rebuilds every `paper_notes_<folder>.html` from
   `template.html` plus that folder's JSON notes. PDFs still without notes are
   listed as "no notes yet".

Log of each run: `logs/weekly_YYYY-MM-DD.log` (includes the cost per paper).

## Things you can do by hand

| Want to | Do |
|---|---|
| Add a paper | Put the PDF in the right `papers/<folder>/`. Name it `Author_Year_...pdf` (the id falls back to the first two parts of the name). |
| Get notes now instead of Wednesday | `~/literature/notes_builder/run_weekly.sh` (up to 15 papers), or for all waiting papers, 3 at a time: `cd ~/literature/notes_builder && (flock -n 9 && python3 -I 01_generate_notes.py --limit 0 --jobs 3 && python3 -I 02_build_html.py) 9>.lock` (first used 2026-11-17, log in `logs/manual_*.log`) |
| Fix or add notes | Edit `notes/<folder>/<name>.json`, then `python3 -I 02_build_html.py`. The JSON is never regenerated once it exists. |
| Add your own opinion line | Fill `"note"` in the JSON (shown in italics under the title). |
| Change a paper's subcategory | Set `"category"` in the paper's JSON to one of the folder's subcategories (or a name from `config.json` → `categories`). `null` = the subcategory from `notes/catalog.json`, else the folder default. |
| Add / rename subcategories | `config.json` → `folders.<folder>.subcategories` (name → colour: mex blue, emb orange, gen green, dam pink, oth purple, ali yellow), then `catalog.json` / JSONs, then `02_build_html.py`. |
| Add papers from a list of links | See "Adding a batch of links" below. |
| Regenerate one paper's notes | Move its JSON out of `notes/` (keep it somewhere), then run `run_weekly.sh`. |
| New subfolder | Just create it under `papers/`; it gets its own page. Optionally add a label/category in `config.json` → `folders`. |
| Choose the model | `config.json` → `"claude_model"` (e.g. `"claude-opus-5-5"`); `null` = Claude Code default. |

"Known" flashcard progress is stored in the browser (localStorage), as in the original page.

## Schedule (cron)

Installed with `crontab -e` on abacus2:

```
# Literature paper-notes: weekly update, Wednesday 04:00
0 4 * * 3 /home/mbosnjak/literature/notes_builder/run_weekly.sh
```

Check: `crontab -l`. Remove: `crontab -e` and delete the line.
The server has to be up at 04:00 on Wednesday; a missed run is caught up the next Wednesday.
The Claude binary is found at run time (`claude` on PATH, else the newest
`~/.vscode-server/extensions/anthropic.claude-code-*/resources/native-binary/claude`),
so VS Code extension updates don't break it. To pin it, set `CLAUDE_BIN` in `run_weekly.sh`.
Headless runs use the same Claude login as VS Code; if a run's log shows an
authentication error, log in again in VS Code/Claude Code.

## How this was set up (2026-11-17), all commands

The page design comes from the example file shared on Google Drive
(`1-BXij4Zxus0TrBBbir08ptqRhmLxAUUK`), which had been generated from the notes
spreadsheet (`1PeNln_oX0PONFDR2MlDlU7wSLrHcPmAobadwjM-i4No`: a `Content` sheet plus
one sheet per paper with columns Section / Question / Answer / Keywords / Additional
information / Main conclusion).

```bash
# 1. download the example page and the spreadsheet via their share links (scratch dir)
D=<scratch dir>
curl -sSL -A "Mozilla/5.0" -o $D/example.html "https://drive.google.com/uc?export=download&id=1-BXij4Zxus0TrBBbir08ptqRhmLxAUUK"
curl -sSL -A "Mozilla/5.0" -o $D/sheet.xlsx  "https://docs.google.com/spreadsheets/d/1PeNln_oX0PONFDR2MlDlU7wSLrHcPmAobadwjM-i4No/export?format=xlsx"
for s in Content Alcantera_2026 Armstrong_2019; do
  curl -sSL -A "Mozilla/5.0" -o "$D/$s.csv" \
    "https://docs.google.com/spreadsheets/d/1PeNln_oX0PONFDR2MlDlU7wSLrHcPmAobadwjM-i4No/gviz/tq?tqx=out:csv&sheet=$s"
done
(cd $D && mkdir -p x && cd x && unzip -o -q ../sheet.xlsx && grep -o '<sheet [^>]*>' xl/workbook.xml)   # sheet names

# 2. inspect the page: it is self-contained, data in `const DATA = {legend, papers:[{id,title,
#    category,link,note,items:[{type:"qa",section,q,a,kw,info,concl} | {type:"note",section,text}]}]}`
python3 -I - $D/example.html <<'EOF'
import sys,re,json
s=open(sys.argv[1],encoding='utf-8').read()
d=json.loads(re.search(r'const DATA = (\{.*?\});\n',s,flags=re.S).group(1))
print(list(d), d['legend'], len(d['papers']), list(d['papers'][0]))
EOF

# 3. check scheduling tools
which crontab; systemctl is-active cron; timedatectl | grep zone
C=$(ls -d ~/.vscode-server/extensions/anthropic.claude-code-*/resources/native-binary/claude | sort -V | tail -1)
env -i HOME=$HOME PATH=/usr/bin:/bin $C -p "Reply with exactly: OK" --tools Read --strict-mcp-config \
    --no-session-persistence --output-format json < /dev/null      # headless works in a cron-like env

# 4. set up this folder
mkdir -p ~/literature/notes_builder/{work,logs,reference} ~/literature/notes
cp $D/example.html ~/literature/notes_builder/reference/example_paper_notes.html
cd ~/literature/notes_builder
python3 -I 00_make_template.py            # reference/example_paper_notes.html -> template.html
python3 -I 01_generate_notes.py --dry-run
python3 -I 02_build_html.py

# 5. first real run, in a cron-like environment
env -i HOME=$HOME PATH=/usr/bin:/bin SHELL=/bin/sh LOGNAME=mbosnjak ~/literature/notes_builder/run_weekly.sh

# 6. install the schedule (keeps any existing crontab lines)
( crontab -l 2>/dev/null; echo "# Literature paper-notes: weekly update, Wednesday 04:00"; \
  echo "0 6 * * 3 /home/mbosnjak/literature/notes_builder/run_weekly.sh" ) | crontab -
```

## Adding a batch of links

Rule: when a preprint (bioRxiv/arXiv) has a peer-reviewed version, that version is
downloaded and used for the notes; the preprint goes to `papers/_superseded_preprints/`.

```bash
cd ~/literature/notes_builder
# 1. put the links, one per line, in batches/<date>_<name>_links.txt
python3 -I 10_resolve_links.py batches/<batch>_links.txt          # -> <batch>_resolved.json (DOIs, metadata, published versions)
python3 -I 12_check_published_versions.py batches/<batch>_resolved.json   # 2nd check: PubMed + OpenAlex (catches renamed journal versions)
# 2. write batches/<batch>_assign.tsv by hand: n, folder, subcategory, filename, doi_override
#    (doi_override = peer-reviewed DOI found only in step 12, or the paper behind an X post)
python3 -I 11_download_papers.py <batch> --shared-by Damir --year 2026     # PDFs + notes/catalog.json + <batch>_download_report.tsv
python3 -I 02_build_html.py
```

`11_download_papers.py` only accepts a real PDF, and from PMC only when PMC's own record
has exactly the wanted DOI (PMC also files preprints under the journal DOI).
It never overwrites existing PDFs, and re-running it is safe.

### Batch 2026-11-17_damir (40 links shared by Damir in 2026)

Files: `batches/2026-11-17_damir_*` (links, resolved, assign, download_report, MANUAL_DOWNLOADS.md).

```bash
python3 -I 10_resolve_links.py batches/2026-11-17_damir_links.txt
python3 -I 12_check_published_versions.py batches/2026-11-17_damir_resolved.json \
    "ENCODE GRAMMAR Genomic Regulatory Atlas of sequence Models Motifs Annotations and Rules"
# X post 2084836326000746855 (Kundaje, ENCODE GRAMMAR) read via
curl -sS "https://cdn.syndication.twimg.com/tweet-result?id=2084836326000746855&token=a"
curl -sS "https://api.datacite.org/dois/10.5281/zenodo.21795359"     # its Zenodo record (zenodo.org itself blocks this network)
mkdir -p ~/literature/papers/_superseded_preprints
mv ~/literature/papers/amexicanus/Richards_2026_bioRxiv_QTL_repeatability_cave_traits.pdf ~/literature/papers/_superseded_preprints/
python3 -I 11_download_papers.py 2026-11-17_damir --shared-by Damir --year 2026
python3 -I 13_verify_pdfs.py batches/2026-11-17_damir_download_report.tsv   # loose check; see note below
# PMC metadata check of every PMC download (found: Richards PMC copy = preprint, not Genetics)
awk -F'\t' '$2=="downloaded" && $6 ~ /pmc-oa-opendata/ {print $6}' batches/2026-11-17_damir_download_report.tsv \
  | while read u; do curl -sS "${u%.pdf}.json" | head -c 300; echo; done
# set doi_override for Richards (10.1093/genetics/iyag223) and DART-Eval (10.52202/079017-1981);
# the wrong copies went to _superseded_preprints/ (Richards_2026_bioRxiv_PMC12889537_copy.pdf, Patel_2024_arXiv_DART-Eval.pdf)
sed -i -E 's/^(3\t.*Richards_2026_Genetics_cave_evolution_on_repeat\.pdf)$/\1\t10.1093\/genetics\/iyag223/; s/^(34\t.*Patel_2024_NeurIPS_DART-Eval\.pdf)$/\1\t10.52202\/079017-1981/' batches/2026-11-17_damir_assign.tsv
# DART-Eval NeurIPS 2024 proceedings PDF (found in https://papers.nips.cc/paper_files/paper/2024 index)
curl -sS -o ~/literature/papers/regulatiory_genomics/Patel_2024_NeurIPS_DART-Eval.pdf \
  "https://papers.nips.cc/paper_files/paper/2024/file/71998bfc3217ffe1cca1ee084dfadadd-Paper-Datasets_and_Benchmarks_Track.pdf"
mutool draw -F txt -o - ~/literature/papers/regulatiory_genomics/Patel_2024_NeurIPS_DART-Eval.pdf 1 | grep -i neurips
# catalog.json: DART-Eval "link_override" = papers.nips.cc page; ENCODE GRAMMAR "title" set by hand (DataCite title)
python3 -I 00_make_template.py && python3 -I 02_build_html.py
```

Result: 23 PDFs in place, 17 need a manual download (subscription / Zenodo); list in
`batches/2026-11-17_damir_MANUAL_DOWNLOADS.md`. The server has no institutional access
(nature.com shows "Access through your institution"). Note: `13_verify_pdfs.py` gave
false "DOI found" for two files; the reliable check is PMC's `.json` record (above) or
`mutool draw -F txt` on page 1.

### Batch 2026-11-17_damir_basics (Drive folder shared by Damir: basics, important)

8 classic core-promoter papers from the shared Drive folder `1OoNQGMp_ik16rr64HT8tblluEp8EI3GU`,
all published journal versions, filed under regulatiory_genomics → "Transcription initiation &
promoters" with tags `Basics`, `Important` (badges in the header, ★ in the lists, listed first,
and notes written first by `01_generate_notes.py`).

```bash
python3 -I 14_fetch_drive_folder.py 1OoNQGMp_ik16rr64HT8tblluEp8EI3GU batches/2026-11-17_damir_basics_files \
    | tee batches/2026-11-17_damir_basics_identified.tsv          # download + DOI + Crossref check
# batches/2026-11-17_damir_basics_assign.tsv written by hand (source, folder, subcategory, filename, doi, tags)
python3 -I 15_add_local_pdfs.py 2026-11-17_damir_basics --shared-by Damir --year 2026
python3 -I 00_make_template.py && python3 -I 02_build_html.py
```

Tags: any list in a catalog entry's `"tags"` is shown; `"Important"` also sorts first.

## Files here

| File | Purpose |
|---|---|
| `config.json` | paths, folder labels → default category, category → colour, model, limits |
| `prompt.md` | instructions + style examples (from the hand-written notes) given to Claude per paper |
| `00_make_template.py` | one-off: example page → `template.html` (same look and JS; data and labels become placeholders) |
| `template.html` | page template |
| `01_generate_notes.py` | PDFs without notes → `notes/<folder>/*.json` |
| `02_build_html.py` | notes → `papers/<folder>/paper_notes_<folder>.html` |
| `run_weekly.sh` | cron entry point (lock + log + steps 01 and 02) |
| `10_resolve_links.py` | links → DOIs, metadata, peer-reviewed versions of preprints |
| `12_check_published_versions.py` | second search for journal versions (PubMed, OpenAlex) |
| `11_download_papers.py` | download PDFs to their folders, write `notes/catalog.json` |
| `13_verify_pdfs.py` | quick DOI-in-PDF check (loose; prefer PMC `.json` / `mutool`) |
| `14_fetch_drive_folder.py` | download a shared Drive folder's PDFs + identify DOIs |
| `serve_notes.py` + `start_notes_server.sh` | local server for the pages + "My comments" saving |
| `17_import_notes.py` | import a paper with prepared notes (no Claude usage) |
| `16_make_abstract_source.py` | abstract-only text source for papers without full-text access |
| `15_add_local_pdfs.py` | add downloaded PDFs to folders + catalog (with tags) |
| `batches/` | one set of files per link batch (links, resolved, assign, report, manual list) |
| `reference/example_paper_notes.html` | the original example page |
| `logs/` | one log per run |

## Known limits and fixes (2026-11-17)

- PDFs over 18 MB (high-resolution figures; e.g. Liu 2026 is 69 MB) cannot be opened by
  Claude's Read tool, and its page-by-page mode needs `pdftoppm` (not installed). For those,
  `01_generate_notes.py` extracts the text with `mutool draw -F txt` into `work/text/` and
  Claude reads that instead (figures not included).
- Long papers can produce a JSON reply longer than the default output limit; the script sets
  `CLAUDE_CODE_MAX_OUTPUT_TOKENS=32000` for the headless run.
- First full run (2026-11-17): 30 papers, 26 ok + 4 failed for the two reasons above, all 4 ok on
  retry; total about $28. Old failure logs: `notes/_failed/resolved_2026-11-17/`.

### Manual downloads and missing access (2026-11-17, batch 2026-11-17_damir_manual)

```bash
python3 -I 14_fetch_drive_folder.py 1KdPIho1Xp6Tb_KFvK8bxJDX1ANz4gnFU batches/2026-11-17_damir_manual_files \
    | tee batches/2026-11-17_damir_manual_identified.tsv
# batches/2026-11-17_damir_manual_assign.tsv by hand; 15_add_local_pdfs.py now merges with existing catalog entries
python3 -I 15_add_local_pdfs.py 2026-11-17_damir_manual
# Richards: Genetics not accessible -> use bioRxiv v1 again (catalog key renamed, "source_note" added)
mv ~/literature/papers/_superseded_preprints/Richards_2026_bioRxiv_QTL_repeatability_cave_traits.pdf ~/literature/papers/amexicanus/
# Xu 2025 / Jaganathan 2025: not accessible -> abstract-only text sources (+ "source_note" in catalog)
python3 -I 16_make_abstract_source.py drerio Xu_2025_TrendsGenet_epigenetics_ZGA_to_lineage 10.1016/j.tig.2025.05.005
python3 -I 16_make_abstract_source.py regulatiory_genomics Jaganathan_2025_Science_promoter_mutations_deep_learning 10.1126/science.ads7373
python3 -I 00_make_template.py
(flock -n 9 && python3 -I 01_generate_notes.py --limit 0 --jobs 3 && python3 -I 02_build_html.py) 9>.lock
```

Source notes: a catalog entry's `"source_note"` is shown under the paper title (orange, ⚠) and
copied into the notes JSON. Use it whenever notes are not from the full peer-reviewed text.
`<stem>.txt` files in a paper folder are treated as (abstract-only) sources when there is no PDF
with the same name; if you later get the PDF, save it as `<stem>.pdf`, move the old notes JSON
aside, and the next run writes full notes (remove the `source_note` from catalog.json).

### Mexican tetra papers (2026-11-17, batch 2026-11-17_tetra, Marta's own, not shared by Damir)

```bash
python3 -I 14_fetch_drive_folder.py 1gfe0FAO_ypllOvrI57baWiThmObhnLPj batches/2026-11-17_tetra_files \
    | tee batches/2026-11-17_tetra_identified.tsv
mutool draw -F txt -o - batches/2026-11-17_tetra_files/Warren_2026.pdf 1   # no DOI in metadata: it is Roback et al. 2026 Genome Res
# config.json: amexicanus subcategories + "Genomes & structural variation", "Gene regulation & metabolism"
python3 -I 15_add_local_pdfs.py 2026-11-17_tetra
```

### Usage limit

Headless note writing (`claude -p`) counts toward the Claude plan's usage. On 2026-11-17 a large
manual run hit the 5-hour limit after ~40 papers; `01_generate_notes.py` now stops at the first
"usage limit" reply and leaves the remaining papers for the next run (no failure logs for them).
Large batches: spread them out, or keep `max_new_papers_per_run` at 15 for the weekly job.

### Shared-by update (tetra batch)

"D" in the tetra folder = shared by Damir (confirmed by Marta): Lal 2025, Gore 2018, da Silva 2023,
  McGaugh 2014, Warren 2021 got shared_by "Damir", shared_year "2026" in notes/catalog.json (edited with a
  short python snippet); 14_fetch_drive_folder.py now goes into subfolders and prefers the page-1 DOI.

### Damir Baranašić's own papers, 2020+ (batch 2026-11-17_baranasic)

Source list: Google Scholar profile JOmsDooAAAAJ (sorted by date), cross-checked with OpenAlex author
A5045920121 (ORCID 0000-0001-5948-0932). 19 items from 2020; datasets/software/commentary excluded;
3 preprints replaced by their journal versions (salmonid preprint → Nat Ecol Evol 2026, Cdx2 preprint →
Dev Cell 2025, "Integrated annotation…" preprint → Nat Genet 2022) → 16 papers, tag `Damir's paper`
(not "shared by"). New subcategories: regulatiory_genomics "Regulatory evolution", drerio "Genomic
resources", general "Genomic resources & assembly".

```bash
curl -sS "https://api.openalex.org/works?filter=author.id:A5045920121,from_publication_date:2020-01-01&per-page=100"
python3 -I 10_resolve_links.py batches/2026-11-17_baranasic_links.txt
python3 -I 12_check_published_versions.py batches/2026-11-17_baranasic_resolved.json
python3 -I 11_download_papers.py 2026-11-17_baranasic --shared-by "" --year ""
# 11_download_papers.py fixes: check all (≤12) PMC hits, not 3 (the DOI search also returns citing papers);
# bioRxiv download for any preprint DOI (not only biorxiv.org links)
# Cdx2 (Dev Cell): PMC has no main PDF -> full text .txt from PMC open data, catalog "fulltext_txt": true
curl -sS -o ~/literature/papers/regulatiory_genomics/Amblard_2025_DevCell_Cdx2_enhancer_attenuator.txt \
  "https://pmc-oa-opendata.s3.amazonaws.com/PMC12979250.1/PMC12979250.1.txt"
# tags "Damir's paper" for all batch entries (python snippet on notes/catalog.json); 02_build_html.py
```

Manual download still needed: Naseer 2025 Genome Res (https://doi.org/10.1101/gr.280579.125; journal and
Edinburgh repository both return 403 to scripts) → save as
`papers/regulatiory_genomics/Naseer_2025_GenomeRes_salmon_antiviral_regulatory_landscape.pdf`.

### Schedule change (2026-11-17)

Weekly job moved from Wednesday 06:00 to **Wednesday 04:00** (Marta's request):
`crontab -l | sed 's|^0 6 \* \* 3 |0 4 * * 3 |' | crontab -` (previous crontab saved in
`batches/crontab_backup_2026-11-17.txt`). Naseer 2025 Genome Res added from Marta's Drive folder
1jy0buFuXecmGW_I4sU0AUsJmeS6rrp_j (batch 2026-11-17_baranasic_manual).

### Per-paper extra instruction (2026-11-17)

A catalog entry's `"prompt_extra"` is appended to the note-writing prompt for that paper only.
Used for Phan 2025 (Nat Genet): two runs were cut off by a false-positive safety stop while writing
detailed Methods items; with `prompt_extra` = "Cover the Methods in at most 4 short summary items …"
it went through (45 questions). Same false-positive cut-offs happened once each for Krishnan 2022 and
Warren 2021 and were fixed by a plain retry. End of 2026-11-17: all 72 papers have notes (2,880 questions).

## Importing prepared notes (no Claude usage)

When a paper comes with notes already in the page format (a JSON like `notes/<folder>/*.json`, e.g.
made elsewhere), `17_import_notes.py` checks and files them without running Claude: it normalises the
items, checks the DOI (PDF page 1 vs the notes' link, then Crossref), copies the PDF, writes the notes
JSON and the catalog entry. The weekly job then skips that paper (its notes exist).

### Wiese 2025 (2026-11-18, Marta's prepared notes; not shared by Damir)

Drive folder 1IHpyZfj2FiaHwNqyQsh7FnIQyA8NIHQS: `Wiese_et_al_2025.pdf` (J Hered 116:89–100,
doi 10.1093/jhered/esae040) + `Wiese_2025_QTL_cavefish_notes.json` (46 Q&A + 3 notes, made with ChatGPT).

```bash
B=batches/2026-11-18_wiese_files; mkdir -p $B
curl -sSL -o $B/Wiese_2025_QTL_cavefish_notes.json "https://drive.google.com/uc?export=download&id=1bCNIdrT1FBdQFMxcvfok_g1TPaq4jEDM"
curl -sSL -o $B/Wiese_et_al_2025.pdf "https://drive.google.com/uc?export=download&id=1gjMtwhUX1Ryfs8T_9qz_TnSc96PI1U-n"
python3 -I 17_import_notes.py $B/Wiese_2025_QTL_cavefish_notes.json $B/Wiese_et_al_2025.pdf amexicanus \
    "Genetics of cave traits" Wiese_2025_JHered_QTL_cavefish_genome_regions.pdf --tags "External notes"
python3 -I 02_build_html.py
```
README: badge renamed from "Marta's notes" to "External notes" on 2026-11-18.

## "My comments" on each paper (notes server, 2026-11-18)

Every paper page ends with a **My comments** box. Comments are saved automatically while typing by a
small local server, into `notes/comments.json` (`{"<folder>/<pdf name>": {"text", "updated"}}`); every
save is also appended to `notes/comments_history.jsonl` (nothing is ever lost). Pages built by
`02_build_html.py` also embed the last saved comments, so a page opened as a file shows them read-only.

- Start / show the link: `~/literature/notes_builder/start_notes_server.sh` (also started by cron `@reboot`).
  It prints `http://localhost:21060/?t=<key>`.
- VS Code: **Ports** tab → *Forward a Port* → `21060`, then open the link (Command Palette →
  *Simple Browser: Show*, or a normal browser). The key is needed once; a cookie remembers it.
- Security (abacus2 is shared): the server listens on 127.0.0.1 only and needs the private key in
  `.server_token` (mode 600); comments files and the built HTML pages are mode 600.
- Stop: `kill "$(cat ~/literature/notes_builder/.server.pid)"`; log: `logs/server.log`.

Files: `serve_notes.py` (server), `start_notes_server.sh` (start + print link), `00_make_template.py`
(comment box, styles, autosave code), `02_build_html.py` (paper `key`, embedded comments, mode 600).
Tested 2026-11-18 with curl: no key → 403 (GET and POST), key → cookie, save + read back (UTF-8),
bad key → 400, path escape → 404; the test comment was removed afterwards.

### Signaling papers with prepared notes (2026-11-19) → new folder `papers/signaling/`

Drive folder 1IHpyZfj2FiaHwNqyQsh7FnIQyA8NIHQS (same as Wiese; not shared by Damir): two PDFs + notes JSON
made in claude.ai. New folder/page "Signaling pathways" (config.json `folders.signaling`, subcategories
"TGF-β / Nodal", "Wnt"). `17_import_notes.py` fix: a DOI wrapped onto the next line on page 1
(Annual Reviews) is completed from the notes' DOI, and Crossref falls back to the notes' DOI.

```bash
B=batches/2026-11-19_signaling_files   # downloaded with curl "https://drive.google.com/uc?export=download&id=<id>"
mkdir -p ~/literature/papers/signaling
python3 -I 17_import_notes.py $B/ElKholtei_2025_AnnuRevCellDevBiol_nodal_signaling_TGFb.json \
    $B/annurev-cellbio-112122-030209.pdf signaling "TGF-β / Nodal" ElKholtei_2025_AnnuRevCellDevBiol_nodal_signaling_TGFb.pdf --tags "External notes"
python3 -I 17_import_notes.py $B/Komiya_2008_Organogenesis_wnt_signal_transduction.json \
    $B/org0402_0068.pdf signaling "Wnt" Komiya_2008_Organogenesis_wnt_signal_transduction.pdf --tags "External notes"
python3 -I 02_build_html.py
```

## GitHub backup (2026-11-20): https://github.com/MartaBos/Literature (private)

`~/literature` is a git repository. Pushed on Marta's request; not pushed automatically by the weekly job.
Excluded by `~/literature/.gitignore`: all PDFs, `papers/**/*.txt` (abstract / full-text sources),
`notes_builder/batches/*_files/`, `work/`, `logs/`, `.server_token`, `.server.pid`, `.lock`, `notes/_failed/`.
Comments (`notes/comments*.json*`) are included (Marta's choice; repo private). Commits use the GitHub
no-reply email (repo-local `git config user.email`).

```bash
GH=/home/mbosnjak/miniforge3/envs/R/bin/gh
$GH repo edit MartaBos/Literature --visibility private --accept-visibility-change-consequences   # was public
cd ~/literature && git init -b main
git config user.email "$($GH api user --jq .id)+MartaBos@users.noreply.github.com"; git config user.name "Marta Bosnjakovic"
git add -A && git commit -m "..."      # (no Claude co-author line, see 2026-11-20) checked first: no PDFs/secrets staged, ~5 MB, 121 files (+ top-level README.md)
git remote add origin https://github.com/MartaBos/Literature.git
git -c credential.helper= -c "credential.helper=!$GH auth git-credential" push -u origin main
```

Later updates (after new notes / comments):
```bash
cd ~/literature && git add -A && git commit -m "Update notes" && \
git -c credential.helper= -c "credential.helper=!/home/mbosnjak/miniforge3/envs/R/bin/gh auth git-credential" push
```

2026-11-20: "Co-Authored-By: Claude" lines removed from both commits at Marta's request
(`git filter-branch --msg-filter 'sed "/^Co-Authored-By: Claude/d"' -- main`, then
`git push --force-with-lease=main:<old sha> origin main`); local tag `backup-before-trailer-removal`
keeps the old commits (not pushed). Future commits: no Claude co-author line.

2026-11-20: Marta enabled GitHub Pages (branch main, /) → https://martabos.github.io/Literature/
(repo made public for that). Links to the five pages added to the top-level README.md; all five
checked with curl (HTTP 200).

## One-time code task: sorting + tag filter (scheduled for Wed 2026-11-25 05:00)

Marta asked (2026-11-20) for sorting (author A→Z/Z→A, year both directions) and filtering by tags
(only / everything except; topic chips unchanged; tags from `tags` + "Shared by <name>") on every page,
to be done on Wednesday if usage is left. Spec: `tasks/2026-11-25_sort_filter.md`.

- `run_task_once.sh tasks/<task>.md`: runs headless Claude with Read/Edit/Write and only three shell
  commands allowed (00_make_template.py, 02_build_html.py, ./check_pages.sh). Backs up the files it may
  change; afterwards rebuilds and runs `check_pages.sh` (node --check on every page, paper counts must not
  change) and checks no other file was touched. Pass → local commit (author Marta, no Claude line, NOT
  pushed). Fail / no usage left → files restored, attempt saved in `logs/task_<task>_attempt.patch`.
  Removes its own cron line. Log: `logs/task_<task>.log`.
- `check_pages.sh`: page check used above (also handy by hand).
- cron: `0 5 25 11 * /home/mbosnjak/literature/notes_builder/run_task_once.sh tasks/2026-11-25_sort_filter.md`
- Tested 2026-11-20: restricted headless flags work (`check_pages.sh` run via Claude, $0.03); template
  did not yet contain the success markers (`pn-sort-`, "except").
