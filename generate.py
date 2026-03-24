#!/usr/bin/env python3
"""
Genera un index.html estilo SharePoint a partir del CSV de TechVigilance.

Uso:
    python generate.py TechVigilance-6.csv
    python generate.py TechVigilance-6.csv --out index.html --title "TechVigilance"
"""

import csv
import sys
import json
import argparse
import re
from pathlib import Path


def clean(text: str) -> str:
    """Limpia texto: elimina comillas sobrantes y espacios."""
    return text.strip().strip('"').strip()


def parse_list_field(value: str) -> list[str]:
    """Convierte '["Brewing & Process","Biotech"]' en una lista Python."""
    value = value.strip()
    if not value:
        return []
    try:
        result = json.loads(value)
        if isinstance(result, list):
            return [str(x).strip() for x in result if str(x).strip()]
    except Exception:
        pass
    # Fallback: quitar corchetes y separar por coma
    value = re.sub(r'[\[\]"]', '', value)
    return [x.strip() for x in value.split(',') if x.strip()]


def load_csv(path: str) -> list[dict]:
    papers = []
    encodings = ["utf-8-sig", "utf-8", "latin-1", "cp1252"]
    rows = None

    for enc in encodings:
        try:
            with open(path, newline="", encoding=enc) as f:
                reader = csv.DictReader(f)
                rows = list(reader)
            break
        except (UnicodeDecodeError, Exception):
            continue

    if rows is None:
        print("Error: no se pudo leer el CSV con ninguna codificación soportada.")
        sys.exit(1)

    for row in rows:
        # Normalizar nombres de columna (sin espacios, minúsculas)
        norm = {k.strip().lower().replace(" ", ""): v.strip() for k, v in row.items()}

        def get(*keys):
            for k in keys:
                v = norm.get(k, "")
                if v:
                    return clean(v)
            return ""

        domains = parse_list_field(get("domain"))
        access_raw = parse_list_field(get("access"))
        access = access_raw[0] if access_raw else ""

        paper = {
            "title":       get("title", "titulo"),
            "authors":     get("authors", "autores", "author"),
            "abstract":    get("abstractmini", "abstract", "resumen"),
            "why":         get("whyrelevant", "relevance"),
            "link":        get("primaryurl", "url", "link", "doi_url"),
            "doi":         get("doi"),
            "year":        get("year", "año"),
            "rank":        get("paperrank", "rank"),
            "domains":     domains,
            "access":      access.upper(),
            "owner":       get("owner"),
            "date":        get("dateadded", "date"),
        }

        if paper["title"]:
            papers.append(paper)

    # Ordenar por rank descendente (mayor rank = más relevante)
    papers.sort(key=lambda p: int(p["rank"]) if p["rank"].isdigit() else 0, reverse=True)
    return papers


def all_domains(papers: list[dict]) -> list[str]:
    seen = set()
    result = []
    for p in papers:
        for d in p["domains"]:
            if d not in seen:
                seen.add(d)
                result.append(d)
    return sorted(result)


def generate_html(papers: list[dict], output: str, title: str):
    papers_json = json.dumps(papers, ensure_ascii=False, indent=2)
    domains = all_domains(papers)
    domains_json = json.dumps(domains, ensure_ascii=False)

    html_content = f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title>
