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
    # (star only when p.star: a tag listed in config.json "star_tags", or catalog "star": true/false)
    ('.shared{border:1px solid var(--rule);border-radius:6px;padding:1px 8px;font-size:.8rem;color:var(--muted)}',
     '.shared{border:1px solid var(--rule);border-radius:6px;padding:1px 8px;font-size:.8rem;color:var(--muted)}\n'
     '.badge{background:var(--ink);color:var(--bg);border-radius:6px;padding:1px 8px;font-size:.78rem;font-weight:600}\n'
     '.star{color:var(--cd);margin-left:4px}'),
    ('<span class="tag">${esc(p.category)}</span>${p.shared ?',
     '<span class="tag">${esc(p.category)}</span>${(p.tags||[]).map(t => `<span class="badge">${esc(t)}</span>`).join("")}${p.shared ?'),
    ('<span><b>${esc(p.id.replace("_"," "))}</b><span class="t">',
     '<span><b>${esc(p.id.replace("_"," "))}${p.star ? `<span class="star" title="${esc(p.tags.join(", "))}">★</span>` : ""}</b><span class="t">'),
    ('<button class="prow" data-p="${p.slug}"><b>${esc(p.id.replace("_"," "))}</b>',
     '<button class="prow" data-p="${p.slug}"><b>${esc(p.id.replace("_"," "))}${p.star ? `<span class="star" title="${esc(p.tags.join(", "))}">★</span>` : ""}</b>'),
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
    # --- sort dropdown, tag filter panel (per page) and font switch (shared) ---
    ("button,input{font:inherit;color:inherit}", "button,input,select{font:inherit;color:inherit}"),
    (".theme{margin:auto 22px 0;align-self:flex-start;",
     '.tools{display:flex;flex-wrap:wrap;gap:8px 10px;align-items:center;padding:0 22px}\n'
     '.sortl{display:inline-flex;align-items:center;gap:6px;font-size:.82rem;color:var(--muted)}\n'
     '.sortl select{border:1px solid var(--rule);border-radius:8px;background:var(--surface);color:var(--ink);padding:4px 6px;font-size:.82rem;max-width:160px}\n'
     '.tagf{font-size:.82rem}\n'
     '.tagf[open]{flex-basis:100%}\n'
     '.tagf summary{list-style:none;cursor:pointer;display:inline-flex;align-items:center;gap:4px;border:1px solid var(--rule);border-radius:8px;padding:4px 10px;color:var(--muted)}\n'
     '.tagf summary::-webkit-details-marker{display:none}\n'
     '.tagf summary::after{content:"\\25BE";font-size:.7rem;margin-left:2px}\n'
     '.tagf[open] summary::after{content:"\\25B4"}\n'
     '.tagf.on summary{background:var(--surface);color:var(--ink);border-color:var(--muted)}\n'
     '.tagbody{margin-top:8px;padding:10px 12px;border:1px solid var(--rule);border-radius:10px;background:var(--surface);display:flex;flex-direction:column;gap:8px}\n'
     '.tmode{display:inline-flex;align-self:flex-start;border:1px solid var(--rule);border-radius:8px;overflow:hidden}\n'
     '.tmode button{background:none;border:0;padding:3px 12px;font-size:.8rem;color:var(--muted)}\n'
     '.tmode button+button{border-left:1px solid var(--rule)}\n'
     '.tmode button[aria-pressed="true"]{background:var(--ink);color:var(--bg)}\n'
     '.thint{color:var(--muted);font-size:.78rem;margin:-2px 0 0}\n'
     '.taglist{display:flex;flex-direction:column;gap:4px}\n'
     '.tagi{display:flex;align-items:center;gap:8px;cursor:pointer;color:var(--ink)}\n'
     '.tagi input{accent-color:var(--ink);margin:0}\n'
     '.tagi small{margin-left:auto;color:var(--muted);font-variant-numeric:tabular-nums}\n'
     '.tfoot{display:flex;justify-content:space-between;align-items:center;gap:8px;color:var(--muted);font-size:.8rem;border-top:1px solid var(--rule);padding-top:8px}\n'
     '.tfoot button{background:none;border:0;padding:0;color:var(--muted);text-decoration:underline;text-underline-offset:3px;font-size:.8rem}\n'
     '.tfoot button:hover{color:var(--ink)}\n'
     '.tfoot button:disabled{opacity:.45;cursor:default;text-decoration:none}\n'
     '.sfoot{margin:auto 22px 0;display:flex;flex-wrap:wrap;gap:8px}\n'
     '.theme{'),
    ("*,*::before,*::after{box-sizing:inherit}",
     ':root[data-font="verdana"]{--serif:Verdana, Geneva, "DejaVu Sans", sans-serif; --sans:Verdana, Geneva, "DejaVu Sans", sans-serif}\n'
     "*,*::before,*::after{box-sizing:inherit}"),
    # apply the saved font before the page renders (attribute on <script> keeps check_pages.sh's regex on the main script)
    ("<title>__PAGE_TITLE__</title>",
     '<title>__PAGE_TITLE__</title>\n'
     '<script data-pn="font">try{if(JSON.parse(localStorage.getItem("pn-font"))==="verdana")'
     'document.documentElement.setAttribute("data-font","verdana")}catch(e){}</script>'),
    ('    <div class="cats" id="cats"></div>\n',
     '    <div class="tools">\n'
     '      <label class="sortl">Sort <select id="sort"><option value="default">Default</option>'
     '<option value="author-az">Author A→Z</option><option value="author-za">Author Z→A</option>'
     '<option value="year-new">Year, newest first</option><option value="year-old">Year, oldest first</option></select></label>\n'
     '      <details class="tagf" id="tagf"><summary>Tags<span id="tagsum"></span></summary>\n'
     '        <div class="tagbody">\n'
     '          <div class="tmode" id="tmode" role="group" aria-label="Tag filter mode"><button type="button" data-mode="only" aria-pressed="true">Only</button>'
     '<button type="button" data-mode="except" aria-pressed="false">Except</button></div>\n'
     '          <p class="thint" id="thint"></p>\n'
     '          <div class="taglist" id="taglist"></div>\n'
     '          <div class="tfoot"><span id="vcount"></span><button type="button" id="tclear">clear</button></div>\n'
     '        </div>\n'
     '      </details>\n'
     '    </div>\n'
     '    <div class="cats" id="cats"></div>\n'),
    ('<button class="theme" id="theme">Theme: auto</button>',
     '<div class="sfoot"><button class="theme" id="theme">Theme: auto</button><button class="theme" id="font">Font: Literata</button></div>'),
    ("applyTheme();\n\nconst totalQ",
     'applyTheme();\n'
     'let font = store.get("pn-font", "current") === "verdana" ? "verdana" : "current";\n'
     'function applyFont(){\n'
     '  if (font==="verdana") document.documentElement.setAttribute("data-font", "verdana");\n'
     '  else document.documentElement.removeAttribute("data-font");\n'
     '  document.getElementById("font").textContent = "Font: " + (font==="verdana" ? "Verdana" : "Literata");\n'
     '}\n'
     'document.getElementById("font").onclick = () => {\n'
     '  font = font==="verdana" ? "current" : "verdana";\n'
     '  store.set("pn-font", font); applyFont();\n'
     '};\n'
     'applyFont();\n\nconst totalQ'),
    ("const visible = () => papers.filter(p => !activeCats.size || activeCats.has(p.category));",
     r'''/* tag filter + sort (remembered per page) */
const sharedName = p => p.shared ? String(p.shared).split(" · ")[0].trim() : "";
papers.forEach((p, i) => {
  p.ord = i;
  p.au = p.id.split("_")[0];
  const m = /_((?:1[89]|20)\d\d)(?!\d)/.exec(p.id); p.yr = m ? +m[1] : null;
  p.tagset = new Set([...(p.tags||[]), ...(sharedName(p) ? ["Shared by " + sharedName(p)] : [])]);
});
const allTags = (() => {
  const n = new Map();
  papers.forEach(p => p.tagset.forEach(t => n.set(t, (n.get(t)||0) + 1)));
  const shr = t => t.startsWith("Shared by ") ? 1 : 0;
  return [...n].sort((a,b) => shr(a[0]) - shr(b[0]) || a[0].localeCompare(b[0])).map(([t,c]) => ({t, c}));
})();
const TKEY = "pn-tags-" + DATA.page.folder, SKEY = "pn-sort-" + DATA.page.folder;
const tSaved = store.get(TKEY, {}) || {};
let tagMode = tSaved.mode==="except" ? "except" : "only";
let tagSel = new Set((Array.isArray(tSaved.sel) ? tSaved.sel : []).filter(t => allTags.some(x => x.t===t)));
const saveTags = () => store.set(TKEY, {mode: tagMode, sel: [...tagSel]});
const sortSel = document.getElementById("sort");
let sortBy = store.get(SKEY, "default");
if (![...sortSel.options].some(o => o.value===sortBy)) sortBy = "default";
sortSel.value = sortBy;
const cmpAu = (a,b) => a.au.localeCompare(b.au, undefined, {sensitivity: "base"});
const noYr = p => p.yr===null ? 1 : 0;
const byYear = dir => (a,b) => noYr(a) - noYr(b) || (noYr(a) ? 0 : dir*(a.yr - b.yr)) || cmpAu(a,b) || a.ord - b.ord;
const SORTFN = {
  "author-az": (a,b) => cmpAu(a,b) || (a.yr ?? 9999) - (b.yr ?? 9999) || a.ord - b.ord,
  "author-za": (a,b) => cmpAu(b,a) || (a.yr ?? 9999) - (b.yr ?? 9999) || a.ord - b.ord,
  "year-new": byYear(-1),
  "year-old": byYear(1)
};
const tagOK = p => !tagSel.size || ([...tagSel].some(t => p.tagset.has(t)) === (tagMode==="only"));
const visible = () => {
  const l = papers.filter(p => (!activeCats.size || activeCats.has(p.category)) && tagOK(p));
  return SORTFN[sortBy] ? l.sort(SORTFN[sortBy]) : l;
};
const filterLabel = () => [activeCats.size ? [...activeCats].join(", ") : "",
  tagSel.size ? (tagMode==="only" ? "Only " : "Except ") + [...tagSel].join(", ") : ""].filter(Boolean).join(" · ") || "All papers";
function renderTags(){
  document.getElementById("tagf").hidden = !allTags.length;
  document.querySelectorAll("#tmode [data-mode]").forEach(b => b.setAttribute("aria-pressed", b.dataset.mode===tagMode));
  document.getElementById("thint").textContent = tagMode==="only"
    ? "Show only papers that have any checked tag." : "Hide papers that have any checked tag.";
  document.getElementById("taglist").innerHTML = allTags.map(({t,c}) =>
    `<label class="tagi"><input type="checkbox" value="${esc(t)}"${tagSel.has(t) ? " checked" : ""}><span>${esc(t)}</span><small>${c}</small></label>`).join("");
  renderCount();
}
function renderCount(){
  const n = visible().length, on = tagSel.size > 0;
  document.getElementById("vcount").textContent = `${n} of ${papers.length} papers`;
  document.getElementById("tagsum").textContent = on ? ` (${tagMode} ${tagSel.size}) · ${n} of ${papers.length}` : "";
  document.getElementById("tagf").classList.toggle("on", on);
  document.getElementById("tclear").disabled = !on;
}
function refresh(){  // re-render everything that depends on visible()
  renderCount(); renderList();
  if (query){ const d = document.body.classList.contains("drawer"); doSearch(); document.body.classList.toggle("drawer", d); }
  else if (!current) renderHome();
}
document.getElementById("taglist").onchange = e => {
  const c = e.target.closest("input[type=checkbox]"); if (!c) return;
  c.checked ? tagSel.add(c.value) : tagSel.delete(c.value);
  saveTags(); refresh();
};
document.getElementById("tmode").onclick = e => {
  const b = e.target.closest("[data-mode]"); if (!b || b.dataset.mode===tagMode) return;
  tagMode = b.dataset.mode; saveTags(); renderTags(); refresh();
};
document.getElementById("tclear").onclick = () => { tagSel.clear(); saveTags(); renderTags(); refresh(); };
sortSel.onchange = () => { sortBy = sortSel.value; store.set(SKEY, sortBy); refresh(); };'''),
    ("renderCats(); renderList(); if (!current && !query) renderHome();",
     "renderCats(); refresh();"),
    ('Study ${activeCats.size ? "these categories" : "everything"}',
     'Study ${tagSel.size ? "these papers" : activeCats.size ? "these categories" : "everything"}'),
    ('activeCats.size ? [...activeCats].join(", ") : "All papers");',
     'filterLabel());'),
    ('    ${groups.map(c => `<div class="grp"',
     '    ${list.length ? "" : `<p class="empty">No papers match the chosen topics and tags.</p>`}\n'
     '    ${groups.map(c => `<div class="grp"'),
    ("renderCats(); route();", "renderCats(); renderTags(); route();"),
]
for old, new in REPL:
    n = html.count(old)
    if n != 1:
        sys.exit(f"expected exactly 1 match, found {n}: {old[:70]!r}")
    html = html.replace(old, new)

(HERE / "template.html").write_text(html, encoding="utf-8")
print("wrote", HERE / "template.html")
