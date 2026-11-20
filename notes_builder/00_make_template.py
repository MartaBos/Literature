#!/usr/bin/env python3
"""Turn the example "Paper notes" page into template.html (run once).

Input : reference/example_paper_notes.html  (downloaded from the shared Drive file)
Output: template.html

The look and the JavaScript stay identical. Only these things change:
  * the embedded DATA object becomes a placeholder filled by 02_build_html.py
  * page title / heading come from DATA.page (one page per literature subfolder)
  * category colours come from DATA.catKeys (config.json) instead of a fixed list
  * DATA.legend is a plain list of category names
  * the "no notes yet" text and the home-page lead mention the weekly update
Each replacement must match exactly once, otherwise the script stops.

Usage: python3 -I 00_make_template.py
"""
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent
src = (HERE / "reference" / "example_paper_notes.html").read_text(encoding="utf-8")

# 1. strip the embedded data
m = re.search(r"const DATA = \{.*?\};\n", src, flags=re.S)
if not m:
    sys.exit("DATA block not found in example page")
html = src[:m.start()] + "const DATA = /*__DATA__*/null;\n" + src[m.end():]

# 2. exact text replacements: (old, new)
REPL = [
    ("<title>Paper notes</title>", "<title>__PAGE_TITLE__</title>"),
    ('<b id="mtitle">Paper notes</b>', '<b id="mtitle">__PAGE_LABEL__</b>'),
    ('<h1 id="home" tabindex="0" role="link">Paper notes</h1>',
     '<h1 id="home" tabindex="0" role="link">__PAGE_LABEL__</h1>'),
    ('const CAT = {\n  "Mexican tetra":"mex","Embryo exposures":"emb","General":"gen","Damir":"dam","Other group members":"oth","Alignment":"ali"\n};',
     "const CAT = DATA.catKeys;"),
    ("const cats = Object.values(DATA.legend).filter(",
     "const cats = DATA.legend.filter("),
    ('current.id.replace("_"," ") : "Paper notes";',
     'current.id.replace("_"," ") : DATA.page.label;'),
    ("<h2>Your reading notes</h2>",
     "<h2>${esc(DATA.page.label)}</h2>"),
    ("You know ${k} of them so far.</p>",
     "You know ${k} of them so far. Last updated ${esc(DATA.page.updated)}.</p>"),
    ("There are no notes for this paper yet. Add a sheet named ${esc(p.id)} to the workbook and fill in questions and answers.",
     "${p.missing_pdf ? `The PDF is not in the folder yet (it needs a subscription). Download it with Open paper and save it as ${esc(p.missing_pdf)}. Notes are written in the next weekly update (Wednesdays 04:00).` : `There are no notes for this paper yet. They are generated in the weekly update (Wednesdays 04:00) from ${esc(p.source_pdf || \"the PDF\")}.`}"),
    # "shared by" label and preprint link in the paper header
    ('.tag{background:var(--cl);color:var(--ink);border-radius:6px;padding:2px 8px;font-size:.8rem}',
     '.tag{background:var(--cl);color:var(--ink);border-radius:6px;padding:2px 8px;font-size:.8rem}\n'
     '.shared{border:1px solid var(--rule);border-radius:6px;padding:1px 8px;font-size:.8rem;color:var(--muted)}'),
    ('<span class="tag">${esc(p.category)}</span>${p.link ? `<a class="open" href="${esc(p.link)}" target="_blank" rel="noopener">Open paper</a>` : ""}</div>',
     '<span class="tag">${esc(p.category)}</span>${p.shared ? `<span class="shared">Shared by ${esc(p.shared)}</span>` : ""}'
     '${p.link ? `<a class="open" href="${esc(p.link)}" target="_blank" rel="noopener">Open paper</a>` : ""}'
     '${p.preprint ? `<a class="open" href="${esc(p.preprint)}" target="_blank" rel="noopener" title="Earlier preprint version">Preprint</a>` : ""}</div>'),
    ('`<div class="barlab">No notes yet</div>`',
     '`<div class="barlab">${p.missing_pdf ? "PDF missing" : "No notes yet"}</div>`'),
    # source note (e.g. "notes from the preprint" / "abstract only") under the title
    ('${p.note ? `<p class="note">${esc(p.note)}</p>` : ""}',
     '${p.note ? `<p class="note">${esc(p.note)}</p>` : ""}${p.source_note ? `<p class="srcnote">⚠ ${esc(p.source_note)}</p>` : ""}'),
    ('.phead .note{', '.phead .srcnote{font-size:.88rem;color:var(--again);border-left:3px solid var(--again);padding:2px 0 2px 10px;margin:8px 0 6px;max-width:68ch}\n.phead .note{'),
    # tags (e.g. Basics, Important): filled badges in the header, a star in the lists
    ('.shared{border:1px solid var(--rule);border-radius:6px;padding:1px 8px;font-size:.8rem;color:var(--muted)}',
     '.shared{border:1px solid var(--rule);border-radius:6px;padding:1px 8px;font-size:.8rem;color:var(--muted)}\n'
     '.badge{background:var(--ink);color:var(--bg);border-radius:6px;padding:1px 8px;font-size:.78rem;font-weight:600}\n'
     '.star{color:var(--cd);margin-left:4px}'),
    ('<span class="tag">${esc(p.category)}</span>${p.shared ?',
     '<span class="tag">${esc(p.category)}</span>${(p.tags||[]).map(t => `<span class="badge">${esc(t)}</span>`).join("")}${p.shared ?'),
    ('<span><b>${esc(p.id.replace("_"," "))}</b><span class="t">',
     '<span><b>${esc(p.id.replace("_"," "))}${(p.tags||[]).length ? `<span class="star" title="${esc(p.tags.join(", "))}">★</span>` : ""}</b><span class="t">'),
    ('<button class="prow" data-p="${p.slug}"><b>${esc(p.id.replace("_"," "))}</b>',
     '<button class="prow" data-p="${p.slug}"><b>${esc(p.id.replace("_"," "))}${(p.tags||[]).length ? `<span class="star" title="${esc(p.tags.join(", "))}">★</span>` : ""}</b>'),
    # "My comments" box at the end of each paper (saved by serve_notes.py; read-only when opened as a file)
    ('.empty{font-family:var(--serif);color:var(--muted);padding:30px 0;max-width:52ch}',
     '.empty{font-family:var(--serif);color:var(--muted);padding:30px 0;max-width:52ch}\n'
     '.comments{margin-top:44px}\n'
     '.comments textarea{width:100%;min-height:140px;resize:vertical;padding:12px 14px;border:1px solid var(--rule);'
     'border-radius:10px;background:var(--surface);font-family:var(--serif);font-size:1rem;line-height:1.6}\n'
     '.comments textarea[readonly]{opacity:.8}\n'
     '.cmtstatus{font-size:.82rem;color:var(--muted);margin-top:6px}'),
    ('    <div id="items">${body}</div>`;\n  bindQA(main);\n  main.querySelectorAll("[data-s]")',
     '    <div id="items">${body}</div>${commentHTML(p)}`;\n  bindQA(main);\n  bindComments(p);\n  main.querySelectorAll("[data-s]")'),
    ('/* search */',
     '/* comments */\n'
     'const COMMENTS = Object.assign({}, DATA.comments || {});\n'
     'let serverOK = null;  // true when served by serve_notes.py (comments editable)\n'
     'const cmtStamp = c => c && c.updated ? c.updated.replace("T", " ").slice(0, 16) : "";\n'
     'function commentHTML(p){\n'
     '  const c = COMMENTS[p.key] || {};\n'
     '  const ro = serverOK === false;\n'
     '  const status = ro ? `Read-only here: open the page through the notes server (start_notes_server.sh) to edit.${c.updated ? " Last saved " + cmtStamp(c) + "." : ""}`\n'
     '               : (c.updated ? `Saved · ${cmtStamp(c)}` : "Comments are saved automatically as you type.");\n'
     '  return `<section class="comments"><h3 class="sec">My comments</h3>\n'
     '    <textarea id="cmtText" placeholder="Your thoughts on this paper and on its notes…"${ro ? " readonly" : ""}>${esc(c.text || "")}</textarea>\n'
     '    <div class="cmtstatus" id="cmtStatus">${esc(status)}</div></section>`;\n'
     '}\n'
     'function bindComments(p){\n'
     '  const ta = document.getElementById("cmtText"), st = document.getElementById("cmtStatus");\n'
     '  if (!ta || serverOK === false) return;\n'
     '  let timer, last = ta.value;\n'
     '  const save = async () => {\n'
     '    clearTimeout(timer);\n'
     '    if (ta.value === last) return;\n'
     '    const text = ta.value; st.textContent = "Saving…";\n'
     '    try {\n'
     '      const r = await fetch("/api/comments", {method: "POST", credentials: "same-origin",\n'
     '        headers: {"Content-Type": "application/json"}, body: JSON.stringify({key: p.key, text})});\n'
     '      if (!r.ok) throw new Error(r.status);\n'
     '      const j = await r.json(); last = text; COMMENTS[p.key] = {text, updated: j.updated};\n'
     '      st.textContent = "Saved · " + cmtStamp(COMMENTS[p.key]);\n'
     '    } catch (e) { st.textContent = "Not saved (" + e.message + "). Is the notes server running?"; }\n'
     '  };\n'
     '  ta.addEventListener("input", () => { st.textContent = "Unsaved changes…"; clearTimeout(timer); timer = setTimeout(save, 800); });\n'
     '  ta.addEventListener("blur", save);\n'
     '}\n'
     '(async () => {  // detect the notes server and load the newest comments\n'
     '  try {\n'
     '    const r = await fetch("/api/comments?folder=" + encodeURIComponent(DATA.page.folder), {credentials: "same-origin"});\n'
     '    if (!r.ok) throw 0;\n'
     '    Object.assign(COMMENTS, await r.json()); serverOK = true;\n'
     '  } catch (e) { serverOK = false; }\n'
     '  if (current && !query) renderPaper(current);\n'
     '})();\n\n'
     '/* search */'),
]
for old, new in REPL:
    n = html.count(old)
    if n != 1:
        sys.exit(f"expected exactly 1 match, found {n}: {old[:70]!r}")
    html = html.replace(old, new)

(HERE / "template.html").write_text(html, encoding="utf-8")
print("wrote", HERE / "template.html")
