"""Extract full text from arXiv papers via LaTeX source (preferred), ar5iv HTML, or PDF fallback."""

import asyncio
import gzip
import io
import json
import logging
import re
import tarfile
from datetime import datetime, timezone

import httpx
from bs4 import BeautifulSoup
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

ARXIV_EPRINT_BASE = "https://arxiv.org/e-print/"
AR5IV_BASE = "https://ar5iv.labs.arxiv.org/html/"
ARXIV_PDF_BASE = "https://arxiv.org/pdf/"
REQUEST_DELAY_SECONDS = 3.0

# ── LaTeX source extraction ─────────────────────────────────────────────

_LATEX_SECTION_RE = re.compile(
    r"\\(section|subsection|subsubsection|paragraph)\*?\{",
)

_LATEX_STRIP_ENVS = {
    "figure", "figure*", "table", "table*", "tikzpicture",
    "thebibliography", "filecontents", "comment",
}

_LATEX_STRIP_CMDS_WITH_ARGS = re.compile(
    r"\\(?:label|ref|eqref|cite[tp]?|citet|citep|nocite|bibliographystyle"
    r"|bibliography|usepackage|documentclass|newcommand|renewcommand"
    r"|DeclareMathOperator|setlength|setcounter|addtocounter"
    r"|vspace|hspace|vskip|hskip|hypersetup|graphicspath|DeclareGraphicsExtensions"
    r"|includegraphics|caption)\s*(?:\[[^\]]*\])?\s*\{[^{}]*\}"
)

_LATEX_STRIP_CMDS_STANDALONE = re.compile(
    r"\\(?:pagestyle|thispagestyle|maketitle|tableofcontents|noindent|centering"
    r"|raggedright|raggedleft|clearpage|newpage|pagebreak|bf|it|rm|tt|sc|sf"
    r"|tiny|scriptsize|footnotesize|small|normalsize|large|Large|LARGE|huge|Huge|textstyle)\b"
)


def _extract_tex_from_archive(data: bytes) -> dict[str, str] | None:
    """Extract .tex file contents from a gzip/tar archive or plain tex. Returns {filename: content}."""
    tex_files: dict[str, str] = {}

    if data[:3] == b"\x1f\x8b\x08":
        try:
            decompressed = gzip.decompress(data)
        except Exception:
            return None

        if decompressed[:5] == b"%PDF-":
            return None

        try:
            tar = tarfile.open(fileobj=io.BytesIO(decompressed))
            for member in tar.getmembers():
                if member.isfile() and member.name.endswith(".tex"):
                    f = tar.extractfile(member)
                    if f:
                        tex_files[member.name] = f.read().decode("utf-8", errors="replace")
            tar.close()
        except tarfile.TarError:
            content = decompressed.decode("utf-8", errors="replace")
            if "\\begin{document}" in content or "\\section" in content:
                tex_files["main.tex"] = content
    elif b"\\begin{document}" in data[:50000] or b"\\section" in data[:50000]:
        tex_files["main.tex"] = data.decode("utf-8", errors="replace")
    else:
        return None

    return tex_files if tex_files else None


def _find_main_tex(tex_files: dict[str, str]) -> str | None:
    """Find the main .tex file containing \\begin{document}."""
    for name, content in tex_files.items():
        if "\\begin{document}" in content:
            return name

    candidates = [n for n in tex_files if n.lower() in ("main.tex", "paper.tex", "manuscript.tex")]
    if candidates:
        return candidates[0]

    if tex_files:
        return max(tex_files, key=lambda n: len(tex_files[n]))
    return None


def _resolve_inputs(content: str, tex_files: dict[str, str], depth: int = 0) -> str:
    """Resolve \\input{} and \\include{} by inlining referenced files."""
    if depth > 10:
        return content

    def _replace(m: re.Match) -> str:
        ref = m.group(1)
        candidates = [ref, ref + ".tex"]
        for c in candidates:
            for name, body in tex_files.items():
                if name == c or name.endswith("/" + c):
                    return _resolve_inputs(body, tex_files, depth + 1)
        return ""

    return re.sub(r"\\(?:input|include)\{([^}]+)\}", _replace, content)


