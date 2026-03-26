#!/usr/bin/env python3
"""Genera feed.xml (Atom) con los últimos 50 papers de TechVigilance."""

import argparse
import csv
import io
import json
import os
import re
import sys
from datetime import datetime, timezone
from html import escape
from typing import Optional
from xml.etree import ElementTree as ET


# ─── CSV parsing ─────────────────────────────────────────────────────────────

EXPECTED_COLS = [
    "paperrank", "title", "authors", "year", "domain", "access",
    "abstractmini", "whyrelevant", "primaryurl", "doi", "owner",
    "dateadded", "globalscore", "internalscore", "combinedscore",
    "tagmatches", "matchedtags",
]


def parse_csv(text: str) -> list[dict]:
    """Parse CSV text into a list of dicts with lowercased keys."""
    reader = csv.DictReader(io.StringIO(text))
    rows = []
    for row in reader:
        normalized = {k.strip().lower().replace(" ", "").replace("_", ""): v.strip()
                      for k, v in row.items() if k}
        rows.append(normalized)
    return rows


def safe_float(value: str, default: float = 0.0) -> float:
    try:
        return float(value) if value else default
    except (ValueError, TypeError):
        return default


def parse_date(s: str) -> Optional[datetime]:
    """Parse DD/MM/YYYY HH:MM format. Returns UTC-aware datetime or None."""
    if not s:
        return None
    # Try DD/MM/YYYY HH:MM
    m = re.match(r"(\d{2})/(\d{2})/(\d{4})\s+(\d{2}):(\d{2})", s.strip())
    if m:
        try:
            return datetime(
                int(m.group(3)), int(m.group(2)), int(m.group(1)),
                int(m.group(4)), int(m.group(5)),
                tzinfo=timezone.utc,
            )
        except ValueError:
            pass
    # Try ISO-like fallback
    for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%dT%H:%M", "%d/%m/%Y"):
        try:
            dt = datetime.strptime(s.strip(), fmt)
            return dt.replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


def parse_access(value: str) -> str:
    """Parse access field — may be JSON array like ["OPEN"]."""
    if not value:
        return "UNKNOWN"
    stripped = value.strip()
    if stripped.startswith("["):
        try:
            arr = json.loads(stripped)
            if arr:
                return str(arr[0]).upper()
        except (json.JSONDecodeError, IndexError):
            pass
    return stripped.upper()


def parse_domains(value: str) -> list[str]:
    """Domain field can be semicolon-separated or a plain string."""
    if not value:
        return []
    return [d.strip() for d in value.split(";") if d.strip()]


def parse_matched_tags(value: str) -> list[str]:
    if not value:
        return []
    try:
        arr = json.loads(value)
        if isinstance(arr, list):
            return [str(t) for t in arr]
    except (json.JSONDecodeError, TypeError):
        pass
    # Fallback: comma-separated plain text
    return [t.strip() for t in value.split(",") if t.strip()]


def normalize_papers(rows: list[dict]) -> list[dict]:
    """Normalize raw CSV dicts into paper objects."""
    papers = []
    for r in rows:
        rank = r.get("paperrank", "").strip()
        title = r.get("title", "").strip()
        if not title:
            continue

        date_raw = r.get("dateadded", "").strip()
        parsed_date = parse_date(date_raw)

        domains = parse_domains(r.get("domain", ""))
        owners = [o.strip() for o in r.get("owner", "").split(";") if o.strip()]

        paper = {
            "rank": rank,
            "title": title,
            "authors": r.get("authors", "").strip(),
            "year": r.get("year", "").strip(),
            "domains": domains,
            "access": parse_access(r.get("access", "")),
            "abstract": r.get("abstractmini", "").strip(),
            "why_relevant": r.get("whyrelevant", "").strip(),
            "primary_url": r.get("primaryurl", "").strip(),
            "doi": r.get("doi", "").strip(),
            "owner": r.get("owner", "").strip(),
            "owners_list": owners,
            "date_raw": date_raw,
            "date": parsed_date,
            "global_score": safe_float(r.get("globalscore", "0")),
            "internal_score": safe_float(r.get("internalscore", "0")),
            "combined_score": safe_float(r.get("combinedscore", "0")),
            "tag_matches": r.get("tagmatches", "").strip(),
            "matched_tags": parse_matched_tags(r.get("matchedtags", "")),
        }
        papers.append(paper)
    return papers


