# blog-post-generator-v2

Generate a publication-ready, SEO-audited blog post from a content outline and
research notes — as a deterministic Python library or a one-command CLI.

**The problem:** drafting SEO posts from outlines is mechanical and easy to get
wrong. Writers restate the same sentence five times chasing keyword density,
leave the meta description half-empty, pad or starve the word count, and ship
claims their research notes never supported. Reviewing every draft by hand does
not scale.

**The solution:** a generator that builds the draft *from* the research notes —
every section paragraph opens with an outline point and is grounded by a
sentence quoted from the notes (or explicitly flagged as unsourced), then runs
a deterministic SEO audit over its own output and reports title/meta/keyword/
density/length/H2 checks as a Markdown report. The same inputs always produce
the same post, byte for byte.

## How it works

```
outline.json ─┐
              ├─▶ generate.py ─▶ Post (markdown, slug, meta, AuditReport)
notes.md ─────┘         │
                        ├─▶ research.py  parses facts, terms, open questions
                        ├─▶ content.py   outline → prose paragraphs
                        ├─▶ seo.py       slugify + front matter + audit checks
                        └─▶ render.py    front matter + body assembly
```

1. **`research.py`** parses Markdown notes: `Facts:` bullets (each ends with a
   `source:` tag), `Terms:` bullets, and `Questions:` bullets it cannot answer.
2. **`content.py`** turns each outline section into a paragraph: the outline
   point first, then a supporting fact matched by word overlap — verified facts
   strengthen the claim; unmatched questions render as an explicit *"the notes
   do not answer this yet"* gap instead of invented filler.
3. **`seo.py`** builds YAML front matter (title, description, slug, keywords)
   and audits the body: title length, meta length, keyword in title, keyword in
   the opening paragraph, keyphrase density (occurrences per 100 words),
   minimum body length, and H2 section count.
4. **`render.py`** assembles front matter + body and writes the post and audit
   report files.

Nothing calls the network, nothing mutates global state, and ordering is fully
deterministic — `sort()` everywhere a set is used, stable matching order, no
wall-clock reads. Two runs on the same inputs diff to zero, which the test
suite asserts.

## Getting started

Requires Python 3.9+ and pytest. No runtime dependencies.

```bash
git clone https://github.com/Retsumdk/blog-post-generator-v2.git
cd blog-post-generator-v2
pip install -r requirements.txt
python -m pytest -q        # 19 tests
```

Or straight from GitHub (also installs the `bpgen` console script):

```bash
pip install git+https://github.com/Retsumdk/blog-post-generator-v2.git
```

## CLI

```bash
bpgen examples/outline.json \
    --notes examples/notes.md \
    --date 2026-10-23 \
    --out draft.md \
    --audit audit.md
cat audit.md
```

Output (`audit.md`) on the bundled example:

```
# SEO audit — Static Site Search with Lunr.js: A Practical Guide

- Keyword: **static site search**
- Words: **322**
- Density: **0.93%**
- Checks passed: **7/7**

| Check | Status | Detail |
|---|---|---|
| title_length | PASS | title is 50 chars (target 30-60) |
| meta_length | PASS | meta description is 140 chars (minimum 70, max 155) |
| keyword_in_title | PASS | keyword 'static site search' present in title |
| keyword_early | PASS | keyword appears in the opening paragraph |
| keyword_density | PASS | 0.93% per 100 words (target 0.5-3.0%) |
| word_count | PASS | body is 322 words (minimum 300) |
| h2_sections | PASS | body has 7 H2 sections (minimum 3) |
```

Omit `--audit` to skip the report; omit `--out` to print the post to stdout.
Exit code is `0` when the draft renders, `1` on bad arguments or missing files.

## Library usage

```python
from blog_post_generator_v2.generate import build_post, load_notes, load_outline
from blog_post_generator_v2.seo import strip_front_matter

outline = load_outline("examples/outline.json")
notes = load_notes("examples/notes.md")
post = build_post(outline, notes)

print(post.title)          # 'Static Site Search with Lunr.js: A Practical Guide'
print(post.slug)           # 'static-site-search-with-lunrjs-a-practical-guide'
print(len(post.meta_description))  # 140
print(post.audit.words)    # 322
print(post.audit.warnings) # [] — every check passed

body = strip_front_matter(post.markdown)
assert "static site search" in body
```

`AuditReport.checks` is a list of `Check` records (`name`, `status`, `detail`)
so CI can fail a build on any `WARN`.

## Input formats

`outline.json` — `audience`, `keyword`, `title_template`, and a `sections`
array of `{heading, points[]}`:

```json
{
  "audience": "frontend developers",
  "keyword": "static site search",
  "title_template": "{topic}: A Practical Guide",
  "sections": [
    {
      "heading": "Why client-side search works",
      "points": [
        "no server infrastructure means zero operating cost for small sites"
      ]
    }
  ]
}
```

`notes.md` — plain Markdown with labeled sections:

```markdown
Facts:
- A prebuilt Lunr index for 500 documents is roughly 80 KB gzipped. source: benchmark.md
- Highlight matched terms with <mark> so users can verify relevance instantly. source: ux-notes.md

Questions:
- How do we keep p95 latency under 50 ms on mid-range phones?

Terms:
- Lunr.js, debounce, CDN
```

Questions the notes cannot answer render as an explicit gap in the draft —
the generator never invents a source.

## Design notes

- **Determinism:** no wall-clock reads or iteration over unordered sets; the
  publish date comes from `--date` / the `date` argument, never `today()`.
- **Provenance:** facts carry a `source:` tag; unmatched questions surface as
  visible gaps so a human closes them before publishing.
- **Density math:** keyphrase density counts occurrences per 100 words, so a
  three-word phrase is not inflated the way naive substring density is.

## Scope

Python 3.9+ stdlib only; pytest is a dev dependency. This is a deterministic
draft generator and auditor — it does not call LLM APIs, publish anywhere, or
touch a CMS. Feed its output to your publishing pipeline.

## License

[MIT](LICENSE) © Retsumdk