def _strip_comments(tex: str) -> str:
    """Remove LaTeX comments (lines starting with % or inline %)."""
    lines = []
    for line in tex.split("\n"):
        stripped = []
        i = 0
        while i < len(line):
            if line[i] == "%" and (i == 0 or line[i - 1] != "\\"):
                break
            stripped.append(line[i])
            i += 1
        lines.append("".join(stripped))
    return "\n".join(lines)


def _extract_body(tex: str) -> str:
    """Extract content between \\begin{document} and \\end{document}."""
    start = tex.find("\\begin{document}")
    if start != -1:
        tex = tex[start + len("\\begin{document}"):]
    end = tex.find("\\end{document}")
    if end != -1:
        tex = tex[:end]
    return tex


def _strip_environments(tex: str) -> str:
    """Remove entire figure/table/tikz environments."""
    for env in _LATEX_STRIP_ENVS:
        pattern = re.compile(
            r"\\begin\{" + re.escape(env) + r"\}.*?\\end\{" + re.escape(env) + r"\}",
            re.DOTALL,
        )
        tex = pattern.sub("", tex)
    return tex


def _latex_to_text(tex: str) -> str:
    """Convert LaTeX body to readable text while preserving math."""
    tex = _strip_environments(tex)

    tex = re.sub(r"\\begin\{(?:equation|align|gather|multline|eqnarray|flalign)\*?\}", r"$$", tex)
    tex = re.sub(r"\\end\{(?:equation|align|gather|multline|eqnarray|flalign)\*?\}", r"$$", tex)

    tex = re.sub(r"\\begin\{(?:itemize|enumerate|description)\}", "", tex)
    tex = re.sub(r"\\end\{(?:itemize|enumerate|description)\}", "", tex)
    tex = re.sub(r"\\item\b\s*(?:\[([^\]]*)\])?", r"• \1 ", tex)

    tex = re.sub(r"\\begin\{abstract\}", "", tex)
    tex = re.sub(r"\\end\{abstract\}", "", tex)

    tex = _LATEX_STRIP_CMDS_WITH_ARGS.sub("", tex)
    tex = _LATEX_STRIP_CMDS_STANDALONE.sub("", tex)

    tex = re.sub(r"\\textbf\{([^}]*)\}", r"\1", tex)
    tex = re.sub(r"\\textit\{([^}]*)\}", r"\1", tex)
    tex = re.sub(r"\\emph\{([^}]*)\}", r"\1", tex)
    tex = re.sub(r"\\text(?:tt|sc|sf|rm)\{([^}]*)\}", r"\1", tex)
    tex = re.sub(r"\\underline\{([^}]*)\}", r"\1", tex)
    tex = re.sub(r"\\(?:footnote|footnotetext)\{[^}]*\}", "", tex)
    tex = re.sub(r"\\(?:url|href)\{([^}]*)\}(?:\{([^}]*)\})?", r"\2 \1", tex)

    tex = re.sub(r"\\(?:left|right|bigl?|bigr?|Bigl?|Bigr?)[.|()\[\]{}\\]?", "", tex)
    tex = re.sub(r"\\(?!mathbb|mathcal|mathbf|mathrm)[a-zA-Z]+\{([^}]*)\}", r"\1", tex)

    tex = re.sub(r"(?<!\\)[{}]", "", tex)
    tex = re.sub(r"\\mathbb([A-Za-z0-9])", r"\\mathbb{\1}", tex)
    tex = re.sub(r"\\mathcal([A-Za-z0-9])", r"\\mathcal{\1}", tex)
    tex = re.sub(r"\\mathbf([A-Za-z0-9])", r"\\mathbf{\1}", tex)
    tex = re.sub(r"\\mathrm([A-Za-z0-9])", r"\\mathrm{\1}", tex)
    tex = re.sub(r"~", " ", tex)
    tex = re.sub(r"\\,", " ", tex)
    tex = re.sub(r"\\\\", "\n", tex)
    tex = re.sub(r"\\&", "&", tex)
    tex = re.sub(r"\\ ", " ", tex)

    tex = re.sub(r"\n{3,}", "\n\n", tex)
    tex = re.sub(r"[ \t]{2,}", " ", tex)

    return tex.strip()