# ─── Atom feed generation ─────────────────────────────────────────────────────

ATOM_NS = "http://www.w3.org/2005/Atom"


def atom_tag(name: str) -> str:
    return f"{{{ATOM_NS}}}{name}"


def build_entry_id(paper: dict, base_url: str) -> str:
    """Build a stable, unique Atom entry ID."""
    if paper["doi"]:
        return f"doi:{paper['doi']}"
    if paper["primary_url"]:
        return paper["primary_url"]
    # Fallback: tag URI based on rank
    rank = paper["rank"] or "unknown"
    return f"{base_url.rstrip('/')}/#paper-{rank}"


def build_entry_link(paper: dict, base_url: str) -> str:
    """Return the best URL for linking to this paper."""
    if paper["primary_url"]:
        return paper["primary_url"]
    if paper["doi"]:
        return f"https://doi.org/{paper['doi']}"
    return base_url.rstrip("/") + "/"


def build_summary(paper: dict) -> str:
    """Build a plain-text summary combining abstract, why-relevant, and scores."""
    parts = []
    if paper["abstract"]:
        parts.append(paper["abstract"])
    if paper["why_relevant"]:
        parts.append(f"¿Por qué es relevante? {paper['why_relevant']}")
    score_parts = []
    if paper["global_score"]:
        score_parts.append(f"Global: {paper['global_score']:.1f}")
    if paper["internal_score"]:
        score_parts.append(f"Internal: {paper['internal_score']:.1f}")
    if paper["combined_score"]:
        score_parts.append(f"Combined: {paper['combined_score']:.1f}")
    if score_parts:
        parts.append("Scores — " + " · ".join(score_parts))
    if paper["matched_tags"]:
        parts.append("Tags: " + ", ".join(paper["matched_tags"]))
    return "\n\n".join(parts) if parts else "(Sin resumen)"