<style>
  :root {{
    --ms-blue:    #0078d4;
    --ms-blue-dk: #005a9e;
    --ms-blue-lt: #c7e0f4;
    --ms-bg:      #f3f2f1;
    --ms-white:   #ffffff;
    --ms-gray1:   #faf9f8;
    --ms-gray2:   #edebe9;
    --ms-gray3:   #d2d0ce;
    --ms-gray4:   #a19f9d;
    --ms-gray5:   #605e5c;
    --ms-text:    #323130;
    --ms-muted:   #605e5c;
    --ms-green:   #107c10;
    --ms-orange:  #d83b01;
    --radius:     4px;
    --shadow:     0 1.6px 3.6px rgba(0,0,0,.13), 0 0.3px 0.9px rgba(0,0,0,.11);
    --shadow-hov: 0 6px 20px rgba(0,0,0,.15);
  }}

  * {{ box-sizing: border-box; margin: 0; padding: 0; }}

  body {{
    background: var(--ms-bg);
    color: var(--ms-text);
    font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, Roboto, sans-serif;
    font-size: 14px;
    min-height: 100vh;
  }}

  /* ── TOPBAR ── */
  .topbar {{
    background: var(--ms-blue);
    height: 48px;
    display: flex;
    align-items: center;
    padding: 0 16px;
    gap: 12px;
    color: white;
  }}
  .topbar-icon {{ opacity: .9; }}
  .topbar h1 {{ font-size: 15px; font-weight: 600; letter-spacing: .01em; }}
  .topbar-count {{
    margin-left: auto;
    background: rgba(255,255,255,.2);
    border-radius: 12px;
    padding: 2px 10px;
    font-size: 12px;
    font-weight: 600;
  }}

  /* ── COMMAND BAR ── */
  .commandbar {{
    background: var(--ms-white);
    border-bottom: 1px solid var(--ms-gray3);
    padding: 8px 20px;
    display: flex;
    align-items: center;
    gap: 8px;
    flex-wrap: wrap;
    box-shadow: var(--shadow);
  }}

  .search-box {{
    display: flex;
    align-items: center;
    border: 1px solid var(--ms-gray3);
    border-radius: var(--radius);
    background: var(--ms-white);
    padding: 0 10px;
    gap: 6px;
    height: 32px;
    flex: 1;
    min-width: 200px;
    max-width: 360px;
    transition: border-color .15s;
  }}
  .search-box:focus-within {{ border-color: var(--ms-blue); box-shadow: 0 0 0 1px var(--ms-blue); }}
  .search-box input {{
    border: none; outline: none; background: transparent;
    font: inherit; color: var(--ms-text); width: 100%; font-size: 13px;
  }}
  .search-box svg {{ color: var(--ms-gray4); flex-shrink: 0; }}

  .ms-btn {{
    height: 32px;
    padding: 0 12px;
    border-radius: var(--radius);
    border: 1px solid var(--ms-gray3);
    background: var(--ms-white);
    color: var(--ms-text);
    font: inherit;
    font-size: 13px;
    cursor: pointer;
    display: inline-flex;
    align-items: center;
    gap: 6px;
    white-space: nowrap;
    transition: background .1s, border-color .1s;
  }}
  .ms-btn:hover {{ background: var(--ms-gray2); }}
  .ms-btn.active {{ background: var(--ms-blue-lt); border-color: var(--ms-blue); color: var(--ms-blue-dk); font-weight: 600; }}

  select.ms-select {{
    height: 32px;
    padding: 0 28px 0 10px;
    border: 1px solid var(--ms-gray3);
    border-radius: var(--radius);
    background: var(--ms-white);
    color: var(--ms-text);
    font: inherit;
    font-size: 13px;
    cursor: pointer;
    outline: none;
    appearance: none;
    background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='10' height='6' viewBox='0 0 10 6'%3E%3Cpath fill='%23605e5c' d='M0 0l5 6 5-6z'/%3E%3C/svg%3E");
    background-repeat: no-repeat;
    background-position: right 10px center;
  }}
  select.ms-select:focus {{ border-color: var(--ms-blue); box-shadow: 0 0 0 1px var(--ms-blue); }}

  .sep {{ width: 1px; height: 24px; background: var(--ms-gray3); margin: 0 4px; }}

  /* ── FILTERS PILLS ── */
  .filter-bar {{
    background: var(--ms-gray1);
    border-bottom: 1px solid var(--ms-gray3);
    padding: 6px 20px;
    display: flex;
    gap: 6px;
    flex-wrap: wrap;
    align-items: center;
  }}
  .filter-label {{ font-size: 12px; color: var(--ms-muted); margin-right: 4px; }}

  .pill {{
    height: 26px;
    padding: 0 10px;
    border-radius: 13px;
    border: 1px solid var(--ms-gray3);
    background: var(--ms-white);
    color: var(--ms-muted);
    font: inherit;
    font-size: 12px;
    cursor: pointer;
    white-space: nowrap;
    transition: all .15s;
  }}
  .pill:hover {{ border-color: var(--ms-blue); color: var(--ms-blue); }}
  .pill.active {{
    background: var(--ms-blue);
    border-color: var(--ms-blue);
    color: white;
    font-weight: 600;
  }}

  /* ── MAIN GRID ── */
  main {{
    max-width: 1100px;
    margin: 20px auto;
    padding: 0 20px 40px;
    display: grid;
    gap: 8px;
  }}

  /* ── CARD ── */
  .card {{
    background: var(--ms-white);
    border: 1px solid var(--ms-gray3);
    border-radius: var(--radius);
    padding: 14px 16px;
    transition: box-shadow .15s, border-color .15s;
    position: relative;
  }}
  .card:hover {{
    border-color: var(--ms-blue);
    box-shadow: var(--shadow-hov);
  }}

  .card-row1 {{
    display: flex;
    align-items: flex-start;
    gap: 12px;
  }}

  .rank-badge {{
    min-width: 36px;
    height: 36px;
    border-radius: var(--radius);
    background: var(--ms-blue);
    color: white;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 12px;
    font-weight: 700;
    flex-shrink: 0;
  }}

  .card-main {{ flex: 1; min-width: 0; }}

  .card-title {{
    font-size: 14px;
    font-weight: 600;
    color: var(--ms-blue-dk);
    line-height: 1.4;
    margin-bottom: 4px;
    cursor: pointer;
  }}
  .card-title:hover {{ text-decoration: underline; color: var(--ms-blue); }}

  .card-meta {{
    display: flex;
    flex-wrap: wrap;
    gap: 12px;
    font-size: 12px;
    color: var(--ms-muted);
    margin-bottom: 8px;
    align-items: center;
  }}

  .meta-item {{ display: flex; align-items: center; gap: 4px; }}

  .access-badge {{
    display: inline-block;
    padding: 1px 7px;
    border-radius: 3px;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: .03em;
    text-transform: uppercase;
  }}
  .access-badge.open {{ background: #dff6dd; color: var(--ms-green); }}
  .access-badge.paywall {{ background: #fff4ce; color: #7d5a00; }}

  .domain-tag {{
    display: inline-block;
    padding: 1px 8px;
    border-radius: 3px;
    font-size: 11px;
    background: var(--ms-blue-lt);
    color: var(--ms-blue-dk);
    font-weight: 500;
  }}

  .card-abstract {{
    font-size: 13px;
    color: var(--ms-muted);
    line-height: 1.55;
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
  }}
  .card-abstract.expanded {{ -webkit-line-clamp: unset; }}

  .card-row2 {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-top: 10px;
    flex-wrap: wrap;
    gap: 8px;
  }}

  .card-actions {{ display: flex; gap: 6px; align-items: center; }}

  .btn-toggle {{
    background: none;
    border: none;
    color: var(--ms-blue);
    font: inherit;
    font-size: 12px;
    cursor: pointer;
    padding: 0;
    display: flex;
    align-items: center;
    gap: 4px;
  }}
  .btn-toggle:hover {{ text-decoration: underline; }}

  .btn-open {{
    height: 28px;
    padding: 0 12px;
    background: var(--ms-blue);
    color: white;
    text-decoration: none;
    border-radius: var(--radius);
    font: inherit;
    font-size: 12px;
    font-weight: 600;
    display: inline-flex;
    align-items: center;
    gap: 5px;
    transition: background .15s;
  }}
  .btn-open:hover {{ background: var(--ms-blue-dk); }}

  .owner-chip {{
    font-size: 11px;
    color: var(--ms-gray4);
    background: var(--ms-gray1);
    border: 1px solid var(--ms-gray2);
    border-radius: 3px;
    padding: 1px 7px;
    max-width: 220px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }}

  .why-box {{
    margin-top: 10px;
    padding: 10px 12px;
    background: var(--ms-gray1);
    border-left: 3px solid var(--ms-blue);
    border-radius: 0 var(--radius) var(--radius) 0;
    font-size: 12px;
    color: var(--ms-muted);
    line-height: 1.5;
    display: none;
  }}
  .why-box.visible {{ display: block; }}

  .no-results {{
    text-align: center;
    color: var(--ms-muted);
    padding: 60px 0;
    font-size: 14px;
  }}

  mark {{ background: #fff3cd; border-radius: 2px; padding: 0 1px; }}

  @media(max-width:600px) {{
    .topbar h1 {{ font-size: 13px; }}
    .card {{ padding: 12px; }}
    .rank-badge {{ min-width: 30px; height: 30px; font-size: 11px; }}
  }}
</style>
</head>
<body>

<div class="topbar">
  <svg class="topbar-icon" width="20" height="20" viewBox="0 0 20 20" fill="white">
    <path d="M2 4h16v2H2zm0 5h16v2H2zm0 5h10v2H2z"/>
  </svg>
  <h1>{title}</h1>
  <span class="topbar-count" id="topbar-count"></span>
</div>

<div class="commandbar">
  <div class="search-box">
    <svg width="14" height="14" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
      <circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/>
    </svg>
    <input type="search" id="searchInput" placeholder="Buscar en todos los campos…">
  </div>

  <div class="sep"></div>

  <select class="ms-select" id="sortSelect">
    <option value="rank">Ordenar: Relevancia</option>
    <option value="year">Ordenar: Año</option>
    <option value="title">Ordenar: A–Z</option>
  </select>

  <select class="ms-select" id="accessSelect">
    <option value="">Acceso: Todos</option>
    <option value="OPEN">Solo Open Access</option>
    <option value="PAYWALL">Solo Paywall</option>
  </select>
</div>

<div class="filter-bar" id="filterBar">
  <span class="filter-label">Dominio:</span>
  <button class="pill active" data-domain="">Todos</button>
</div>

<main id="grid"></main>

<script>
const PAPERS  = {papers_json};
const DOMAINS = {domains_json};

let query  = "";
let domain = "";
let sort   = "rank";
let access = "";

// Build domain pills
const bar = document.getElementById("filterBar");
DOMAINS.forEach(d => {{
  const btn = document.createElement("button");
  btn.className = "pill";
  btn.dataset.domain = d;
  btn.textContent = d;
  btn.onclick = () => setDomain(d);
  bar.appendChild(btn);
}});

function setDomain(d) {{
  domain = d;
  bar.querySelectorAll(".pill").forEach(p => p.classList.toggle("active", p.dataset.domain === d));
  render();
}}

function esc(s) {{
  return String(s).replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;");
}}

function hl(text, q) {{
  if (!q || !text) return esc(text);
  const re = new RegExp("(" + q.replace(/[.*+?^${{}}()|[\\]\\\\]/g,"\\\\$&") + ")", "gi");
  return esc(text).replace(re, "<mark>$1</mark>");
}}

function matches(p, q) {{
  if (!q) return true;
  const lq = q.toLowerCase();
  return [p.title, p.authors, p.abstract, p.why, p.owner, ...(p.domains||[])]
    .some(f => f && f.toLowerCase().includes(lq));
}}

function render() {{
  const grid = document.getElementById("grid");
  const q = query.trim();

  let list = PAPERS.filter(p =>
    matches(p, q) &&
    (!domain || (p.domains||[]).includes(domain)) &&
    (!access || p.access === access)
  );

  if (sort === "title") list.sort((a,b) => a.title.localeCompare(b.title));
  else if (sort === "year") list.sort((a,b) => (b.year||"").localeCompare(a.year||""));
  else list.sort((a,b) => (parseInt(b.rank)||0) - (parseInt(a.rank)||0));

  document.getElementById("topbar-count").textContent = list.length + " papers";

  if (!list.length) {{
    grid.innerHTML = '<div class="no-results">No hay resultados para esta búsqueda.</div>';
    return;
  }}

  grid.innerHTML = list.map((p, i) => {{
    const domains = (p.domains||[]).map(d => `<span class="domain-tag">${{esc(d)}}</span>`).join(" ");
    const accessClass = p.access === "OPEN" ? "open" : "paywall";
    const accessLabel = p.access === "OPEN" ? "Open" : p.access === "PAYWALL" ? "Paywall" : p.access;

    return `
    <article class="card" id="card-${{i}}">
      <div class="card-row1">
        ${{p.rank ? `<div class="rank-badge">${{esc(p.rank)}}</div>` : ""}}
        <div class="card-main">
          <div class="card-title" onclick="${{p.link ? `window.open('${{esc(p.link)}}','_blank')` : ""}}">${{hl(p.title, q)}}</div>
          <div class="card-meta">
            ${{p.authors ? `<span class="meta-item"><svg width="11" height="11" fill="currentColor" viewBox="0 0 20 20"><path d="M10 10a4 4 0 1 0 0-8 4 4 0 0 0 0 8zm-7 8a7 7 0 0 1 14 0H3z"/></svg>${{hl(p.authors, q)}}</span>` : ""}}
            ${{p.year ? `<span class="meta-item">${{esc(p.year)}}</span>` : ""}}
            ${{accessLabel ? `<span class="access-badge ${{accessClass}}">${{esc(accessLabel)}}</span>` : ""}}
            ${{domains}}
          </div>
          ${{p.abstract ? `<div class="card-abstract" id="abs-${{i}}">${{hl(p.abstract, q)}}</div>` : ""}}
          ${{p.why ? `<div class="why-box" id="why-${{i}}">${{hl(p.why, q)}}</div>` : ""}}
        </div>
      </div>
      <div class="card-row2">
        <div class="card-actions">
          ${{p.abstract && p.abstract.length > 120
            ? `<button class="btn-toggle" onclick="toggleAbs(${{i}}, this)">▾ Ver resumen</button>`
            : '<span></span>'
          }}
          ${{p.why ? `<button class="btn-toggle" onclick="toggleWhy(${{i}}, this)" style="color:#605e5c">💡 ¿Por qué?</button>` : ""}}
        </div>
        <div style="display:flex;gap:8px;align-items:center">
          ${{p.owner ? `<span class="owner-chip" title="${{esc(p.owner)}}">${{esc(p.owner.split(";")[0].trim())}}</span>` : ""}}
          ${{p.link ? `<a class="btn-open" href="${{esc(p.link)}}" target="_blank" rel="noopener">
            Abrir
            <svg width="11" height="11" fill="none" stroke="currentColor" stroke-width="2.5" viewBox="0 0 24 24">
              <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/>
              <polyline points="15 3 21 3 21 9"/><line x1="10" y1="14" x2="21" y2="3"/>
            </svg>
          </a>` : ""}}
        </div>
      </div>
    </article>`;
  }}).join("");
}}

function toggleAbs(i, btn) {{
  const el = document.getElementById("abs-" + i);
  const on = el.classList.toggle("expanded");
  btn.textContent = on ? "▴ Ocultar resumen" : "▾ Ver resumen";
}}

function toggleWhy(i, btn) {{
  const el = document.getElementById("why-" + i);
  const on = el.classList.toggle("visible");
  btn.textContent = on ? "💡 Ocultar" : "💡 ¿Por qué?";
}}

document.getElementById("searchInput").addEventListener("input", e => {{ query = e.target.value; render(); }});
document.getElementById("sortSelect").addEventListener("change", e => {{ sort = e.target.value; render(); }});
document.getElementById("accessSelect").addEventListener("change", e => {{ access = e.target.value; render(); }});

render();
</script>
</body>
</html>
"""

    Path(output).write_text(html_content, encoding="utf-8")
    print(f"✓ Generado: {output}  ({len(papers)} papers)")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("csv", help="Ruta al CSV")
    parser.add_argument("--out",   default="index.html")
    parser.add_argument("--title", default="TechVigilance Papers")
    args = parser.parse_args()

    if not Path(args.csv).exists():
        print(f"Error: no encuentro '{args.csv}'")
        sys.exit(1)

    papers = load_csv(args.csv)
    if not papers:
        print("Error: CSV vacío o sin columnas reconocibles.")
        sys.exit(1)

    generate_html(papers, args.out, args.title)


if __name__ == "__main__":
    main()
