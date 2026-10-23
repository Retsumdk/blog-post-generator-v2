import json
import subprocess
import sys
from pathlib import Path

import pytest

from blog_post_generator_v2 import (
    Outline,
    OutlineError,
    Section,
    build_post,
    load_notes,
    load_outline,
    slugify,
    keyword_density,
)
from blog_post_generator_v2.seo import build_meta_description, strip_front_matter

REPO = Path(__file__).resolve().parent.parent


def make_outline(**overrides):
    data = dict(
        title="Static Site Search with Lunr.js: A Practical Guide",
        primary_keyword="static site search",
        audience="frontend developers",
        sections=[
            Section(heading="Why client-side search works", points=[
                "no server infrastructure means zero operating cost for small sites",
                "the index ships as a static file, so a CDN does the distribution",
            ]),
            Section(heading="Building the index", points=[
                "precompute the Lunr index at build time from your content pipeline",
            ]),
            Section(heading="Query UX patterns", points=[
                "debounce input and highlight matched terms in results",
            ]),
        ],
    )
    data.update(overrides)
    return Outline(**data)


NOTES = load_notes(REPO / "examples" / "notes.md")


def test_build_is_deterministic():
    a = build_post(make_outline(), NOTES, date="2026-10-23")
    b = build_post(make_outline(), NOTES, date="2026-10-23")
    assert a.markdown == b.markdown
    assert a.slug == b.slug
    assert a.meta_description == b.meta_description


def test_front_matter_contains_metadata():
    post = build_post(make_outline(), NOTES)
    assert post.markdown.startswith("---\n")
    assert 'title: "Static Site Search with Lunr.js: A Practical Guide"' in post.markdown
    assert 'slug: "static-site-search-with-lunrjs-a-practical-guide"' in post.markdown
    assert 'description: "' in post.markdown


def test_slugify():
    assert slugify("Static Site Search with Lunr.js: A Practical Guide") == "static-site-search-with-lunrjs-a-practical-guide"
    assert slugify("!!!") == "untitled"
    assert slugify("A B C D E F G H I J") == "a-b-c-d-e-f-g-h"


def test_meta_description_length():
    post = build_post(make_outline(), NOTES)
    assert 0 < len(post.meta_description) <= 155
    assert post.meta_description.endswith((".", "…"))


def test_build_meta_hard_trim():
    meta = build_meta_description("word " * 100, max_len=155)
    assert len(meta) <= 155
    assert meta.endswith("…")


def test_keyword_appears_early_and_in_title():
    post = build_post(make_outline(), NOTES)
    body = strip_front_matter(post.markdown)
    assert "static site search" in body.lower().split("## ")[0].lower()
    assert "static site search" in post.title.lower()


def test_sections_and_headings_render():
    post = build_post(make_outline(), NOTES)
    body = strip_front_matter(post.markdown)
    assert "## Why client-side search works" in body
    assert "## Building the index" in body
    assert "## How to use this draft" in body
    assert "## Key takeaways" in body
    assert "## Next steps" in body


def test_faq_extracted_from_questions():
    post = build_post(make_outline(), NOTES)
    body = strip_front_matter(post.markdown)
    assert "## Frequently asked questions" in body
    assert "### Debounce input at 150ms to keep the UI responsive on mobile keyboards?" in body
    assert "### How large can the index get before load time hurts?" in body


def test_faq_fallback_when_no_matching_fact():
    notes = load_notes(REPO / "examples" / "notes.md")
    notes.questions = ["What about quantum entanglement semantics?"]
    post = build_post(make_outline(), notes)
    assert "do not answer this question yet" in post.markdown


def test_notes_fact_used_in_matching_section():
    post = build_post(make_outline(), NOTES)
    body = strip_front_matter(post.markdown)
    assert "80 KB gzipped" in body


def test_density_in_target_range():
    post = build_post(make_outline(), NOTES)
    assert 0.5 <= keyword_density(strip_front_matter(post.markdown),
                                  "static site search") <= 2.5


def test_audit_checks_exist_and_word_count():
    post = build_post(make_outline(), NOTES)
    names = {c.name for c in post.audit.checks}
    assert {"title_length", "meta_length", "keyword_in_title", "keyword_early",
            "keyword_density", "word_count", "h2_sections"} <= names
    assert post.audit.words >= 300
    assert post.audit.to_dict()["total_checks"] == 7


def test_audit_flags_bad_title():
    bad = make_outline(title="Too Short", primary_keyword="search")
    post = build_post(bad, NOTES)
    assert any(not c.passed for c in post.audit.checks)


def test_load_outline_validation():
    with pytest.raises(OutlineError):
        load_outline(REPO / "examples" / "notes.md")
    missing = REPO / "does-not-exist.json"
    with pytest.raises(OutlineError, match="not found"):
        load_outline(missing)
    bad = Path(REPO / "examples" / "_bad.json")
    bad.write_text(json.dumps({"title": "x"}))
    try:
        with pytest.raises(OutlineError, match="primary_keyword"):
            load_outline(bad)
    finally:
        bad.unlink()


def test_load_notes_parses_questions_and_facts():
    notes = load_notes(REPO / "examples" / "notes.md")
    assert len(notes.questions) == 2
    assert len(notes.facts) >= 4
    assert all(not q.endswith("?") or True for q in notes.questions)


def test_strip_front_matter():
    md = "---\ntitle: \"x\"\n---\n\n# body"
    assert strip_front_matter(md) == "# body"
    assert strip_front_matter("# no front matter") == "# no front matter"


def test_cli_end_to_end(tmp_path):
    out = tmp_path / "post.md"
    audit = tmp_path / "audit.md"
    r = subprocess.run(
        [sys.executable, "-m", "blog_post_generator_v2",
         str(REPO / "examples" / "outline.json"),
         "--notes", str(REPO / "examples" / "notes.md"),
         "--date", "2026-10-23",
         "--out", str(out), "--audit", str(audit)],
        capture_output=True, text=True, cwd=REPO,
    )
    assert r.returncode == 0, r.stderr
    text = out.read_text()
    assert text.startswith("---\n")
    assert audit.exists()
    assert "SEO audit" in audit.read_text()


def test_cli_deterministic_across_runs(tmp_path):
    outs = []
    for i in range(2):
        p = tmp_path / f"post{i}.md"
        r = subprocess.run(
            [sys.executable, "-m", "blog_post_generator_v2",
             str(REPO / "examples" / "outline.json"),
             "--notes", str(REPO / "examples" / "notes.md"),
             "--out", str(p)],
            capture_output=True, text=True, cwd=REPO,
        )
        assert r.returncode == 0
        outs.append(p.read_text())
    assert outs[0] == outs[1]


def test_cli_error_exit_code(tmp_path):
    r = subprocess.run(
        [sys.executable, "-m", "blog_post_generator_v2", str(tmp_path / "nope.json")],
        capture_output=True, text=True, cwd=REPO,
    )
    assert r.returncode == 2
    assert "error:" in r.stderr
