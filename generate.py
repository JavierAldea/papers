#!/usr/bin/env python3
"""
Genera un index.html moderno a partir de un CSV de papers académicos.

Uso:
    python generate.py papers.csv
    python generate.py papers.csv --out index.html

Columnas esperadas en el CSV (en cualquier orden, mayúsculas/minúsculas ignoradas):
    title     -> título del paper
    authors   -> autores (separados por coma o punto y coma)
    abstract  -> resumen corto
    link      -> URL del paper (doi, arxiv, etc.)

Si tus columnas tienen nombres distintos, edita COLUMN_MAP abajo.
"""

import csv
import sys
import html
import json
import argparse
from pathlib import Path

# --- Mapeo de nombres de columna (minúsculas) a campos internos ---
# Si tu CSV tiene nombres distintos, cámbialos aquí.
# Ejemplo: si tu columna se llama "URL" en vez de "link", pon "url": "link"
COLUMN_MAP = {
    "title":    "title",
    "titulo":   "title",
    "authors":  "authors",
    "autores":  "authors",
    "author":   "authors",
    "abstract": "abstract",
    "resumen":  "abstract",
    "summary":  "abstract",
    "link":     "link",
    "url":      "link",
    "doi":      "link",
}

def load_csv(path: str) -> list[dict]:
    papers = []
    with open(path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            paper = {"title": "", "authors": "", "abstract": "", "link": ""}
            for col, value in row.items():
                mapped = COLUMN_MAP.get(col.strip().lower())
                if mapped:
                    paper[mapped] = value.strip()
            if paper["title"]:
                papers.append(paper)
    return papers


def generate_html(papers: list[dict], output: str):
    papers_json = json.dumps(papers, ensure_ascii=False, indent=2)

    html_content = f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Papers</title>
<style>
  :root {{
    --bg: #0f1117;
    --surface: #1a1d27;
    --surface2: #22263a;
    --accent: #6366f1;
    --accent2: #818cf8;
    --text: #e2e8f0;
    --muted: #94a3b8;
    --border: #2d3148;
    --radius: 12px;
    --shadow: 0 4px 24px rgba(0,0,0,0.4);
  }}

  * {{ box-sizing: border-box; margin: 0; padding: 0; }}

  body {{
    background: var(--bg);
    color: var(--text);
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif;
    min-height: 100vh;
  }}

  header {{
    background: linear-gradient(135deg, #1e1b4b 0%, #0f172a 100%);
    border-bottom: 1px solid var(--border);
    padding: 48px 24px 32px;
    text-align: center;
  }}

  header h1 {{
    font-size: 2.2rem;
    font-weight: 700;
    background: linear-gradient(135deg, #a5b4fc, #818cf8);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    margin-bottom: 8px;
  }}

  header p {{
    color: var(--muted);
    font-size: 0.95rem;
  }}

  #counter {{
    display: inline-block;
    background: var(--accent);
    color: white;
    font-size: 0.75rem;
    font-weight: 600;
    padding: 2px 10px;
    border-radius: 99px;
    margin-left: 8px;
    vertical-align: middle;
  }}

  .controls {{
    max-width: 900px;
    margin: 28px auto 0;
    padding: 0 24px;
    display: flex;
    gap: 12px;
    flex-wrap: wrap;
    align-items: center;
  }}

  .search-wrap {{
    flex: 1;
    min-width: 200px;
    position: relative;
  }}

  .search-wrap svg {{
    position: absolute;
    left: 14px;
    top: 50%;
    transform: translateY(-50%);
    color: var(--muted);
    pointer-events: none;
  }}

  input[type=search] {{
    width: 100%;
    padding: 12px 16px 12px 42px;
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    color: var(--text);
    font-size: 0.95rem;
    outline: none;
    transition: border-color 0.2s;
  }}

  input[type=search]:focus {{
    border-color: var(--accent);
  }}

  input[type=search]::placeholder {{
    color: var(--muted);
  }}

  .sort-select {{
    padding: 12px 16px;
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    color: var(--text);
    font-size: 0.9rem;
    cursor: pointer;
    outline: none;
  }}

  main {{
    max-width: 900px;
    margin: 0 auto;
    padding: 24px;
    display: grid;
    gap: 16px;
  }}

  .card {{
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 22px 24px;
    transition: border-color 0.2s, transform 0.15s, box-shadow 0.2s;
    cursor: default;
  }}

  .card:hover {{
    border-color: var(--accent);
    transform: translateY(-2px);
    box-shadow: var(--shadow);
  }}

  .card-top {{
    display: flex;
    align-items: flex-start;
    gap: 16px;
  }}

  .card-num {{
    min-width: 32px;
    height: 32px;
    background: var(--surface2);
    border-radius: 8px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 0.75rem;
    font-weight: 700;
    color: var(--accent2);
    margin-top: 2px;
  }}

  .card-body {{ flex: 1; }}

  .card-title {{
    font-size: 1.05rem;
    font-weight: 600;
    color: var(--text);
    line-height: 1.4;
    margin-bottom: 6px;
  }}

  .card-authors {{
    font-size: 0.82rem;
    color: var(--accent2);
    margin-bottom: 10px;
    font-style: italic;
  }}

  .card-abstract {{
    font-size: 0.88rem;
    color: var(--muted);
    line-height: 1.6;
    display: -webkit-box;
    -webkit-line-clamp: 3;
    -webkit-box-orient: vertical;
    overflow: hidden;
    transition: all 0.3s;
  }}

  .card-abstract.expanded {{
    -webkit-line-clamp: unset;
  }}

  .card-footer {{
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-top: 14px;
    flex-wrap: wrap;
    gap: 8px;
  }}

  .btn-expand {{
    background: none;
    border: none;
    color: var(--muted);
    font-size: 0.8rem;
    cursor: pointer;
    padding: 0;
    transition: color 0.2s;
  }}

  .btn-expand:hover {{ color: var(--accent2); }}

  .btn-link {{
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 7px 14px;
    background: var(--accent);
    color: white;
    text-decoration: none;
    border-radius: 8px;
    font-size: 0.82rem;
    font-weight: 600;
    transition: background 0.2s, transform 0.1s;
  }}

  .btn-link:hover {{
    background: var(--accent2);
    transform: translateY(-1px);
  }}

  .no-results {{
    text-align: center;
    color: var(--muted);
    padding: 64px 0;
    font-size: 1rem;
  }}

  .highlight {{ background: rgba(99,102,241,0.3); border-radius: 3px; padding: 0 2px; }}

  @media (max-width: 600px) {{
    header h1 {{ font-size: 1.6rem; }}
    .card {{ padding: 16px; }}
  }}
</style>
</head>
<body>

<header>
  <h1>Papers <span id="counter"></span></h1>
  <p>Lista de papers académicos</p>
</header>

<div class="controls">
  <div class="search-wrap">
    <svg width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
      <circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/>
    </svg>
    <input type="search" id="searchInput" placeholder="Buscar por título, autores o abstract…" autofocus>
  </div>
  <select class="sort-select" id="sortSelect">
    <option value="default">Orden original</option>
    <option value="title">A–Z por título</option>
  </select>
</div>

<main id="grid"></main>

<script>
const PAPERS = {papers_json};

let query = "";
let sortMode = "default";

function escape(str) {{
  return str.replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;");
}}

function highlight(text, q) {{
  if (!q) return escape(text);
  const re = new RegExp("(" + q.replace(/[.*+?^${{}}()|[\\]\\\\]/g,"\\\\$&") + ")", "gi");
  return escape(text).replace(re, '<mark class="highlight">$1</mark>');
}}

function render() {{
  const grid = document.getElementById("grid");
  const q = query.toLowerCase().trim();

  let papers = [...PAPERS];

  if (q) {{
    papers = papers.filter(p =>
      p.title.toLowerCase().includes(q) ||
      p.authors.toLowerCase().includes(q) ||
      p.abstract.toLowerCase().includes(q)
    );
  }}

  if (sortMode === "title") {{
    papers.sort((a, b) => a.title.localeCompare(b.title));
  }}

  document.getElementById("counter").textContent = papers.length;

  if (papers.length === 0) {{
    grid.innerHTML = '<div class="no-results">No se encontraron papers para esa búsqueda.</div>';
    return;
  }}

  grid.innerHTML = papers.map((p, i) => `
    <article class="card">
      <div class="card-top">
        <div class="card-num">${{i + 1}}</div>
        <div class="card-body">
          <div class="card-title">${{highlight(p.title, q)}}</div>
          ${{p.authors ? `<div class="card-authors">${{highlight(p.authors, q)}}</div>` : ""}}
          ${{p.abstract ? `<div class="card-abstract" id="abs-${{i}}">${{highlight(p.abstract, q)}}</div>` : ""}}
        </div>
      </div>
      <div class="card-footer">
        ${{p.abstract && p.abstract.length > 200
          ? `<button class="btn-expand" onclick="toggleAbstract(${{i}}, this)">Ver más ▾</button>`
          : '<span></span>'
        }}
        ${{p.link
          ? `<a class="btn-link" href="${{escape(p.link)}}" target="_blank" rel="noopener">
               Ver paper
               <svg width="12" height="12" fill="none" stroke="currentColor" stroke-width="2.5" viewBox="0 0 24 24">
                 <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/>
                 <polyline points="15 3 21 3 21 9"/><line x1="10" y1="14" x2="21" y2="3"/>
               </svg>
             </a>`
          : ""
        }}
      </div>
    </article>
  `).join("");
}}

function toggleAbstract(i, btn) {{
  const el = document.getElementById("abs-" + i);
  const expanded = el.classList.toggle("expanded");
  btn.textContent = expanded ? "Ver menos ▴" : "Ver más ▾";
}}

document.getElementById("searchInput").addEventListener("input", e => {{
  query = e.target.value;
  render();
}});

document.getElementById("sortSelect").addEventListener("change", e => {{
  sortMode = e.target.value;
  render();
}});

render();
</script>
</body>
</html>
"""

    Path(output).write_text(html_content, encoding="utf-8")
    print(f"✓ Generado: {output}  ({len(papers)} papers)")


def main():
    parser = argparse.ArgumentParser(description="Genera una web moderna desde un CSV de papers.")
    parser.add_argument("csv", help="Ruta al archivo CSV")
    parser.add_argument("--out", default="index.html", help="Archivo HTML de salida (default: index.html)")
    args = parser.parse_args()

    if not Path(args.csv).exists():
        print(f"Error: no encuentro el archivo '{args.csv}'")
        sys.exit(1)

    papers = load_csv(args.csv)
    if not papers:
        print("Error: el CSV está vacío o no tiene columnas reconocibles.")
        print("Columnas soportadas:", list(COLUMN_MAP.keys()))
        sys.exit(1)

    generate_html(papers, args.out)


if __name__ == "__main__":
    main()
