"""SEO primitives: tokenizing, keyword scoring, slugs, meta descriptions, audits.

Pure functions over plain strings — no I/O, no randomness, fully deterministic.
"""
from __future__ import annotations

import json
import re
from collections import Counter
from dataclasses import dataclass, field

WORD_RE = re.compile(r"[a-z0-9']+")

STOPWORDS = frozenset(
    """a about above after again against all am an and any are aren as at be because
    been before being below between both but by can cannot could did do does doing
    don down during each few for from further had has have having he her here hers
    herself him himself his how i if in into is it its itself just ll me more most
    my myself no nor not now of off on once only or other our ours ourselves out over
    own re s same she should so some such t than that the their theirs them themselves
    then there these they this those through to too under until up ve very was we were
    what when where which while who whom why will with won would you your yours
    yourself yourselves it's don't we're they're you're that's there's can't isn't
    also however therefore thus within without across among using use used may might
    one two get got make makes made much many thing things""".split()
)

TITLE_MIN, TITLE_MAX = 30, 60
META_MAX = 155
META_MIN = 70
DENSITY_MIN = 0.5
DENSITY_MAX = 3.0
MIN_WORDS = 300
MIN_H2 = 3


def tokenize(text: str) -> list[str]:
    return WORD_RE.findall(text.lower())


def word_count(text: str) -> int:
    return len(tokenize(text))


def content_words(text: str) -> list[str]:
    return [w for w in tokenize(text) if len(w) > 2 and w not in STOPWORDS]


def keyword_scores(text: str) -> Counter[str]:
    return Counter(content_words(text))


def top_keywords(text: str, limit: int = 8) -> list[tuple[str, int]]:
    return keyword_scores(text).most_common(limit)


def slugify(title: str, max_words: int = 8) -> str:
    cleaned = re.sub(r"[^a-z0-9\s-]", "", title.lower())
    words = cleaned.split()
    return "-".join(words[:max_words]) or "untitled"


def sentence(s: str) -> str:
    s = " ".join(s.strip().split())
    if not s:
        return s
    s = s[0].upper() + s[1:]
    if s[-1] not in ".!?":
        s += "."
    return s


def build_meta_description(text: str, max_len: int = META_MAX) -> str:
    """Assemble the first sentences of `text` into a description <= max_len chars."""
    text = " ".join(text.strip().split())
    if not text:
        return ""
    sentences = re.split(r"(?<=[.!?])\s+", text)
    out = sentences[0]
    for s in sentences[1:]:
        candidate = f"{out} {s}"
        if len(candidate) > max_len:
            break
        out = candidate
    if len(out) > max_len:
        trimmed = out[: max_len - 1]
        cut = trimmed.rfind(" ")
        out = (trimmed[:cut] if cut > 0 else trimmed).rstrip(",;:") + "…"
    return out


def phrase_count(text: str, phrase: str) -> int:
    """Case-insensitive occurrences of `phrase`, respecting word boundaries."""
    pattern = r"\b" + re.escape(phrase.lower()) + r"\b"
    return len(re.findall(pattern, text.lower()))


def keyword_density(text: str, phrase: str) -> float:
    """Keyphrase density as used by mainstream SEO tools: occurrences per 100 words."""
    total = word_count(text)
    if total == 0:
        return 0.0
    return phrase_count(text, phrase) / total * 100


@dataclass
class SeoCheck:
    name: str
    passed: bool
    detail: str


@dataclass
class SeoAudit:
    keyword: str
    words: int
    density: float
    checks: list[SeoCheck] = field(default_factory=list)

    @property
    def warnings(self) -> list[str]:
        return [c.detail for c in self.checks if not c.passed]

    def to_dict(self) -> dict:
        return {
            "keyword": self.keyword,
            "words": self.words,
            "density_pct": round(self.density, 2),
            "passed": len(self.checks) - len(self.warnings),
            "total_checks": len(self.checks),
            "warnings": self.warnings,
        }


def audit_post(markdown_body: str, title: str, meta: str, keyword: str) -> SeoAudit:
    body = strip_front_matter(markdown_body)
    kw = keyword.lower()
    checks: list[SeoCheck] = []

    checks.append(SeoCheck(
        "title_length",
        TITLE_MIN <= len(title) <= TITLE_MAX,
        f"title is {len(title)} chars (target {TITLE_MIN}-{TITLE_MAX})",
    ))
    checks.append(SeoCheck(
        "meta_length",
        len(meta) >= META_MIN,
        f"meta description is {len(meta)} chars (minimum {META_MIN}, max {META_MAX})",
    ))
    checks.append(SeoCheck(
        "keyword_in_title",
        kw in title.lower(),
        f"keyword '{keyword}' {'present in' if kw in title.lower() else 'missing from'} title",
    ))
    first_block = " ".join(body.split()[:40])
    checks.append(SeoCheck(
        "keyword_early",
        kw in first_block.lower(),
        f"keyword '{keyword}' {'appears in' if kw in first_block.lower() else 'missing from'} the opening paragraph",
    ))
    density = keyword_density(body, keyword)
    checks.append(SeoCheck(
        "keyword_density",
        DENSITY_MIN <= density <= DENSITY_MAX,
        f"keyphrase density is {density:.2f}% occurrences-per-100-words (target {DENSITY_MIN}-{DENSITY_MAX}%)",
    ))
    words = word_count(body)
    checks.append(SeoCheck(
        "word_count",
        words >= MIN_WORDS,
        f"body is {words} words (minimum {MIN_WORDS})",
    ))
    h2s = len(re.findall(r"^##\s", body, flags=re.M))
    checks.append(SeoCheck(
        "h2_sections",
        h2s >= MIN_H2,
        f"body has {h2s} H2 sections (minimum {MIN_H2})",
    ))
    return SeoAudit(keyword=keyword, words=words, density=density, checks=checks)


def strip_front_matter(markdown: str) -> str:
    if markdown.startswith("---\n"):
        end = markdown.find("\n---\n", 4)
        if end != -1:
            return markdown[end + 5:].lstrip("\n")
    return markdown


def yaml_scalar(value: str) -> str:
    """Quote a scalar safely for YAML front matter (JSON double-quoted is valid YAML)."""
    return json.dumps(value, ensure_ascii=False)
