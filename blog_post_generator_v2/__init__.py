"""blog-post-generator-v2: deterministic SEO blog-post drafts from outlines + notes.

Zero runtime dependencies. The same inputs always produce byte-identical output.
"""
from .generate import (
    GeneratedPost,
    Notes,
    Outline,
    OutlineError,
    Section,
    build_audit_report,
    build_post,
    load_notes,
    load_outline,
)
from .seo import SeoAudit, SeoCheck, audit_post, keyword_density, slugify

__version__ = "2.0.0"

__all__ = [
    "GeneratedPost", "Notes", "Outline", "OutlineError", "Section",
    "SeoAudit", "SeoCheck", "build_audit_report", "build_post", "load_notes",
    "load_outline", "audit_post", "keyword_density", "slugify", "__version__",
]
