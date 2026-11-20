# Task: sorting and tag filtering on the paper-notes pages

Requested by Marta on 2026-11-20, to be done on Wednesday 2026-11-25 if usage is left.

You are working in `~/literature/notes_builder/`. The five pages
`~/literature/papers/<folder>/paper_notes_<folder>.html` are generated: **never edit them directly**.
Change only:
- `00_make_template.py` (it turns `reference/example_paper_notes.html` into `template.html` through a
  list of exact text replacements `REPL`; add new replacements at the end of that list, each must match
  exactly once in the text produced so far; read the file first to see how it works), and
- `02_build_html.py` (it fills `DATA` for each page), only if you need extra data per paper.

Then rebuild with `python3 -I 00_make_template.py` and `python3 -I 02_build_html.py`, and check every page with `./check_pages.sh`
(it runs `node --check` on every page script and prints the number of papers per page; the numbers must not change). These three commands are the only shell commands you are allowed to run.

## 1. Sorting (each page separately)

Add a "Sort" dropdown in the sidebar (under the search box, near the topic chips). Options:
- Default (current order)
- Author A→Z, Author Z→A (by the paper id, e.g. "Haberle_2014" → "Haberle")
- Year newest first, Year oldest first (year from the id, e.g. "_2014"; papers without a year go last)

The chosen order applies to the paper list in the sidebar and to the papers inside each topic group
on the home view. Remember the choice per page in localStorage (use the existing `store` helper;
key e.g. "pn-sort-" + DATA.page.folder).

## 2. Filtering by tags (each page separately)

Keep the current topic chips (categories) exactly as they are.

Add a "Tags" dropdown (e.g. a `<details>` panel or similar) listing the tags that occur on **that page**:
- every value in `p.tags` (e.g. "Basics", "Important", "External notes", "Damir's paper", and any
  future tag), and
- "Shared by <name>" for papers that have `p.shared` (e.g. "Shared by Damir"; `p.shared` looks like
  "Damir · 2026", use the part before " · ").
Do NOT include "Open paper", "Preprint" or other links as tags.

Each tag has a checkbox. A mode switch with two options:
- **Only**: show papers that have ANY of the checked tags,
- **Except**: show all papers EXCEPT those that have ANY of the checked tags.
No tag checked = no tag filtering. Show how many papers are visible (e.g. "12 of 41 papers").
Tag filtering combines with the topic chips (a paper must pass both) and applies everywhere the
current `visible()` filter applies (sidebar list, home view, "Study" button, search results).
Remember checked tags + mode per page in localStorage. Add a small "clear" control.

## Must keep working (do not break)
Search, flashcards (study mode, keys 1/2/space), "known" progress, the "My comments" box, theme
toggle, mobile drawer (narrow screens), dark mode colours, badges, source notes. Use the existing CSS
variables so it looks native in light and dark mode. No external libraries, no network requests.

## Do not
Do not run git, do not push, do not change the weekly job, the notes JSONs, catalog.json,
comments, config.json or any file outside `notes_builder/` (except that `02_build_html.py` rewrites
the pages when you run it). Do not edit `template.html` by hand (it is generated).

When done, reply with a short summary of what you changed.