def _extract_sections_from_latex(tex: str) -> tuple[str, list[dict]]:
    """Split raw LaTeX into sections. Returns (full_text, sections_list)."""
    sections: list[dict] = []
    current_title = "Preamble"

    abs_match = re.search(r"\\begin\{abstract\}(.*?)\\end\{abstract\}", tex, re.DOTALL)
    if abs_match:
        abs_text = _latex_to_text(abs_match.group(1)).strip()
        if abs_text:
            sections.append({"title": "Abstract", "text": abs_text})
        tex = tex[:abs_match.start()] + tex[abs_match.end():]

    body = _extract_body(tex)

    section_pattern = re.compile(
        r"\\(section|subsection|subsubsection|paragraph)\*?\{([^}]*)\}",
        re.DOTALL,
    )
    matches = list(section_pattern.finditer(body))

    if not matches:
        text_content = _latex_to_text(body).strip()
        if text_content:
            sections.append({"title": current_title, "text": text_content})
    else:
        preamble = _latex_to_text(body[: matches[0].start()]).strip()
        if preamble:
            sections.append({"title": current_title, "text": preamble})

        for idx, match in enumerate(matches):
            raw_title = match.group(2).strip()
            title = _latex_to_text(raw_title)
            title = re.sub(r"\s+", " ", title).strip() or "Untitled"

            content_start = match.end()
            content_end = matches[idx + 1].start() if idx + 1 < len(matches) else len(body)
            chunk = _latex_to_text(body[content_start:content_end]).strip()
            if chunk and len(chunk) > 10:
                sections.append({"title": title, "text": chunk})

    if not sections:
        sections.append({"title": "Full Text", "text": _latex_to_text(body).strip()})

    full_text = "\n\n".join(f"## {s['title']}\n{s['text']}" for s in sections)
    return full_text, sections


async def _try_latex_source(
    client: httpx.AsyncClient, arxiv_id: str,
) -> tuple[str, list[dict]] | None:
    """Download and extract text from LaTeX source. Returns None if unavailable."""
    url = f"{ARXIV_EPRINT_BASE}{arxiv_id}"
    try:
        resp = await client.get(url, follow_redirects=True, timeout=30.0)
        if resp.status_code != 200:
            return None

        tex_files = _extract_tex_from_archive(resp.content)
        if not tex_files:
            return None

        main_name = _find_main_tex(tex_files)
        if not main_name:
            return None

        content = tex_files[main_name]
        content = _resolve_inputs(content, tex_files)
        content = _strip_comments(content)

        if "\\begin{document}" not in content and "\\section" not in content:
            logger.debug("LaTeX source for %s has no document body", arxiv_id)
            return None

        full_text, sections = _extract_sections_from_latex(content)

        if len(full_text) < 500:
            logger.debug("LaTeX extraction for %s too short (%d chars)", arxiv_id, len(full_text))
            return None

        full_text = _sanitize_text(full_text)
        sections = [
            {**s, "text": _sanitize_text(s["text"])} for s in sections
        ]
        return full_text, sections

    except Exception as e:
        logger.debug("LaTeX source extraction failed for %s: %s", arxiv_id, e)
        return None


# ── ar5iv HTML extraction ───────────────────────────────────────────────

_HEADING_TAGS = {"h1", "h2", "h3", "h4", "h5", "h6"}
_SECTION_CLASSES = {"ltx_section", "ltx_subsection", "ltx_subsubsection", "ltx_chapter", "ltx_paragraph"}
_SKIP_CLASSES = {"ltx_bibliography", "ltx_appendix", "ltx_TOC"}


