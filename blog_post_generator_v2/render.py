"""Markdown rendering for the generated post and the SEO audit report."""
from __future__ import annotations

from .seo import META_MAX, META_MIN, TITLE_MAX, TITLE_MIN, yaml_scalar


def render_markdown(title: str, description: str, slug: str, keywords: list[str],
                    date: str | None, body: str) -> str:
    lines = ["---", f"title: {yaml_scalar(title)}", f"description: {yaml_scalar(description)}",
             f"slug: {yaml_scalar(slug)}", "keywords:"]
    lines.extend(f"  - {yaml_scalar(k)}" for k in keywords)
    if date:
        lines.append(f"date: {yaml_scalar(date)}")
    lines.extend(["---", "", body])
    return "\n".join(lines) + "\n"


def render_audit_markdown(post) -> str:
    a = post.audit
    passed = len(a.checks) - len(a.warnings)
    out = [
        f"# SEO audit — {post.title}", "",
        f"- Keyword: **{a.keyword}**",
        f"- Words: **{a.words}**",
        f"- Density: **{a.density:.2f}%**",
        f"- Checks passed: **{passed}/{len(a.checks)}**", "",
        "| Check | Status | Detail |", "|---|---|---|",
    ]
    for c in a.checks:
        status = "PASS" if c.passed else "WARN"
        out.append(f"| {c.name} | {status} | {c.detail} |")
    out.extend(["", f"Targets: title {TITLE_MIN}-{TITLE_MAX} chars, meta {META_MIN}-{META_MAX} chars, "
                    "body length and density floors enforced by the audit module.", ""])
    return "\n".join(out)
