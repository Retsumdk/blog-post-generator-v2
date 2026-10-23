"""Post generation: outline + research notes -> a complete structured draft.

Deterministic by construction: the same outline and notes always produce the
same post byte-for-byte. No LLM calls, no network, no randomness.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from .render import render_markdown, render_audit_markdown
from .seo import (
    SeoAudit,
    audit_post,
    build_meta_description,
    sentence,
    slugify,
    top_keywords,
)

MAX_PREVIEW_SECTIONS = 4
FAQ_FALLBACK = (
    "The research notes for this outline do not answer this question yet. "
    "Add a source fact covering it and regenerate."
)


class OutlineError(ValueError):
    """Raised when an outline file fails validation."""


@dataclass
class Section:
    heading: str
    points: list[str] = field(default_factory=list)


@dataclass
class Outline:
    title: str
    primary_keyword: str
    audience: str = "readers"
    sections: list[Section] = field(default_factory=list)


@dataclass
class Notes:
    facts: list[str] = field(default_factory=list)
    questions: list[str] = field(default_factory=list)


@dataclass
class GeneratedPost:
    title: str
    slug: str
    meta_description: str
    keywords: list[str]
    markdown: str
    audit: SeoAudit


def load_outline(path: str | Path) -> Outline:
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except FileNotFoundError as e:
        raise OutlineError(f"outline file not found: {path}") from e
    except json.JSONDecodeError as e:
        raise OutlineError(f"outline is not valid JSON: {e}") from e
    if not isinstance(data, dict):
        raise OutlineError("outline must be a JSON object")
    title = data.get("title")
    keyword = data.get("primary_keyword")
    if not isinstance(title, str) or not title.strip():
        raise OutlineError("outline needs a non-empty 'title' string")
    if not isinstance(keyword, str) or not keyword.strip():
        raise OutlineError("outline needs a non-empty 'primary_keyword' string")
    sections: list[Section] = []
    raw_sections = data.get("sections", [])
    if not isinstance(raw_sections, list):
        raise OutlineError("'sections' must be a list")
    for i, raw in enumerate(raw_sections):
        if not isinstance(raw, dict) or not isinstance(raw.get("heading"), str):
            raise OutlineError(f"section {i} needs a 'heading' string")
        points = raw.get("points", [])
        if not isinstance(points, list) or not all(isinstance(p, str) for p in points):
            raise OutlineError(f"section {i} 'points' must be a list of strings")
        sections.append(Section(heading=raw["heading"], points=points))
    audience = data.get("audience", "readers")
    if not isinstance(audience, str):
        raise OutlineError("'audience' must be a string")
    return Outline(title=title.strip(), primary_keyword=keyword.strip(),
                   audience=audience, sections=sections)


def load_notes(path: str | Path) -> Notes:
    """Parse a markdown research-notes file.

    Lines ending in '?' (or prefixed with 'q:') become FAQ questions;
    every other non-heading line becomes a fact. Bullet markers are stripped.
    """
    notes = Notes()
    try:
        text = Path(path).read_text(encoding="utf-8")
    except FileNotFoundError as e:
        raise OutlineError(f"notes file not found: {path}") from e
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        line = line.lstrip("-* ").strip()
        if not line:
            continue
        if line.lower().startswith("q:"):
            notes.questions.append(line[2:].strip())
        elif line.endswith("?"):
            notes.questions.append(line)
        else:
            notes.facts.append(line)
    return notes


def _best_match(source: str, candidates: list[str], used: set[str]) -> str | None:
    """Deterministic best-overlap match from `candidates` against `source`."""
    from .seo import content_words
    src = set(content_words(source))
    best, best_score = None, 0
    for c in candidates:
        if c in used:
            continue
        score = len(src & set(content_words(c)))
        if score > best_score:
            best, best_score = c, score
    return best


def _intro(outline: Outline) -> list[str]:
    kw = outline.primary_keyword
    p1 = sentence(
        f"If you are {outline.audience} looking for a practical handle on {kw}, "
        f"this guide walks through what actually matters and why"
    )
    names = [s.heading.lower() for s in outline.sections[:MAX_PREVIEW_SECTIONS]]
    if names:
        listed = ", ".join(names[:-1]) + f" and {names[-1]}" if len(names) > 1 else names[0]
        p2 = sentence(
            f"It covers {listed}, with every section grounded in the research "
            f"notes behind this outline"
        )
    else:
        p2 = sentence(f"Use it as a working draft for your {kw} content")
    return [p1, p2]


def _section_paragraphs(outline: Outline, section: Section,
                        notes: Notes, used_facts: set[str]) -> list[str]:
    paragraphs: list[str] = []
    for point in section.points:
        para = sentence(point)
        fact = _best_match(point, notes.facts, used_facts)
        if fact:
            para = f"{para} {sentence(fact)}"
            used_facts.add(fact)
        paragraphs.append(para)
    if not paragraphs:
        fact = _best_match(section.heading, notes.facts, used_facts)
        if fact:
            paragraphs.append(sentence(fact))
            used_facts.add(fact)
        else:
            paragraphs.append(sentence(
                f"Add the key points for this section to the outline to complete "
                f"the draft"
            ))
    return paragraphs


def _faq(notes: Notes, used_facts: set[str]) -> list[tuple[str, str]]:
    qa: list[tuple[str, str]] = []
    used: set[str] = set()
    for question in notes.questions:
        picks: list[str] = []
        for _ in range(2):
            fact = _best_match(question, notes.facts, used | set(picks) | used_facts)
            if not fact:
                break
            picks.append(fact)
        if picks:
            used.update(picks)
            used_facts.update(picks)
            answer = " ".join(sentence(f) for f in picks)
        else:
            answer = FAQ_FALLBACK
        qa.append((question, answer))
    return qa


def _takeaways(outline: Outline) -> list[str]:
    items = [sentence(f"{s.heading}: {s.points[0]}") if s.points
             else sentence(f"{s.heading}") for s in outline.sections]
    items.append(sentence("Revisit the checklist above before publishing"))
    return items


def build_post(outline: Outline, notes: Notes, date: str | None = None) -> GeneratedPost:
    """Generate the full draft and its SEO audit. Deterministic."""
    used_facts: set[str] = set()
    intro = _intro(outline)
    intro.append(sentence(
        f"Read the sections in order, or jump to the FAQ if a specific question "
        f"about {outline.primary_keyword} is already on your mind"
    ))
    meta = build_meta_description(" ".join(intro))

    keywords = [outline.primary_keyword]
    corpus = " ".join(
        [outline.title, outline.primary_keyword]
        + [p for s in outline.sections for p in s.points]
        + notes.facts
    )
    for word, _score in top_keywords(corpus, limit=7):
        if word not in keywords and word not in outline.primary_keyword.lower():
            keywords.append(word)

    body_parts: list[str] = [
        f"# {outline.title}",
        "",
        intro[0],
        "",
        intro[1],
        "",
    ]
    for section in outline.sections:
        body_parts.append(f"## {section.heading}")
        body_parts.append("")
        body_parts.extend(p + "\n" for p in _section_paragraphs(
            outline, section, notes, used_facts))
    if notes.questions:
        body_parts.append("## Frequently asked questions")
        body_parts.append("")
        for q, a in _faq(notes, used_facts):
            body_parts.append(f"### {q}")
            body_parts.append("")
            body_parts.append(a + "\n")
    body_parts.append("## How to use this draft")
    body_parts.append("")
    body_parts.append(sentence(
        f"Every section paragraph starts from an outline point, and supporting "
        f"sentences quote the research notes verbatim"
    ))
    body_parts.append(sentence(
        "Expand the thin spots with your own voice, verify each fact against its "
        "source, and adjust the title and meta description before publishing"
    ))
    body_parts.append("")

    body_parts.append("## Key takeaways")
    body_parts.append("")
    body_parts.extend(f"- {t}" for t in _takeaways(outline))
    body_parts.append("")
    body_parts.append("## Next steps")
    body_parts.append("")
    body_parts.append(sentence(
        f"Turn the takeaways into a checklist, ship the draft, and measure how "
        f"your {outline.audience} respond before iterating on the next post"
    ))

    markdown = render_markdown(
        title=outline.title,
        description=meta,
        slug=slugify(outline.title),
        keywords=keywords,
        date=date,
        body="\n".join(body_parts),
    )
    audit = audit_post(markdown, outline.title, meta, outline.primary_keyword)
    return GeneratedPost(
        title=outline.title,
        slug=slugify(outline.title),
        meta_description=meta,
        keywords=keywords,
        markdown=markdown,
        audit=audit,
    )


def build_audit_report(post: GeneratedPost) -> str:
    return render_audit_markdown(post)