def _extract_sections_from_html(html: str) -> tuple[str, list[dict]]:
    """Parse ar5iv LaTeXML HTML into sections. Returns (full_text, sections_list)."""
    soup = BeautifulSoup(html, "lxml")

    for tag in soup.find_all(["script", "style", "nav", "footer", "header"]):
        tag.decompose()

    article = (
        soup.find("article", class_="ltx_document")
        or soup.find("div", class_="ltx_page_content")
        or soup.find("article")
        or soup
    )

    sections: list[dict] = []

    ltx_sections = article.find_all("section", class_=lambda c: c and any(s in (c if isinstance(c, list) else [c]) for s in _SECTION_CLASSES))

    if ltx_sections:
        for sec in ltx_sections:
            classes = set(sec.get("class", []))
            if classes & _SKIP_CLASSES:
                continue
            heading = sec.find(_HEADING_TAGS)
            title = heading.get_text(separator=" ", strip=True) if heading else "Untitled"
            if heading:
                heading.decompose()
            for nested in sec.find_all("section", class_=lambda c: c and any(s in (c if isinstance(c, list) else [c]) for s in _SECTION_CLASSES)):
                nested.decompose()

            body = sec.get_text(separator=" ", strip=True)
            if body and len(body) > 20:
                sections.append({"title": title, "text": body})
    else:
        current_title = "Preamble"
        current_parts: list[str] = []

        def _flush():
            body = "\n".join(current_parts).strip()
            if body:
                sections.append({"title": current_title, "text": body})

        for element in article.children:
            if not hasattr(element, "name") or element.name is None:
                continue

            el_classes = set(element.get("class", []))
            if el_classes & _SKIP_CLASSES:
                continue

            if element.name in _HEADING_TAGS:
                _flush()
                current_title = element.get_text(separator=" ", strip=True)
                current_parts = []
            else:
                block_text = element.get_text(separator=" ", strip=True)
                if block_text:
                    current_parts.append(block_text)

        _flush()

    full_text = "\n\n".join(f"## {s['title']}\n{s['text']}" for s in sections)
    return _sanitize_text(full_text), [{**s, "text": _sanitize_text(s["text"])} for s in sections]


def _sanitize_text(s: str) -> str:
    """Remove null bytes and other characters that PostgreSQL text columns reject."""
    return s.replace("\x00", "")


def _extract_text_from_pdf_bytes(pdf_bytes: bytes) -> tuple[str, list[dict]]:
    """Extract text from PDF bytes using PyMuPDF. Returns (full_text, sections)."""
    import fitz  # pymupdf

    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    full_parts: list[str] = []

    for page in doc:
        page_text = page.get_text("text")
        if page_text.strip():
            full_parts.append(page_text)

    doc.close()

    raw_text = "\n\n".join(full_parts)
    raw_text = re.sub(r"\n{3,}", "\n\n", raw_text)
    raw_text = _sanitize_text(raw_text)

    sections = _guess_sections_from_text(raw_text)
    return raw_text, sections


def _guess_sections_from_text(text_body: str) -> list[dict]:
    """Heuristic section detection from raw PDF text."""
    heading_re = re.compile(
        r"^(?:\d+\.?\s+)?(Abstract|Introduction|Related Work|Background|"
        r"Methods?|Methodology|Approach|Experiments?|Results?|Discussion|"
        r"Conclusion|Conclusions|Acknowledgm?ents?|References|Appendix)\b",
        re.IGNORECASE | re.MULTILINE,
    )

    sections: list[dict] = []
    last_end = 0
    last_title = "Preamble"

    for m in heading_re.finditer(text_body):
        chunk = text_body[last_end:m.start()].strip()
        if chunk:
            sections.append({"title": last_title, "text": chunk})
        last_title = m.group(0).strip()
        last_end = m.end()

    remaining = text_body[last_end:].strip()
    if remaining:
        sections.append({"title": last_title, "text": remaining})

    if not sections:
        sections.append({"title": "Full Text", "text": text_body.strip()})

    return sections


async def _try_ar5iv(client: httpx.AsyncClient, arxiv_id: str) -> tuple[str, list[dict]] | None:
    """Attempt to fetch and parse ar5iv HTML. Returns None if unavailable."""
    url = f"{AR5IV_BASE}{arxiv_id}"
    try:
        resp = await client.get(url, follow_redirects=True, timeout=30.0)
        if resp.status_code != 200:
            return None
        final_host = str(resp.url.host) if resp.url else ""
        if "arxiv.org" in final_host and "ar5iv" not in final_host:
            logger.debug("ar5iv redirected to arxiv.org for %s — HTML not available", arxiv_id)
            return None
        if "ltx_document" not in resp.text and "ltx_page" not in resp.text:
            logger.debug("ar5iv response for %s is not LaTeXML — skipping", arxiv_id)
            return None
        if len(resp.text) < 5000:
            return None
        return _extract_sections_from_html(resp.text)
    except Exception as e:
        logger.debug("ar5iv fetch failed for %s: %s", arxiv_id, e)
        return None