def format_atom_date(dt: Optional[datetime]) -> str:
    if dt is None:
        return datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def generate_atom(papers: list[dict], base_url: str, top_n: int = 50) -> str:
    """Generate a complete Atom 1.0 feed XML string."""
    # Sort by date descending, papers without date go last
    def sort_key(p):
        d = p["date"]
        if d is None:
            return datetime.min.replace(tzinfo=timezone.utc)
        return d

    sorted_papers = sorted(papers, key=sort_key, reverse=True)
    entries = sorted_papers[:top_n]

    # Feed updated = most recent entry date (or now if no entries)
    if entries and entries[0]["date"]:
        feed_updated = entries[0]["date"]
    else:
        feed_updated = datetime.now(tz=timezone.utc)

    # Build XML using ElementTree
    ET.register_namespace("", ATOM_NS)

    feed_el = ET.Element(atom_tag("feed"))
    feed_el.set("xml:lang", "es")

    # Feed title
    title_el = ET.SubElement(feed_el, atom_tag("title"))
    title_el.text = "TechVigilance — Últimos papers"

    # Feed subtitle
    subtitle_el = ET.SubElement(feed_el, atom_tag("subtitle"))
    subtitle_el.text = "Biblioteca de vigilancia tecnológica para I+D"

    # Feed link (self)
    link_self = ET.SubElement(feed_el, atom_tag("link"))
    link_self.set("href", base_url.rstrip("/") + "/feed.xml")
    link_self.set("rel", "self")
    link_self.set("type", "application/atom+xml")

    # Feed link (alternate)
    link_alt = ET.SubElement(feed_el, atom_tag("link"))
    link_alt.set("href", base_url.rstrip("/") + "/")
    link_alt.set("rel", "alternate")
    link_alt.set("type", "text/html")

    # Feed id
    feed_id_el = ET.SubElement(feed_el, atom_tag("id"))
    feed_id_el.text = base_url.rstrip("/") + "/feed.xml"

    # Feed updated
    updated_el = ET.SubElement(feed_el, atom_tag("updated"))
    updated_el.text = format_atom_date(feed_updated)

    # Feed author
    author_el = ET.SubElement(feed_el, atom_tag("author"))
    author_name_el = ET.SubElement(author_el, atom_tag("name"))
    author_name_el.text = "TechVigilance"
    author_uri_el = ET.SubElement(author_el, atom_tag("uri"))
    author_uri_el.text = base_url.rstrip("/") + "/"

    # Feed generator
    gen_el = ET.SubElement(feed_el, atom_tag("generator"))
    gen_el.set("uri", "https://github.com/javieraldea/papers")
    gen_el.set("version", "2.0")
    gen_el.text = "TechVigilance generate_feed.py"

    # Entries
    for paper in entries:
        entry_el = ET.SubElement(feed_el, atom_tag("entry"))

        # Entry title
        e_title = ET.SubElement(entry_el, atom_tag("title"))
        e_title.set("type", "text")
        e_title.text = paper["title"]

        # Entry link
        e_link = ET.SubElement(entry_el, atom_tag("link"))
        e_link.set("href", build_entry_link(paper, base_url))
        e_link.set("rel", "alternate")
        e_link.set("type", "text/html")

        # Entry id
        e_id = ET.SubElement(entry_el, atom_tag("id"))
        e_id.text = build_entry_id(paper, base_url)

        # Entry updated (use date or feed_updated as fallback)
        e_updated = ET.SubElement(entry_el, atom_tag("updated"))
        e_updated.text = format_atom_date(paper["date"])

        # Entry published (same as updated since we only have one date)
        e_published = ET.SubElement(entry_el, atom_tag("published"))
        e_published.text = format_atom_date(paper["date"])

        # Entry authors (per-paper)
        if paper["authors"]:
            # May be semicolon or comma-separated
            author_names = [a.strip() for a in re.split(r"[;,]", paper["authors"]) if a.strip()]
            # Limit to first 5 for feed size
            for aname in author_names[:5]:
                ea = ET.SubElement(entry_el, atom_tag("author"))
                ean = ET.SubElement(ea, atom_tag("name"))
                ean.text = aname
            if len(author_names) > 5:
                # Note remaining
                ea = ET.SubElement(entry_el, atom_tag("author"))
                ean = ET.SubElement(ea, atom_tag("name"))
                ean.text = f"… y {len(author_names) - 5} más"
        else:
            ea = ET.SubElement(entry_el, atom_tag("author"))
            ean = ET.SubElement(ea, atom_tag("name"))
            ean.text = "Autor desconocido"

        # Entry category (first domain)
        if paper["domains"]:
            e_cat = ET.SubElement(entry_el, atom_tag("category"))
            e_cat.set("term", paper["domains"][0])
            e_cat.set("label", paper["domains"][0])

        # Additional domains as extra categories
        for domain in paper["domains"][1:]:
            e_cat2 = ET.SubElement(entry_el, atom_tag("category"))
            e_cat2.set("term", domain)
            e_cat2.set("label", domain)

        # Entry summary
        e_summary = ET.SubElement(entry_el, atom_tag("summary"))
        e_summary.set("type", "text")
        e_summary.text = build_summary(paper)

        # Entry content (HTML-enriched version)
        e_content = ET.SubElement(entry_el, atom_tag("content"))
        e_content.set("type", "html")
        content_parts = []
        if paper["year"]:
            content_parts.append(f"<p><strong>Año:</strong> {escape(paper['year'])}</p>")
        if paper["authors"]:
            content_parts.append(f"<p><strong>Autores:</strong> {escape(paper['authors'])}</p>")
        if paper["domains"]:
            content_parts.append(f"<p><strong>Dominio(s):</strong> {escape(', '.join(paper['domains']))}</p>")
        content_parts.append(
            f"<p><strong>Scores:</strong> Global {paper['global_score']:.1f} · "
            f"Internal {paper['internal_score']:.1f} · Combined {paper['combined_score']:.1f}</p>"
        )
        if paper["abstract"]:
            content_parts.append(f"<p><strong>Resumen:</strong> {escape(paper['abstract'])}</p>")
        if paper["why_relevant"]:
            content_parts.append(f"<blockquote><strong>¿Por qué es relevante?</strong> {escape(paper['why_relevant'])}</blockquote>")
        if paper["doi"]:
            doi_url = f"https://doi.org/{paper['doi']}"
            content_parts.append(f"<p><strong>DOI:</strong> <a href=\"{escape(doi_url)}\">{escape(paper['doi'])}</a></p>")
        if paper["matched_tags"]:
            content_parts.append(f"<p><strong>Tags:</strong> {escape(', '.join(paper['matched_tags']))}</p>")
        if paper["primary_url"]:
            content_parts.append(f"<p><a href=\"{escape(paper['primary_url'])}\">Acceder al paper →</a></p>")
        e_content.text = "\n".join(content_parts)

    # Serialize with declaration
    tree = ET.ElementTree(feed_el)
    ET.indent(tree, space="  ")

    buf = io.BytesIO()
    tree.write(buf, encoding="utf-8", xml_declaration=True)
    xml_bytes = buf.getvalue()

    return xml_bytes.decode("utf-8")