async def _try_pdf(client: httpx.AsyncClient, arxiv_id: str, pdf_url: str | None) -> tuple[str, list[dict]] | None:
    """Download and extract text from PDF. Returns None on failure."""
    url = pdf_url or f"{ARXIV_PDF_BASE}{arxiv_id}.pdf"
    try:
        resp = await client.get(url, follow_redirects=True, timeout=60.0)
        if resp.status_code != 200:
            return None
        content_type = resp.headers.get("content-type", "")
        if "pdf" not in content_type and not resp.content[:5] == b"%PDF-":
            return None
        return _extract_text_from_pdf_bytes(resp.content)
    except Exception as e:
        logger.debug("PDF fetch failed for %s: %s", arxiv_id, e)
        return None


async def extract_fulltext_batch(
    db: AsyncSession,
    batch_size: int = 20,
    prefer_html: bool = True,
) -> int:
    """Extract full text for papers that haven't been processed yet. Returns count processed."""

    result = await db.execute(text("""
        SELECT p.id, p.pdf_url
        FROM papers p
        LEFT JOIN paper_fulltext pf ON pf.paper_id = p.id
        WHERE pf.paper_id IS NULL
        ORDER BY p.published_at DESC
        LIMIT :batch_size
    """), {"batch_size": batch_size})
    rows = result.fetchall()

    if not rows:
        logger.info("No papers need fulltext extraction")
        return 0

    logger.info("Extracting fulltext for %d papers", len(rows))
    processed = 0

    upsert_sql = text("""
        INSERT INTO paper_fulltext (paper_id, source, content, sections, char_count, status, extracted_at, error_message)
        VALUES (:paper_id, :source, :content, CAST(:sections AS jsonb), :char_count, :status, :extracted_at, :error_message)
        ON CONFLICT (paper_id) DO UPDATE SET
            source = EXCLUDED.source,
            content = EXCLUDED.content,
            sections = EXCLUDED.sections,
            char_count = EXCLUDED.char_count,
            status = EXCLUDED.status,
            extracted_at = EXCLUDED.extracted_at,
            error_message = EXCLUDED.error_message
    """)

    async with httpx.AsyncClient(
        headers={"User-Agent": "arxiv-radar/1.0 (fulltext indexer)"},
    ) as client:
        for row in rows:
            arxiv_id = row.id
            pdf_url = row.pdf_url
            source = "unknown"
            try:
                result_data = None

                result_data = await _try_latex_source(client, arxiv_id)
                if result_data:
                    source = "latex"

                if result_data is None and prefer_html:
                    result_data = await _try_ar5iv(client, arxiv_id)
                    if result_data:
                        source = "ar5iv_html"

                if result_data is None:
                    result_data = await _try_pdf(client, arxiv_id, pdf_url)
                    if result_data:
                        source = "pdf"

                if result_data is None:
                    await db.execute(upsert_sql, {
                        "paper_id": arxiv_id,
                        "source": "none",
                        "content": None,
                        "sections": None,
                        "char_count": None,
                        "status": "failed",
                        "extracted_at": datetime.now(timezone.utc),
                        "error_message": "Could not retrieve from LaTeX, ar5iv, or PDF",
                    })
                else:
                    full_text, sections = result_data
                    await db.execute(upsert_sql, {
                        "paper_id": arxiv_id,
                        "source": source,
                        "content": full_text,
                        "sections": json.dumps(sections),
                        "char_count": len(full_text),
                        "status": "extracted",
                        "extracted_at": datetime.now(timezone.utc),
                        "error_message": None,
                    })

                processed += 1
                logger.info("Extracted fulltext for %s via %s (%d/%d)", arxiv_id, source, processed, len(rows))

            except Exception as e:
                logger.exception("Failed to extract fulltext for %s", arxiv_id)
                try:
                    await db.rollback()
                    await db.execute(upsert_sql, {
                        "paper_id": arxiv_id,
                        "source": "none",
                        "content": None,
                        "sections": None,
                        "char_count": None,
                        "status": "failed",
                        "extracted_at": datetime.now(timezone.utc),
                        "error_message": str(e)[:500],
                    })
                    await db.commit()
                except Exception:
                    logger.exception("Failed to record error for %s", arxiv_id)
                processed += 1

            await asyncio.sleep(REQUEST_DELAY_SECONDS)

    await db.commit()
    logger.info("Fulltext extraction complete: %d papers processed", processed)
    return processed