# ─── CLI ─────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Genera feed.xml (Atom) con los últimos 50 papers de TechVigilance.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Ejemplos:\n"
            "  python3 generate_feed.py\n"
            "  python3 generate_feed.py --csv data/papers.csv --out dist/feed.xml\n"
            "  python3 generate_feed.py --base-url https://example.github.io/papers/ --top 30\n"
        ),
    )
    parser.add_argument(
        "--csv",
        default="papers.csv",
        metavar="FILE",
        help="Ruta al CSV de papers (default: papers.csv)",
    )
    parser.add_argument(
        "--out",
        default="feed.xml",
        metavar="FILE",
        help="Ruta de salida para el feed Atom (default: feed.xml)",
    )
    parser.add_argument(
        "--base-url",
        default="https://javieraldea.github.io/papers/",
        metavar="URL",
        help="URL base del sitio (default: https://javieraldea.github.io/papers/)",
    )
    parser.add_argument(
        "--top",
        type=int,
        default=50,
        metavar="N",
        help="Número máximo de entradas en el feed (default: 50)",
    )
    args = parser.parse_args()

    # Validate CSV path
    csv_path = args.csv
    if not os.path.isfile(csv_path):
        print(f"\n  ERROR: No se encontró el archivo CSV: {csv_path!r}\n", file=sys.stderr)
        sys.exit(1)

    if args.top < 1:
        print("\n  ERROR: --top debe ser un entero positivo.\n", file=sys.stderr)
        sys.exit(1)

    base_url = args.base_url
    if not base_url.startswith("http"):
        print(f"\n  AVISO: --base-url no parece una URL válida: {base_url!r}\n", file=sys.stderr)

    # Read CSV
    print(f"[feed] Leyendo {csv_path!r} …")
    try:
        with open(csv_path, "r", encoding="utf-8-sig") as fh:
            csv_text = fh.read()
    except OSError as exc:
        print(f"\n  ERROR al leer el CSV: {exc}\n", file=sys.stderr)
        sys.exit(1)

    # Parse & normalize
    rows = parse_csv(csv_text)
    papers = normalize_papers(rows)

    total = len(papers)
    with_date = sum(1 for p in papers if p["date"] is not None)
    without_date = total - with_date

    print(f"[feed] {total} papers encontrados ({with_date} con fecha, {without_date} sin fecha).")

    if total == 0:
        print("[feed] No hay papers. El feed estará vacío.", file=sys.stderr)

    # Generate feed
    print(f"[feed] Generando feed Atom con los {min(args.top, total)} papers más recientes …")
    xml_str = generate_atom(papers, base_url=base_url, top_n=args.top)

    # Write output
    out_path = args.out
    try:
        with open(out_path, "w", encoding="utf-8") as fh:
            fh.write(xml_str)
    except OSError as exc:
        print(f"\n  ERROR al escribir {out_path!r}: {exc}\n", file=sys.stderr)
        sys.exit(1)

    # Summary
    entry_count = min(args.top, total)
    newest = None
    for p in sorted(papers, key=lambda x: x["date"] or datetime.min.replace(tzinfo=timezone.utc), reverse=True):
        if p["date"]:
            newest = p
            break

    print()
    print("=" * 56)
    print("  Feed generado correctamente")
    print("=" * 56)
    print(f"  Archivo de salida : {out_path}")
    print(f"  Entradas en feed  : {entry_count} de {total} papers")
    print(f"  Base URL          : {base_url}")
    if newest:
        print(f"  Paper más reciente: {newest['title'][:45]}…")
        print(f"  Fecha más reciente: {format_atom_date(newest['date'])}")
    print(f"  Sin fecha         : {without_date} papers (al final del feed)")
    print("=" * 56)
    print()


if __name__ == "__main__":
    main()
