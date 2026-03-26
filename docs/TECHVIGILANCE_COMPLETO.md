# TechVigilance — Documentación Completa

> Última actualización: 2026-03-25
> URL pública: https://javieraldea.github.io/papers/
> Repositorio: https://github.com/JavierAldea/papers

---

## Índice

1. [Qué es esto](#1-qué-es-esto)
2. [Estructura de archivos](#2-estructura-de-archivos)
3. [Cómo funciona la web (index.html)](#3-cómo-funciona-la-web-indexhtml)
4. [El CSV y el pipeline de scoring](#4-el-csv-y-el-pipeline-de-scoring)
5. [Sistema de PDFs para papers PAYWALL](#5-sistema-de-pdfs-para-papers-paywall)
6. [Automatización con watcher.sh](#6-automatización-con-watchersh)
7. [Scripts de utilidad](#7-scripts-de-utilidad)
8. [Código completo — index.html](#8-código-completo--indexhtml)
9. [Código completo — watcher.sh](#9-código-completo--watchersh)
10. [Código completo — build_pdf_index.py](#10-código-completo--build_pdf_indexpy)
11. [Código completo — add_pdf.sh](#11-código-completo--add_pdfsh)
12. [Código completo — generate.py](#12-código-completo--generatepy-script-original-legacy)
13. [Decisiones de arquitectura (ADRs)](#13-decisiones-de-arquitectura-adrs)
14. [Contraseña y autenticación](#14-contraseña-y-autenticación)
15. [Flujos operativos habituales](#15-flujos-operativos-habituales)

---

## 1. Qué es esto

**TechVigilance** es una app web estática que muestra una biblioteca de papers académicos con:

- Búsqueda en tiempo real por título, autores, abstract, etc.
- Filtro por dominio tecnológico (7 dominios)
- Ordenación por tres scores: GlobalScore, InternalScore, CombinedScore
- Vista Lista (tarjetas) + Vista Radar (scatter plot + heatmap)
- Botón de acceso diferenciado: PDF propio (lila) / PAYWALL externo (ámbar) / OPEN (azul)
- Chip de fecha relativa ("hace 3d", "hoy", etc.)
- Tag matches expandibles y clicables para filtrar por dominio
- Protección por contraseña (SHA-256, sin backend)

Está desplegada en **GitHub Pages** — cero backend, cero dependencias, cero build step.

---

## 2. Estructura de archivos

```
papers-page/
├── index.html            ← App web completa (HTML + CSS + JS inline, ~1074 líneas)
├── papers.csv            ← DATOS: papers con scores (17 cols) — generado por score_papers.py
├── papers_raw.csv        ← FUENTE: papers sin scores (12 cols) — se edita manualmente
├── WatchTags.csv         ← FUENTE: 104 antenas de vigilancia con keywords y pesos
├── score_papers.py       ← PIPELINE: lee papers_raw + WatchTags, calcula scores, genera papers.csv
├── watcher.sh            ← AUTO: fswatch → detecta cambios → score → git push
├── watcher.log           ← Log del watcher (en .gitignore)
├── generate.py           ← LEGACY: generador original de HTML desde CSV (ya no se usa)
├── setup_pdfs.sh         ← UTIL: crea carpetas pdfs/{rank}/ para todos los PAYWALL
├── build_pdf_index.py    ← UTIL: escanea pdfs/ y genera pdfs/index.json
├── add_pdf.sh            ← UTIL: copia un PDF + regenera índice + git push (todo en uno)
├── papers.numbers        ← Spreadsheet Numbers con los datos (fuente manual)
├── pdfs/
│   ├── index.json        ← JSON con qué PDFs están disponibles (generado por build_pdf_index.py)
│   ├── 10/
│   │   └── 1-s2.0-S0165572826000184-main.pdf
│   ├── 18/  (carpeta vacía — README.txt de placeholder)
│   ├── 20/  ...
│   ├── 22/  ...
│   ├── 26/  ...
│   ├── 27/  ...
│   ├── 29/  ...
│   ├── 33/  ...
│   ├── 34/  ...
│   └── 35/  ...
└── docs/
    ├── ADR.md            ← Decisiones de arquitectura
    └── TECHVIGILANCE_COMPLETO.md  ← Este archivo
```

**`.gitignore`** — solo excluye:
```
.DS_Store
watcher.log
```
Los PDFs **no** están excluidos; GitHub Pages los sirve directamente.

---

## 3. Cómo funciona la web (index.html)

### Flujo de arranque

```
Usuario abre URL
    → Pantalla de login (password input)
    → sha256(input) se compara con HASH hardcodeado
    → Si correcto: sessionStorage.tv_auth = "1"
    → loadCSV() se ejecuta
        → fetch("pdfs/index.json")  ← en paralelo
        → fetch("papers.csv")
    → normalizePapers() mapea columnas CSV → objetos JS
    → buildDomainPills() crea los filtros de dominio
    → render() pinta las tarjetas
```

### Variables de estado

```js
let PAPERS     = [];   // Array de papers normalizados
let PDF_INDEX  = {};   // { "10": "archivo.pdf", "22": "otro.pdf", ... }
let query      = "";   // Texto de búsqueda actual
let domain     = "";   // Dominio filtrado (vacío = todos)
let sort       = "combined";  // Criterio de ordenación actual
```

### Estructura de un paper normalizado

```js
{
  _id:           0,          // Índice interno
  title:         "...",
  authors:       "...",
  abstract:      "...",      // Campo abstractmini del CSV
  why:           "...",      // Campo whyrelevant del CSV
  link:          "https://...",  // primaryurl del CSV
  doi:           "10.xxx/...",
  year:          "2024",
  rank:          "10",       // PaperRank del CSV
  domains:       ["Brewing & Process", "Biotech applied"],
  access:        "PAYWALL",  // o "OPEN"
  owner:         "Javier",
  date:          "15/03/2026 10:30",
  globalScore:   78.4,
  internalScore: 65.2,
  combinedScore: 71.4,
  tagMatches:    5,
  matchedTags:   [
    { tag: "...", domain: "Brewing & Process", strength: 0.82, phrases: ["malt extract"] }
  ],
  _hasScores:    true,
}
```

### Lógica de botones de acceso

```js
const pdfFile = PDF_INDEX[String(p.rank)];

if (pdfFile) {
  // PDF subido al repo → botón lila "PDF" + botón "web" secundario
  openBtns = `<a class="btn-open btn-pdf" href="pdfs/${rank}/${pdfFile}">PDF</a>`;
  if (href) openBtns += `<a class="btn-open btn-web-small" href="${href}">web</a>`;

} else if (p.access === "PAYWALL" && href) {
  // PAYWALL sin PDF → botón ámbar "🔒 Acceder"
  openBtns = `<a class="btn-open btn-paywall-link" href="${href}">🔒 Acceder</a>`;

} else if (href) {
  // OPEN → botón azul "Abrir ↗"
  openBtns = `<a class="btn-open" href="${href}">Abrir ↗</a>`;
}
```

### Colores de dominio (compartidos por scatter, heatmap y cards)

```js
const DOM_COLORS = {
  'Brewing & Process':         '#f97316',  // naranja
  'Byproducts & Circularity':  '#10b981',  // verde
  'Materials & Packaging':     '#818cf8',  // violeta
  'Water & Environment':       '#38bdf8',  // azul claro
  'Biotech applied':           '#ec4899',  // rosa
  'Analytics & Digital':       '#a78bfa',  // lila
  'Neuroscience & Functional': '#eab308',  // amarillo
};
```

### Scores — colores en barras

| Score         | Color   | Clase CSS          |
|---------------|---------|--------------------|
| GlobalScore   | naranja | `.score-fill.global`   |
| InternalScore | violeta | `.score-fill.internal` |
| CombinedScore | verde   | `.score-fill.combined` |

Las barras tienen **3px de alto** — deliberadamente finas para no dominar visualmente.

### Vista Radar

Toggle en el topbar entre **Lista** y **Radar**. El Radar tiene dos paneles:

- **Scatter plot SVG** (sin D3): eje X = GlobalScore, eje Y = InternalScore, tamaño del punto = CombinedScore, color = dominio. Líneas de mediana dividen en 4 cuadrantes: GOLD / NICHE / WATCH / BACKLOG.
- **Heatmap HTML table**: top 15 papers por CombinedScore × 7 dominios. Intensidad = suma de strengths de tag matches. Click en celda → filtra por dominio y vuelve a lista. Click en título → scroll a la tarjeta.

---

## 4. El CSV y el pipeline de scoring

### Archivos fuente

**`papers_raw.csv`** — 12 columnas, se edita manualmente (o con otra IA):

| Columna      | Descripción                          |
|--------------|--------------------------------------|
| PaperRank    | ID único del paper (número)          |
| Title        | Título del paper                     |
| Authors      | Autores                              |
| Year         | Año de publicación                   |
| AbstractMini | Resumen breve                        |
| WhyRelevant  | Por qué es relevante para nosotros   |
| PrimaryURL   | URL al paper (DOI o directo)         |
| DOI          | DOI si existe                        |
| Domain       | Lista JSON de dominios               |
| Access       | "OPEN" o "PAYWALL"                   |
| Owner        | Persona responsable de seguimiento   |
| DateAdded    | Fecha de incorporación (DD/MM/YYYY HH:MM) |

**`WatchTags.csv`** — 104 antenas de vigilancia. Cada fila es un tema de interés con keywords y pesos. Cruzar papers contra estas antenas da el InternalScore.

**`papers.csv`** — Generado automáticamente por `score_papers.py`. Nunca editar a mano. Añade 5 columnas a papers_raw: `GlobalScore`, `InternalScore`, `CombinedScore`, `TagMatches`, `MatchedTags`.

### Pipeline de scoring (`score_papers.py`)

```
papers_raw.csv  ─┐
                 ├→ score_papers.py → papers.csv (17 cols)
WatchTags.csv  ─┘
```

**GlobalScore (0-100)**: Mide calidad/documentación del paper.
- Recencia: 45%
- Riqueza del abstract: 25%
- Riqueza del WhyRelevant: 18%
- Tiene owner asignado: 12%

**InternalScore (0-100)**: Mide relevancia para nuestros intereses.
- Cruce semántico Title+Abstract+WhyRelevant contra las 104 WatchTags
- Matching por keyword phrases
- Bonus ×1.4 si el Domain del paper coincide con el dominio del WatchTag
- Normalizado 0-100 sobre el rango observado

**CombinedScore**: Media geométrica `sqrt(GlobalScore × InternalScore)`.
- Premia el equilibrio: G=70, I=70 → C=70 (mejor que G=100, I=10 → C=31.6)

---

## 5. Sistema de PDFs para papers PAYWALL

GitHub Pages sirve archivos estáticos directamente. Los PDFs se almacenan en el repo en `pdfs/{PaperRank}/archivo.pdf`.

### Por qué este enfoque

- Google Drive: requiere autenticación, URLs cambiantes
- Carpeta local: solo funciona en el Mac del usuario
- GitHub Pages: gratuito, siempre disponible, sin auth
- Límite: 1 GB por repo, ~25 MB por archivo. Con ~10 papers PAYWALL × ~3 MB = ~30 MB, muy dentro del límite.

### pdfs/index.json

La web no puede listar directorios estáticos, así que `build_pdf_index.py` genera un JSON con qué PDFs existen:

```json
{
  "10": "1-s2.0-S0165572826000184-main.pdf",
  "22": "paper_rank22.pdf"
}
```

La web carga este JSON al arrancar y solo muestra el botón lila "PDF" si el rank del paper aparece en el índice.

### Carpetas PAYWALL actuales

Los papers PAYWALL (ranks con carpeta creada): **10, 18, 20, 22, 26, 27, 29, 33, 34, 35**.

PDF subido hasta ahora: solo rank **10** (`1-s2.0-S0165572826000184-main.pdf`).

---

## 6. Automatización con watcher.sh

`watcher.sh` usa `fswatch` (macOS) para vigilar en tiempo real:
- `papers.csv` → cuando cambia, hace `git add papers.csv && git commit && git push`
- `pdfs/` → cuando detecta un `.pdf` nuevo, regenera `pdfs/index.json` y hace push

**Requiere tener el proceso corriendo en terminal.**

Para iniciarlo:
```bash
bash /Users/nomada/papers-page/watcher.sh
```

Para que arranque automáticamente con el Mac, existe un LaunchAgent en:
`~/Library/LaunchAgents/com.techvigilance.watcher.plist`

### Flujo completo al añadir un PDF

```
1. Copiar PDF a pdfs/10/archivo.pdf  (Finder o terminal)
      ↓ fswatch detecta el cambio
2. watcher.sh ejecuta build_pdf_index.py
      → pdfs/index.json actualizado
3. git add pdfs/ && git commit && git push
      ↓ ~30 segundos
4. GitHub Pages sirve el PDF
5. La web muestra el botón lila "PDF" en el paper 10
```

---

## 7. Scripts de utilidad

### add_pdf.sh — Todo en uno

```bash
bash add_pdf.sh <PaperRank> <ruta_al_pdf>

# Ejemplo:
bash add_pdf.sh 22 ~/Downloads/mi-paper.pdf
```

Hace: copia el PDF a `pdfs/22/`, regenera `index.json`, `git add/commit/push`.

> Si el watcher está corriendo, no hace falta usar `add_pdf.sh` — basta con copiar el PDF a la carpeta y el watcher hace el resto automáticamente.

### build_pdf_index.py — Regenerar índice manualmente

```bash
cd /Users/nomada/papers-page
python3 build_pdf_index.py
```

Escanea todas las subcarpetas de `pdfs/`, toma el primer `.pdf` de cada una, genera `pdfs/index.json`.

### setup_pdfs.sh — Crear carpetas para PAYWALL

Crea las carpetas `pdfs/{rank}/` para todos los papers PAYWALL (con un README.txt de placeholder). Solo se necesita correr una vez.

---

## 8. Código completo — index.html

```html
<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>TechVigilance</title>
<style>
  :root {
    --ms-blue:    #0078d4;
    --ms-blue-dk: #005a9e;
    --ms-blue-lt: #c7e0f4;
    --ms-bg:      #f3f2f1;
    --ms-white:   #ffffff;
    --ms-gray1:   #faf9f8;
    --ms-gray2:   #edebe9;
    --ms-gray3:   #d2d0ce;
    --ms-gray4:   #a19f9d;
    --ms-muted:   #605e5c;
    --ms-text:    #323130;
    --ms-green:   #107c10;
    --radius:     4px;
    --shadow:     0 1.6px 3.6px rgba(0,0,0,.13), 0 0.3px 0.9px rgba(0,0,0,.11);
    --shadow-hov: 0 6px 20px rgba(0,0,0,.15);
  }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    background: #fafbfc;
    color: var(--ms-text);
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    font-size: 14px;
    min-height: 100vh;
  }

  /* TOPBAR */
  .topbar {
    background: var(--ms-blue);
    height: 48px;
    display: flex;
    align-items: center;
    padding: 0 16px;
    gap: 12px;
    color: white;
  }
  .topbar h1 { font-size: 15px; font-weight: 600; }
  .topbar-count {
    background: rgba(255,255,255,.2);
    border-radius: 12px;
    padding: 2px 10px;
    font-size: 12px;
    font-weight: 600;
    white-space: nowrap;
  }
  .view-toggle {
    display: flex;
    gap: 3px;
    background: rgba(255,255,255,.15);
    border-radius: 8px;
    padding: 3px;
    margin-left: auto;
  }
  .view-btn {
    padding: 4px 12px;
    border: none;
    background: none;
    border-radius: 5px;
    cursor: pointer;
    font-size: 12px;
    font-family: inherit;
    color: rgba(255,255,255,.75);
    transition: all .15s;
    white-space: nowrap;
  }
  .view-btn.active {
    background: white;
    color: var(--ms-blue-dk);
    font-weight: 600;
  }

  /* STATS BAR */
  .stats-bar {
    display: flex;
    align-items: center;
    gap: 16px;
    padding: 8px 24px;
    font-size: 13px;
    color: #94a3b8;
    border-bottom: 1px solid #f1f5f9;
    flex-wrap: wrap;
    min-height: 30px;
  }
  .stats-bar .sv { font-weight: 600; color: #334155; }
  .stats-bar .ss { color: #e2e8f0; }

  /* COMMAND BAR */
  .commandbar {
    background: var(--ms-white);
    border-bottom: 1px solid var(--ms-gray3);
    padding: 8px 20px;
    display: flex;
    align-items: center;
    gap: 8px;
    flex-wrap: wrap;
    box-shadow: var(--shadow);
  }
  .search-box {
    display: flex;
    align-items: center;
    border: 1px solid var(--ms-gray3);
    border-radius: var(--radius);
    padding: 0 10px;
    gap: 6px;
    height: 32px;
    flex: 1;
    min-width: 200px;
    max-width: 360px;
    transition: border-color .15s;
  }
  .search-box:focus-within { border-color: var(--ms-blue); box-shadow: 0 0 0 1px var(--ms-blue); }
  .search-box input {
    border: none; outline: none; background: transparent;
    font: inherit; color: var(--ms-text); width: 100%; font-size: 13px;
  }
  .search-box svg { color: var(--ms-gray4); flex-shrink: 0; }
  .sep { width: 1px; height: 24px; background: var(--ms-gray3); margin: 0 4px; }
  select.ms-select {
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
  }
  select.ms-select:focus { border-color: var(--ms-blue); box-shadow: 0 0 0 1px var(--ms-blue); }

  /* DOMAIN PILLS */
  .filter-bar {
    background: var(--ms-gray1);
    border-bottom: 1px solid var(--ms-gray3);
    padding: 6px 20px;
    display: flex;
    gap: 6px;
    flex-wrap: wrap;
    align-items: center;
  }
  .filter-label { font-size: 12px; color: var(--ms-muted); margin-right: 4px; }
  .pill {
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
  }
  .pill:hover { border-color: var(--ms-blue); color: var(--ms-blue); }
  .pill.active { background: var(--ms-blue); border-color: var(--ms-blue); color: white; font-weight: 600; }

  /* CARDS */
  main { margin: 20px 24px 40px; display: grid; gap: 0; }
  .card {
    background: white;
    border: 1px solid #e8ecf0;
    border-radius: 12px;
    padding: 20px 24px;
    margin-bottom: 8px;
    transition: border-color 0.15s ease, box-shadow 0.15s ease;
  }
  .card:hover { border-color: #cbd5e1; box-shadow: 0 2px 8px rgba(0,0,0,0.04); }
  .card-row1 { display: flex; align-items: flex-start; gap: 12px; }
  .rank-badge {
    min-width: 36px; height: 36px;
    border-radius: var(--radius);
    background: var(--ms-blue);
    color: white;
    display: flex; align-items: center; justify-content: center;
    font-size: 12px; font-weight: 700; flex-shrink: 0;
  }
  .card-main { flex: 1; min-width: 0; }
  .card-title {
    font-size: 14px; font-weight: 600;
    color: var(--ms-blue-dk);
    line-height: 1.4; margin-bottom: 4px; cursor: pointer;
  }
  .card-title:hover { text-decoration: underline; color: var(--ms-blue); }
  .card-meta {
    display: flex; flex-wrap: wrap; gap: 12px;
    font-size: 12px; color: var(--ms-muted); margin-bottom: 8px; align-items: center;
  }
  .meta-item { display: flex; align-items: center; gap: 4px; }
  .access-badge {
    display: inline-block; padding: 1px 7px; border-radius: 3px;
    font-size: 11px; font-weight: 700; letter-spacing: .03em; text-transform: uppercase;
  }
  .access-badge.open  { background: #dff6dd; color: var(--ms-green); }
  .access-badge.paywall { background: #fff4ce; color: #7d5a00; }
  .domain-tag {
    display: inline-block; padding: 1px 8px; border-radius: 3px;
    font-size: 11px; background: var(--ms-blue-lt); color: var(--ms-blue-dk); font-weight: 500;
  }
  .card-abstract {
    font-size: 13px; color: var(--ms-muted); line-height: 1.55;
    margin-top: 6px;
  }
  .card-row2 {
    display: flex; justify-content: space-between; align-items: center;
    margin-top: 10px; flex-wrap: wrap; gap: 8px;
  }
  .card-actions { display: flex; gap: 6px; align-items: center; flex-wrap: wrap; }
  .btn-toggle {
    background: none; border: none; color: #64748b;
    font: inherit; font-size: 13px; cursor: pointer; padding: 4px 0;
    transition: color 0.15s ease;
  }
  .btn-toggle:hover { color: #334155; }
  .btn-open {
    height: 28px; padding: 0 12px;
    background: var(--ms-blue); color: white; text-decoration: none;
    border-radius: var(--radius); font: inherit; font-size: 12px; font-weight: 600;
    display: inline-flex; align-items: center; gap: 5px; transition: background .15s;
  }
  .btn-open:hover { background: var(--ms-blue-dk); }
  .btn-pdf { background: #7c3aed; }
  .btn-pdf:hover { background: #6d28d9; }
  .btn-paywall-link { background: #d97706; }
  .btn-paywall-link:hover { background: #b45309; }
  .btn-web-small {
    background: transparent; color: #64748b;
    border: 1px solid #e2e8f0; padding: 0 10px;
    font-size: 12px;
  }
  .btn-web-small:hover { background: #f8fafc; }
  .btn-disabled { background: #f1f5f9; color: #94a3b8; cursor: default; }
  .date-chip {
    display: inline-flex; align-items: center; gap: 2px;
    padding: 1px 7px; border-radius: 8px; font-size: 10px;
    color: #94a3b8; letter-spacing: 0.2px;
    cursor: default; white-space: nowrap;
  }
  .owner-chip {
    font-size: 11px; color: var(--ms-gray4);
    background: var(--ms-gray1); border: 1px solid var(--ms-gray2);
    border-radius: 3px; padding: 1px 7px;
    max-width: 220px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
  }
  .why-box {
    display: none;
    margin-top: 8px; padding: 10px 14px;
    background: #fefce8; border-left: 3px solid #eab308;
    border-radius: 8px;
    font-size: 13px; color: #713f12; line-height: 1.6;
  }
  .why-box.open { display: block; }

  /* SCORE BARS */
  .score-bars { display: flex; flex-direction: column; gap: 6px; margin: 10px 0; }
  .score-row { display: flex; align-items: center; gap: 10px; }
  .score-label {
    width: 14px; font-size: 11px; font-weight: 500; color: #94a3b8;
    text-align: right; flex-shrink: 0;
  }
  .score-track { flex: 1; height: 3px; background: #f1f5f9; border-radius: 2px; overflow: hidden; }
  .score-fill { height: 100%; border-radius: 2px; transition: width 0.5s cubic-bezier(0.4,0,0.2,1); }
  .score-fill.global   { background: #fb923c; }
  .score-fill.internal { background: #818cf8; }
  .score-fill.combined { background: #34d399; }
  .score-value {
    width: 32px; text-align: right; font-size: 11px; font-weight: 500; color: #64748b;
    font-family: ui-monospace, 'SF Mono', monospace; flex-shrink: 0;
  }

  /* TAG MATCHES */
  .btn-tags {
    background: none; border: none; color: #94a3b8;
    font: inherit; font-size: 12px; cursor: pointer; padding: 0;
    transition: color 0.15s ease;
  }
  .btn-tags:hover { color: #64748b; }
  .tag-matches {
    max-height: 0; overflow: hidden;
    transition: max-height 0.3s ease, margin 0.3s ease;
    margin-top: 0;
  }
  .tag-matches.open { max-height: 400px; margin-top: 8px; }
  .tag-match-item {
    display: flex; align-items: center; gap: 8px; flex-wrap: wrap;
    padding: 5px 10px; margin: 2px 0;
    background: #fafbfc; border-radius: 6px;
    font-size: 11px; border-left: 2px solid #e2e8f0;
    cursor: pointer; transition: background 0.15s ease;
  }
  .tag-match-item:hover { background: #f1f5f9; border-left-color: #818cf8; }
  .tag-match-name { font-weight: 500; color: #334155; }
  .tag-match-meta { color: #94a3b8; font-size: 10px; }
  .tag-match-phrases { color: #10b981; font-size: 10px; }

  /* LOADING / EMPTY */
  .state-box {
    text-align: center; color: var(--ms-muted);
    padding: 60px 0; font-size: 14px; grid-column: 1/-1;
  }
  .spinner {
    width: 28px; height: 28px; margin: 0 auto 14px;
    border: 3px solid var(--ms-gray3); border-top-color: var(--ms-blue);
    border-radius: 50%; animation: spin .8s linear infinite;
  }
  @keyframes spin { to { transform: rotate(360deg); } }
  mark { background: #fff3cd; border-radius: 2px; padding: 0 1px; }

  /* RADAR VIEW */
  #radarView { display: none; margin: 20px 24px 40px; padding: 0; gap: 16px; }
  #radarView.active { display: grid; grid-template-columns: 1fr 1fr; }
  .radar-panel {
    background: white; border-radius: 8px;
    border: 1px solid var(--ms-gray3); padding: 20px; box-shadow: var(--shadow);
  }
  .radar-panel h3 {
    font-size: 11px; color: #64748b; text-transform: uppercase;
    letter-spacing: 1px; margin-bottom: 16px; font-weight: 600;
  }
  #scatterContainer  { min-height: 360px; display: flex; align-items: center; justify-content: center; }
  #heatmapContainer  { min-height: 300px; display: flex; align-items: center; justify-content: center; }
  #scatterContainer svg, #heatmapContainer > div { width: 100%; }
  .radar-placeholder { color: #94a3b8; font-size: 13px; text-align: center; line-height: 1.7; padding: 20px; }
  .scatter-dot { cursor: pointer; }
  .scatter-dot:hover { filter: brightness(.8); }
  .heatmap-table { width: 100%; border-collapse: collapse; font-size: 11px; }
  .heatmap-table th {
    padding: 5px 4px; font-weight: 600; font-size: 10px;
    text-align: center; color: #64748b; border-bottom: 1px solid #e2e8f0;
  }
  .heatmap-table td {
    padding: 5px 4px; text-align: center;
    font-family: monospace; font-size: 11px; font-weight: 600;
    transition: background .2s;
  }
  .heatmap-table td:first-child {
    text-align: left; font-family: inherit; font-weight: 400;
    max-width: 160px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
    cursor: pointer; color: var(--ms-blue-dk);
  }
  .heatmap-table td:first-child:hover { text-decoration: underline; }
  .heatmap-table td:not(:first-child):not(:last-child) { cursor: pointer; border-radius: 3px; }
  .heatmap-table tr:hover td { background-color: rgba(0,120,212,.04) !important; }

  /* TOOLTIP */
  #tooltip {
    position: fixed; display: none; z-index: 9999;
    background: #1e293b; color: white;
    padding: 8px 12px; border-radius: 6px;
    font-size: 12px; line-height: 1.5;
    pointer-events: none;
    box-shadow: 0 4px 16px rgba(0,0,0,.3);
    max-width: 240px;
  }

  /* LOGIN */
  #login-screen {
    position: fixed; inset: 0; z-index: 999;
    background: var(--ms-bg);
    display: flex; align-items: center; justify-content: center;
  }
  .login-card {
    background: var(--ms-white); border: 1px solid var(--ms-gray3);
    border-radius: 6px; box-shadow: var(--shadow-hov);
    padding: 40px 36px; width: 100%; max-width: 360px; text-align: center;
  }
  .login-logo {
    width: 48px; height: 48px; background: var(--ms-blue);
    border-radius: 8px; display: flex; align-items: center; justify-content: center;
    margin: 0 auto 20px;
  }
  .login-card h2 { font-size: 18px; font-weight: 600; margin-bottom: 6px; }
  .login-card p  { font-size: 13px; color: var(--ms-muted); margin-bottom: 24px; }
  .login-field {
    width: 100%; height: 36px; padding: 0 12px;
    border: 1px solid var(--ms-gray3); border-radius: var(--radius);
    font: inherit; font-size: 14px; color: var(--ms-text);
    outline: none; margin-bottom: 12px; transition: border-color .15s;
  }
  .login-field:focus { border-color: var(--ms-blue); box-shadow: 0 0 0 1px var(--ms-blue); }
  .login-field.error { border-color: #d13438; box-shadow: 0 0 0 1px #d13438; }
  .login-btn {
    width: 100%; height: 36px;
    background: var(--ms-blue); color: white;
    border: none; border-radius: var(--radius);
    font: inherit; font-size: 14px; font-weight: 600;
    cursor: pointer; transition: background .15s;
  }
  .login-btn:hover { background: var(--ms-blue-dk); }
  .login-error { font-size: 12px; color: #d13438; margin-top: 10px; display: none; }

  @media(max-width:900px) {
    #radarView.active { grid-template-columns: 1fr; }
  }
  @media(max-width:600px) {
    .topbar h1 { font-size: 13px; }
    .card { padding: 12px; }
    .rank-badge { min-width: 30px; height: 30px; font-size: 11px; }
    .view-btn { padding: 4px 8px; font-size: 11px; }
  }
</style>
</head>
<body>

<div id="login-screen">
  <div class="login-card">
    <div class="login-logo">
      <svg width="24" height="24" viewBox="0 0 20 20" fill="white">
        <path d="M2 4h16v2H2zm0 5h16v2H2zm0 5h10v2H2z"/>
      </svg>
    </div>
    <h2>TechVigilance</h2>
    <p>Introduce la contraseña para acceder</p>
    <input class="login-field" type="password" id="pwdInput" placeholder="Contraseña" autocomplete="current-password">
    <button class="login-btn" id="loginBtn">Entrar</button>
    <div class="login-error" id="loginError">Contraseña incorrecta.</div>
  </div>
</div>

<div id="app" style="display:none">

<div class="topbar">
  <svg width="20" height="20" viewBox="0 0 20 20" fill="white">
    <path d="M2 4h16v2H2zm0 5h16v2H2zm0 5h10v2H2z"/>
  </svg>
  <h1>TechVigilance</h1>
  <div class="view-toggle">
    <button class="view-btn active" data-view="list" onclick="switchView('list')">📋 Lista</button>
    <button class="view-btn" data-view="radar" onclick="switchView('radar')">📡 Radar</button>
  </div>
  <span class="topbar-count" id="topbar-count">Cargando…</span>
</div>

<div class="stats-bar" id="statsBar"></div>

<div class="commandbar">
  <div class="search-box">
    <svg width="14" height="14" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
      <circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/>
    </svg>
    <input type="search" id="searchInput" placeholder="Buscar en todos los campos…" disabled>
  </div>
  <div class="sep"></div>
  <select class="ms-select" id="sortSelect" disabled>
    <option value="combined">Ordenar: Combined Score</option>
    <option value="global">Ordenar: Global Score</option>
    <option value="internal">Ordenar: Internal Score</option>
    <option value="rank">Ordenar: Rank original</option>
    <option value="year">Ordenar: Año</option>
    <option value="title">Ordenar: A–Z</option>
  </select>
</div>

<div class="filter-bar" id="filterBar">
  <span class="filter-label">Dominio:</span>
  <button class="pill active" data-domain="">Todos</button>
</div>

<main id="grid">
  <div class="state-box"><div class="spinner"></div>Cargando papers…</div>
</main>

<div id="radarView">
  <div class="radar-panel">
    <h3>📡 Global vs Internal Score</h3>
    <div id="scatterContainer"></div>
  </div>
  <div class="radar-panel">
    <h3>🔥 Heatmap Papers × Dominios</h3>
    <div id="heatmapContainer"></div>
  </div>
</div>

<div id="tooltip"></div>

<script>
// ── Colores de dominio ──
const DOM_COLORS = {
  'Brewing & Process':         '#f97316',
  'Byproducts & Circularity':  '#10b981',
  'Materials & Packaging':     '#818cf8',
  'Water & Environment':       '#38bdf8',
  'Biotech applied':           '#ec4899',
  'Analytics & Digital':       '#a78bfa',
  'Neuroscience & Functional': '#eab308'
};

// ── CSV parser ──
function parseCSV(text) {
  if (text.charCodeAt(0) === 0xFEFF) text = text.slice(1);
  const rows = [];
  let row = [], field = "", inQuote = false, i = 0;
  while (i < text.length) {
    const ch = text[i];
    if (inQuote) {
      if (ch === '"' && text[i+1] === '"') { field += '"'; i += 2; continue; }
      if (ch === '"') { inQuote = false; i++; continue; }
      field += ch;
    } else {
      if (ch === '"') { inQuote = true; i++; continue; }
      if (ch === ',') { row.push(field.trim()); field = ""; i++; continue; }
      if (ch === '\n') {
        row.push(field.trim()); field = "";
        if (row.some(Boolean)) rows.push(row);
        row = []; i++; continue;
      }
      if (ch === '\r') { i++; continue; }
      field += ch;
    }
    i++;
  }
  if (field || row.length) { row.push(field.trim()); if (row.some(Boolean)) rows.push(row); }
  return rows;
}

function csvToObjects(rows) {
  if (rows.length < 2) return [];
  const headers = rows[0].map(h => h.toLowerCase().replace(/\s+/g, ""));
  return rows.slice(1).map(cols => {
    const obj = {};
    headers.forEach((h, i) => { obj[h] = cols[i] || ""; });
    return obj;
  });
}

function get(obj, ...keys) {
  for (const k of keys) { const v = (obj[k] || "").trim(); if (v) return v; }
  return "";
}

function parseListField(val) {
  val = val.trim();
  if (!val) return [];
  try {
    const r = JSON.parse(val);
    if (Array.isArray(r)) return r.map(x => String(x).trim()).filter(Boolean);
  } catch {}
  return val.replace(/[\[\]"]/g, "").split(",").map(x => x.trim()).filter(Boolean);
}

function normalizePapers(records) {
  return records
    .map((r, idx) => {
      let matchedTags = [];
      try { matchedTags = JSON.parse(r.matchedtags || '[]'); } catch(e) {}
      return {
        _id:           idx,
        title:         get(r, "title", "titulo"),
        authors:       get(r, "authors", "autores", "author"),
        abstract:      get(r, "abstractmini", "abstract", "resumen"),
        why:           get(r, "whyrelevant", "relevance"),
        link:          get(r, "primaryurl", "url", "link"),
        doi:           get(r, "doi"),
        year:          get(r, "year", "año"),
        rank:          get(r, "paperrank", "rank"),
        domains:       parseListField(get(r, "domain")),
        access:        (parseListField(get(r, "access"))[0] || "").toUpperCase(),
        owner:         get(r, "owner"),
        date:          get(r, "dateadded", "date"),
        globalScore:   parseFloat(r.globalscore)   || 0,
        internalScore: parseFloat(r.internalscore) || 0,
        combinedScore: parseFloat(r.combinedscore) || 0,
        tagMatches:    parseInt(r.tagmatches)       || 0,
        matchedTags:   Array.isArray(matchedTags) ? matchedTags : [],
        _hasScores:    !!(r.globalscore && r.globalscore.trim()),
      };
    })
    .filter(p => p.title);
}

// ── Estado ──
let PAPERS = [], PDF_INDEX = {}, query = "", domain = "", sort = "combined";

function allDomains(papers) {
  const seen = new Set(), list = [];
  papers.forEach(p => p.domains.forEach(d => { if (!seen.has(d)) { seen.add(d); list.push(d); } }));
  return list.sort();
}

function buildDomainPills(papers) {
  const bar = document.getElementById("filterBar");
  [...bar.querySelectorAll(".pill:not([data-domain=''])")].forEach(el => el.remove());
  allDomains(papers).forEach(d => {
    const btn = document.createElement("button");
    btn.className = "pill"; btn.dataset.domain = d; btn.textContent = d;
    btn.onclick = () => setDomain(d);
    bar.appendChild(btn);
  });
}

function setDomain(d) {
  domain = d;
  document.querySelectorAll("#filterBar .pill").forEach(p => p.classList.toggle("active", p.dataset.domain === d));
  render();
}

function esc(s) {
  return String(s||"").replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;");
}
function hl(text, q) {
  if (!q || !text) return esc(text);
  const re = new RegExp("(" + q.replace(/[.*+?^${}()|[\]\\]/g,"\\$&") + ")", "gi");
  return esc(text).replace(re, "<mark>$1</mark>");
}
function matches(p, q) {
  if (!q) return true;
  const lq = q.toLowerCase();
  return [p.title, p.authors, p.abstract, p.why, p.owner, ...p.domains].some(f => f && f.toLowerCase().includes(lq));
}

// ── Stats bar ──
function updateStatsBar(list) {
  const bar = document.getElementById("statsBar");
  if (!PAPERS.length) { bar.innerHTML = ""; return; }
  const gMed = PAPERS.reduce((s,p) => s + p.globalScore, 0) / PAPERS.length;
  const iMed = PAPERS.reduce((s,p) => s + p.internalScore, 0) / PAPERS.length;
  const gold = list.filter(p => p.globalScore >= gMed && p.internalScore >= iMed).length;
  const f1 = n => list.length ? (list.reduce((s,p) => s+n(p), 0) / list.length).toFixed(1) : "—";
  const hasS = PAPERS.some(p => p._hasScores);
  let html = `<span class="sv">${list.length}</span> papers`;
  if (hasS) {
    html += `<span class="ss">·</span> ★ <span class="sv" style="color:#10b981">${gold}</span> Gold`;
    html += `<span class="ss">·</span> Global <span class="sv" style="color:#f97316">${f1(p=>p.globalScore)}</span>`;
    html += `<span class="ss">·</span> Internal <span class="sv" style="color:#818cf8">${f1(p=>p.internalScore)}</span>`;
    html += `<span class="ss">·</span> Combined <span class="sv" style="color:#10b981">${f1(p=>p.combinedScore)}</span>`;
  }
  bar.innerHTML = html;
}

// ── Tiempo relativo ──
function timeAgo(dateStr) {
  if (!dateStr) return '';
  const parts = dateStr.match(/(\d{2})\/(\d{2})\/(\d{4})\s+(\d{2}):(\d{2})/);
  if (!parts) return '';
  const date = new Date(parseInt(parts[3]), parseInt(parts[2])-1, parseInt(parts[1]), parseInt(parts[4]), parseInt(parts[5]));
  const diffDays = Math.floor((new Date() - date) / (1000 * 60 * 60 * 24));
  if (diffDays < 0) return 'futuro';
  if (diffDays === 0) return 'hoy';
  if (diffDays === 1) return 'ayer';
  if (diffDays < 7) return `hace ${diffDays}d`;
  if (diffDays < 30) return `hace ${Math.floor(diffDays/7)}sem`;
  if (diffDays < 365) return `hace ${Math.floor(diffDays/30)}m`;
  return `hace ${Math.floor(diffDays/365)}a`;
}

// ── Render lista ──
function render() {
  const grid = document.getElementById("grid");
  const q = query.trim();
  let list = PAPERS.filter(p =>
    matches(p, q) && (!domain || p.domains.includes(domain))
  );
  if      (sort === "combined")  list.sort((a,b) => b.combinedScore  - a.combinedScore);
  else if (sort === "global")    list.sort((a,b) => b.globalScore    - a.globalScore);
  else if (sort === "internal")  list.sort((a,b) => b.internalScore  - a.internalScore);
  else if (sort === "title")     list.sort((a,b) => a.title.localeCompare(b.title));
  else if (sort === "year")      list.sort((a,b) => (b.year||"").localeCompare(a.year||""));
  else                           list.sort((a,b) => (parseInt(b.rank)||0) - (parseInt(a.rank)||0));

  document.getElementById("topbar-count").textContent = list.length + " papers";
  updateStatsBar(list);

  if (!list.length) {
    grid.innerHTML = '<div class="state-box">No hay resultados para esta búsqueda.</div>';
    return;
  }

  grid.innerHTML = list.map(p => {
    const dtags = p.domains.map(d => `<span class="domain-tag">${esc(d)}</span>`).join(" ");
    const aClass = p.access === "OPEN" ? "open" : "paywall";
    const aLabel = p.access === "OPEN" ? "Open" : p.access === "PAYWALL" ? "Paywall" : p.access;
    const href = p.link || (p.doi ? "https://doi.org/" + p.doi : "");

    const scoreBars = p._hasScores ? `
      <div class="score-bars">
        <div class="score-row">
          <span class="score-label">G</span>
          <div class="score-track"><div class="score-fill global" style="width:${p.globalScore}%"></div></div>
          <span class="score-value">${p.globalScore.toFixed(1)}</span>
        </div>
        <div class="score-row">
          <span class="score-label">I</span>
          <div class="score-track"><div class="score-fill internal" style="width:${p.internalScore}%"></div></div>
          <span class="score-value">${p.internalScore.toFixed(1)}</span>
        </div>
        <div class="score-row">
          <span class="score-label">C</span>
          <div class="score-track"><div class="score-fill combined" style="width:${p.combinedScore}%"></div></div>
          <span class="score-value">${p.combinedScore.toFixed(1)}</span>
        </div>
      </div>` : "";

    const pdfFile = PDF_INDEX[String(p.rank)];
    let openBtns = '';
    if (pdfFile) {
      openBtns = `<a class="btn-open btn-pdf" href="pdfs/${esc(p.rank)}/${esc(pdfFile)}" target="_blank">PDF</a>`;
      if (href) openBtns += ` <a class="btn-open btn-web-small" href="${esc(href)}" target="_blank" rel="noopener">web</a>`;
    } else if (p.access === "PAYWALL" && href) {
      openBtns = `<a class="btn-open btn-paywall-link" href="${esc(href)}" target="_blank" rel="noopener" title="Acceso de pago">🔒 Acceder</a>`;
    } else if (href) {
      openBtns = `<a class="btn-open" href="${esc(href)}" target="_blank" rel="noopener">Abrir <svg width="11" height="11" fill="none" stroke="currentColor" stroke-width="2.5" viewBox="0 0 24 24"><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/><polyline points="15 3 21 3 21 9"/><line x1="10" y1="14" x2="21" y2="3"/></svg></a>`;
    }

    const tagMatchesHtml = p.matchedTags.length > 0 ? `
      <button class="btn-tags" onclick="this.nextElementSibling.classList.toggle('open')">
        🔗 ${p.tagMatches} tag match${p.tagMatches !== 1 ? "es" : ""} ▸
      </button>
      <div class="tag-matches">
        ${p.matchedTags.map(t => `
          <div class="tag-match-item" onclick="setDomain('${esc(t.domain||"")}');window.scrollTo(0,0);" title="Filtrar por ${esc(t.domain||"")}">
            <span class="tag-match-name">${esc(String(t.tag||"").substring(0,50))}</span>
            <span class="tag-match-meta">${esc(t.domain||"")} · ${Math.round((t.strength||0)*100)}%</span>
            ${t.phrases && t.phrases.length ? `<span class="tag-match-phrases">${esc(t.phrases.slice(0,2).join(", "))}</span>` : ""}
          </div>`).join("")}
      </div>` : "";

    return `
    <article class="card" id="card-${p._id}">
      <div class="card-row1">
        ${p.rank ? `<div class="rank-badge">${esc(p.rank)}</div>` : ""}
        <div class="card-main">
          <div class="card-title" ${href ? `onclick="window.open('${esc(href)}','_blank')"` : ""}>${hl(p.title, q)}</div>
          <div class="card-meta">
            ${p.authors ? `<span class="meta-item">${hl(p.authors, q)}</span>` : ""}
            ${p.year    ? `<span class="meta-item">${esc(p.year)}</span>` : ""}
            ${aLabel    ? `<span class="access-badge ${aClass}">${esc(aLabel)}</span>` : ""}
            ${dtags}
            ${p.date ? `<span class="date-chip" title="Añadido: ${esc(p.date)}">📥 ${timeAgo(p.date)}</span>` : ""}
          </div>
          ${scoreBars}
          ${p.abstract ? `<div class="card-abstract" id="abs-${p._id}">${hl(p.abstract, q)}</div>` : ""}
          ${tagMatchesHtml}
          ${p.why ? `<div class="why-box" id="why-${p._id}">${hl(p.why, q)}</div>` : ""}
        </div>
      </div>
      <div class="card-row2">
        <div class="card-actions">
          ${p.why ? `<button class="btn-toggle" onclick="toggleWhy(this)">💡 ¿Por qué?</button>` : ""}
        </div>
        <div style="display:flex;gap:8px;align-items:center">
          ${p.owner ? `<span class="owner-chip" title="${esc(p.owner)}">${esc(p.owner.split(";")[0].trim())}</span>` : ""}
          ${openBtns}
        </div>
      </div>
    </article>`;
  }).join("");
}

function toggleWhy(btn) {
  const why = btn.closest('.card').querySelector('.why-box');
  if (!why) return;
  const isOpen = why.classList.toggle('open');
  btn.textContent = isOpen ? '💡 Ocultar' : '💡 ¿Por qué?';
}
window.toggleWhy = toggleWhy;

// ── Vista switch ──
function switchView(view) {
  document.querySelectorAll(".view-btn").forEach(b => b.classList.toggle("active", b.dataset.view === view));
  const grid  = document.getElementById("grid");
  const radar = document.getElementById("radarView");
  if (view === "list") {
    grid.style.display  = "";
    radar.classList.remove("active");
  } else {
    grid.style.display = "none";
    radar.classList.add("active");
    requestAnimationFrame(() => { renderScatter(); renderHeatmap(); });
  }
}

// ── Scatter plot (SVG inline, sin dependencias) ──
function renderScatter() {
  const container = document.getElementById("scatterContainer");
  if (!PAPERS.length) { container.innerHTML = '<p class="radar-placeholder">Sin papers cargados.</p>'; return; }
  const hasScores = PAPERS.some(p => p._hasScores);
  if (!hasScores) {
    container.innerHTML = `<p class="radar-placeholder">📊 Sin datos de scoring aún.</p>`;
    return;
  }
  const W = Math.max(container.offsetWidth || 400, 280);
  const H = 340;
  const pad = { top: 24, right: 16, bottom: 42, left: 42 };
  const pw = W - pad.left - pad.right;
  const ph = H - pad.top - pad.bottom;
  const gMed = PAPERS.reduce((s,p) => s + p.globalScore, 0) / PAPERS.length;
  const iMed = PAPERS.reduce((s,p) => s + p.internalScore, 0) / PAPERS.length;
  const maxC = Math.max(...PAPERS.map(p => p.combinedScore), 1);
  const sx = v => pad.left + (v / 100) * pw;
  const sy = v => pad.top + ph - (v / 100) * ph;
  let svg = `<svg id="scatterSvg" width="${W}" height="${H}" viewBox="0 0 ${W} ${H}" style="font-family:inherit;display:block">`;
  [0,25,50,75,100].forEach(v => {
    svg += `<line x1="${sx(v).toFixed(1)}" y1="${pad.top}" x2="${sx(v).toFixed(1)}" y2="${H-pad.bottom}" stroke="#e2e8f0" stroke-width="0.5" stroke-dasharray="3,3"/>`;
    svg += `<line x1="${pad.left}" y1="${sy(v).toFixed(1)}" x2="${W-pad.right}" y2="${sy(v).toFixed(1)}" stroke="#e2e8f0" stroke-width="0.5" stroke-dasharray="3,3"/>`;
    svg += `<text x="${sx(v).toFixed(1)}" y="${H-pad.bottom+13}" text-anchor="middle" fill="#94a3b8" font-size="10">${v}</text>`;
    svg += `<text x="${pad.left-5}" y="${(sy(v)+3).toFixed(1)}" text-anchor="end" fill="#94a3b8" font-size="10">${v}</text>`;
  });
  svg += `<line x1="${sx(gMed).toFixed(1)}" y1="${pad.top}" x2="${sx(gMed).toFixed(1)}" y2="${H-pad.bottom}" stroke="#94a3b8" stroke-width="1" stroke-dasharray="5,3" opacity="0.5"/>`;
  svg += `<line x1="${pad.left}" y1="${sy(iMed).toFixed(1)}" x2="${W-pad.right}" y2="${sy(iMed).toFixed(1)}" stroke="#94a3b8" stroke-width="1" stroke-dasharray="5,3" opacity="0.5"/>`;
  svg += `<text x="${sx((100+gMed)/2).toFixed(1)}" y="${(sy((100+iMed)/2)+4).toFixed(1)}" text-anchor="middle" fill="#10b981" font-size="11" font-weight="600" opacity="0.7">★ GOLD</text>`;
  svg += `<text x="${sx(gMed/2).toFixed(1)}" y="${(sy((100+iMed)/2)+4).toFixed(1)}" text-anchor="middle" fill="#818cf8" font-size="10" opacity="0.6">NICHE</text>`;
  svg += `<text x="${sx((100+gMed)/2).toFixed(1)}" y="${(sy(iMed/2)+4).toFixed(1)}" text-anchor="middle" fill="#f97316" font-size="10" opacity="0.6">WATCH</text>`;
  svg += `<text x="${sx(gMed/2).toFixed(1)}" y="${(sy(iMed/2)+4).toFixed(1)}" text-anchor="middle" fill="#94a3b8" font-size="10" opacity="0.5">BACKLOG</text>`;
  svg += `<text x="${(W/2).toFixed(1)}" y="${H-3}" text-anchor="middle" fill="#94a3b8" font-size="11">Global Score →</text>`;
  svg += `<text x="11" y="${(H/2).toFixed(1)}" text-anchor="middle" fill="#94a3b8" font-size="11" transform="rotate(-90,11,${(H/2).toFixed(1)})">Internal →</text>`;
  PAPERS.forEach(p => {
    const r = (4 + (p.combinedScore / maxC) * 10).toFixed(1);
    const col = DOM_COLORS[p.domains[0]] || "#94a3b8";
    const safeTitle = p.title.substring(0, 60).replace(/"/g, "&quot;").replace(/'/g, "&#39;");
    svg += `<circle class="scatter-dot"
      cx="${sx(p.globalScore).toFixed(1)}" cy="${sy(p.internalScore).toFixed(1)}" r="${r}"
      fill="${col}" fill-opacity="0.65" stroke="${col}" stroke-width="1.5"
      data-pid="${p._id}" data-title="${safeTitle}"
      data-scores="G=${p.globalScore.toFixed(1)} · I=${p.internalScore.toFixed(1)} · C=${p.combinedScore.toFixed(1)}"/>`;
  });
  svg += "</svg>";
  container.innerHTML = svg;
  const svgEl = container.querySelector("#scatterSvg");
  svgEl.addEventListener("mousemove", e => {
    const dot = e.target.closest(".scatter-dot");
    if (dot) showTooltip(e, dot.dataset.title, dot.dataset.scores);
    else hideTooltip();
  });
  svgEl.addEventListener("mouseleave", hideTooltip);
  svgEl.addEventListener("click", e => {
    const dot = e.target.closest(".scatter-dot");
    if (dot) scrollToCard(parseInt(dot.dataset.pid));
  });
}

// ── Heatmap ──
function renderHeatmap() {
  const container = document.getElementById("heatmapContainer");
  if (!PAPERS.length) { container.innerHTML = '<p class="radar-placeholder">Sin papers cargados.</p>'; return; }
  const hasMatchData = PAPERS.some(p => p.matchedTags && p.matchedTags.length > 0);
  if (!hasMatchData) {
    container.innerHTML = `<p class="radar-placeholder">🔥 Sin datos de tag matching aún.</p>`;
    return;
  }
  const top15 = [...PAPERS].sort((a,b) => b.combinedScore - a.combinedScore).slice(0, 15);
  const domainSet = new Set();
  PAPERS.forEach(p => p.matchedTags.forEach(t => { if (t.domain) domainSet.add(t.domain); }));
  const domCols = Object.keys(DOM_COLORS).filter(d => domainSet.has(d));
  const matrix = top15.map(p =>
    domCols.map(d => p.matchedTags.filter(t => t.domain === d).reduce((s,t) => s + (t.strength||0), 0))
  );
  const colMax = domCols.map((_, ci) => Math.max(...matrix.map(r => r[ci]), 0.001));
  const hexToRgb = h => `${parseInt(h.slice(1,3),16)},${parseInt(h.slice(3,5),16)},${parseInt(h.slice(5,7),16)}`;
  const shortName = d => d.split(' & ')[0].split(' ')[0].substring(0, 8);
  let html = `<div style="overflow-x:auto"><table class="heatmap-table"><thead><tr>
    <th style="text-align:left;min-width:120px">Paper</th>
    ${domCols.map(d => `<th title="${esc(d)}" style="color:${DOM_COLORS[d]}">${shortName(d)}</th>`).join("")}
    <th style="color:#10b981">C</th>
  </tr></thead><tbody>`;
  top15.forEach((p, ri) => {
    html += `<tr>
      <td title="${esc(p.title)}" onclick="scrollToCard(${p._id})">${esc(p.title.substring(0, 32))}…</td>
      ${domCols.map((d, ci) => {
        const norm = matrix[ri][ci] / colMax[ci];
        const rgb  = hexToRgb(DOM_COLORS[d] || "#94a3b8");
        const bg   = norm > 0.05 ? `rgba(${rgb},${Math.min(norm * 0.8 + 0.1, 0.9).toFixed(2)})` : "transparent";
        const val  = norm > 0.05 ? Math.round(norm * 100) : "";
        const tc   = norm > 0.45 ? "white" : "#334155";
        return `<td style="background:${bg};color:${tc}" data-domain="${esc(d)}" onclick="heatCellClick(event)">${val}</td>`;
      }).join("")}
      <td style="color:#10b981;font-weight:700">${p.combinedScore.toFixed(1)}</td>
    </tr>`;
  });
  html += "</tbody></table></div>";
  container.innerHTML = html;
}

function heatCellClick(e) {
  const d = e.currentTarget.dataset.domain;
  if (d) { setDomain(d); switchView("list"); }
}

function scrollToCard(pid) {
  query = ""; domain = "";
  const si = document.getElementById("searchInput");
  if (si) si.value = "";
  document.querySelectorAll("#filterBar .pill").forEach(p => p.classList.toggle("active", p.dataset.domain === ""));
  switchView("list");
  render();
  requestAnimationFrame(() => {
    const el = document.getElementById("card-" + pid);
    if (el) {
      el.scrollIntoView({ behavior: "smooth", block: "center" });
      el.style.outline = "2px solid #0078d4";
      setTimeout(() => { el.style.outline = ""; }, 2000);
    }
  });
}

// ── Tooltip ──
const _tooltip = document.getElementById("tooltip");
function showTooltip(e, title, scores) {
  _tooltip.innerHTML = `<div style="font-weight:600;margin-bottom:3px">${esc(title)}…</div><div style="color:#94a3b8;font-size:11px">${esc(scores)}</div>`;
  _tooltip.style.display = "block";
  _tooltip.style.left = (e.clientX + 14) + "px";
  _tooltip.style.top  = (e.clientY - 10) + "px";
}
function hideTooltip() { _tooltip.style.display = "none"; }

// ── Controles ──
document.getElementById("searchInput").addEventListener("input",  e => { query = e.target.value; render(); });
document.getElementById("sortSelect").addEventListener("change",  e => { sort  = e.target.value; render(); });
document.querySelector(".pill[data-domain='']").onclick = () => setDomain("");

// ── Auth ──
// Contraseña: haka_2026
const HASH = "d1325278ceeeb1fe96b7c3b64e6c495c16074b8864c7b82af202573bfb4ff98f";

async function sha256(str) {
  const buf = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(str));
  return Array.from(new Uint8Array(buf)).map(b => b.toString(16).padStart(2,"0")).join("");
}

async function tryLogin() {
  const val = document.getElementById("pwdInput").value;
  const hash = await sha256(val);
  if (hash === HASH) {
    sessionStorage.setItem("tv_auth", "1");
    document.getElementById("login-screen").style.display = "none";
    document.getElementById("app").style.display = "block";
    loadCSV();
  } else {
    const field = document.getElementById("pwdInput");
    const err   = document.getElementById("loginError");
    field.classList.add("error");
    err.style.display = "block";
    field.value = "";
    field.focus();
    setTimeout(() => { field.classList.remove("error"); err.style.display = "none"; }, 2500);
  }
}

document.getElementById("loginBtn").onclick = tryLogin;
document.getElementById("pwdInput").addEventListener("keydown", e => { if (e.key === "Enter") tryLogin(); });

if (sessionStorage.getItem("tv_auth") === "1") {
  document.getElementById("login-screen").style.display = "none";
  document.getElementById("app").style.display = "block";
}

// ── Carga CSV ──
function loadCSV() {
  // Índice de PDFs — carga en paralelo
  fetch("pdfs/index.json")
    .then(r => r.ok ? r.json() : {})
    .catch(() => ({}))
    .then(idx => { PDF_INDEX = idx; if (PAPERS.length) render(); });

  fetch("papers.csv")
    .then(r => {
      if (!r.ok) throw new Error("No se pudo cargar papers.csv (" + r.status + ")");
      return r.text();
    })
    .then(text => {
      const rows    = parseCSV(text);
      const records = csvToObjects(rows);
      PAPERS        = normalizePapers(records);
      buildDomainPills(PAPERS);
      ["searchInput","sortSelect"].forEach(id => document.getElementById(id).disabled = false);
      render();
    })
    .catch(err => {
      document.getElementById("grid").innerHTML =
        `<div class="state-box">⚠️ Error al cargar los datos.<br><small>${esc(err.message)}</small></div>`;
      document.getElementById("topbar-count").textContent = "Error";
    });
}

if (sessionStorage.getItem("tv_auth") === "1") loadCSV();
</script>
</div>
</body>
</html>
```

---

## 9. Código completo — watcher.sh

```bash
#!/bin/bash
# Vigila papers.csv y pdfs/ en esta carpeta.
# Cuando detecta un cambio, hace commit y push automáticamente a GitHub Pages.

REPO="$(cd "$(dirname "$0")" && pwd)"
CSV="$REPO/papers.csv"
PDF_DIR="$REPO/pdfs"

echo "👁  Vigilando: $CSV y $PDF_DIR"
echo "    Cada vez que guardes el CSV o añadas un PDF, la web se actualizará sola."
echo "    Pulsa Ctrl+C para detener."
echo ""

fswatch -0 "$CSV" "$PDF_DIR" | while IFS= read -r -d "" event; do
  cd "$REPO"

  if [[ "$event" == *.pdf ]]; then
    echo "$(date '+%H:%M:%S')  PDF detectado: $event — regenerando índice..."
    python3 build_pdf_index.py
    git add pdfs/
    git commit -m "PDF añadido — $(date '+%d/%m/%Y %H:%M')"
    git push
    echo "$(date '+%H:%M:%S')  ✓ PDF disponible en la web en ~30 segundos."
  else
    echo "$(date '+%H:%M:%S')  Cambio en CSV detectado — subiendo a GitHub..."
    git add papers.csv
    git commit -m "Actualizar papers — $(date '+%d/%m/%Y %H:%M')"
    git push
    echo "$(date '+%H:%M:%S')  ✓ Listo. Web actualizada en ~30 segundos."
  fi
  echo ""
done
```

---

## 10. Código completo — build_pdf_index.py

```python
#!/usr/bin/env python3
"""Genera pdfs/index.json con la lista de PDFs disponibles.
Ejecutar despues de añadir cualquier PDF a pdfs/{rank}/
"""
import os, json

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
pdf_dir = os.path.join(SCRIPT_DIR, "pdfs")
available = {}

if os.path.isdir(pdf_dir):
    for folder in sorted(os.listdir(pdf_dir)):
        folder_path = os.path.join(pdf_dir, folder)
        if os.path.isdir(folder_path):
            pdfs = [f for f in os.listdir(folder_path) if f.lower().endswith(".pdf")]
            if pdfs:
                available[folder] = pdfs[0]

out_path = os.path.join(pdf_dir, "index.json")
with open(out_path, "w") as f:
    json.dump(available, f, indent=2)

total_folders = len([d for d in os.listdir(pdf_dir) if os.path.isdir(os.path.join(pdf_dir, d))]) if os.path.isdir(pdf_dir) else 0
print(f"PDF index: {len(available)} PDFs disponibles de {total_folders} carpetas")
for rank, filename in sorted(available.items(), key=lambda x: int(x[0]) if x[0].isdigit() else 0):
    print(f"  pdfs/{rank}/{filename}")
```

---

## 11. Código completo — add_pdf.sh

```bash
#!/bin/bash
# add_pdf.sh — Añade un PDF a la biblioteca de TechVigilance
# Uso: bash add_pdf.sh <PaperRank> <ruta_al_pdf>
# Ejemplo: bash add_pdf.sh 22 ~/Downloads/paper.pdf

cd /Users/nomada/papers-page

if [ -z "$1" ] || [ -z "$2" ]; then
  echo "Uso: bash add_pdf.sh <PaperRank> <ruta_al_pdf>"
  echo "Ejemplo: bash add_pdf.sh 22 ~/Downloads/mi-paper.pdf"
  exit 1
fi

RANK=$1
PDF_PATH=$2

if [ ! -f "$PDF_PATH" ]; then
  echo "Error: no encuentro el archivo $PDF_PATH"
  exit 1
fi

# Crear carpeta si no existe
mkdir -p "pdfs/$RANK"

# Copiar PDF
FILENAME=$(basename "$PDF_PATH")
cp "$PDF_PATH" "pdfs/$RANK/$FILENAME"
echo "Copiado: pdfs/$RANK/$FILENAME"

# Regenerar índice
python3 build_pdf_index.py

# Git
git add "pdfs/$RANK/" pdfs/index.json
git commit -m "PDF añadido: rank $RANK ($FILENAME)"
git push

echo ""
echo "✅ PDF disponible en la web en ~1 minuto"
```

---

## 12. Código completo — generate.py (script original, legacy)

> Este script es el generador original que producía el `index.html` desde un CSV embebiendo los datos. **Ya no se usa** — la versión actual de `index.html` carga `papers.csv` dinámicamente via `fetch()`. Se conserva por referencia histórica.

El archivo existe en `/Users/nomada/papers-page/generate.py`. Lee un CSV y genera un `index.html` estático con los papers embebidos como JSON. La versión actual es superior porque: los datos están en `papers.csv` separado (fácil de actualizar), tiene scoring, vista radar, PDFs dinámicos y login.

---

## 13. Decisiones de arquitectura (ADRs)

### ADR-001: Vanilla HTML/CSS/JS
Un solo `index.html` con CSS y JS inline. Cero dependencias, cero build step. Despliegue trivial (solo archivos estáticos).

### ADR-002: Pipeline de scoring automático
`papers_raw.csv` → `score_papers.py` → `papers.csv`. El usuario nunca edita `papers.csv` directamente. `watcher.sh` con fswatch detecta cambios y hace git push automáticamente.

### ADR-003: Scoring dual — GlobalScore × InternalScore → CombinedScore
- **GlobalScore**: Recencia 45% + Riqueza abstract 25% + Riqueza WhyRelevant 18% + Tiene owner 12%
- **InternalScore**: Cruce semántico contra 104 WatchTags. Bonus ×1.4 si Domain coincide.
- **CombinedScore**: Media geométrica `sqrt(G × I)` — premia equilibrio sobre extremos.

### ADR-004: PDFs en GitHub Pages
`pdfs/{rank}/archivo.pdf` dentro del repo. `build_pdf_index.py` genera `pdfs/index.json`. La web carga el índice y muestra botón PDF solo si el archivo existe.

### ADR-005: Diseño minimalista (estilo Claude)
Barras de score de 3px, mucho aire, tipografía limpia. Paleta restringida: naranja/violeta/verde solo para los 3 scores. El foco visual sigue en el título y abstract.

### ADR-006: Estructura de archivos (ver sección 2)

### ADR-007: Vista Radar
Toggle Lista/Radar. Scatter SVG inline (sin D3): X=Global, Y=Internal, tamaño=Combined, color=Dominio. Cuadrantes GOLD/WATCH/NICHE/BACKLOG por medianas. Heatmap HTML table top 15 papers × 7 dominios.

---

## 14. Contraseña y autenticación

- **Contraseña actual**: `haka_2026`
- **Hash SHA-256**: `d1325278ceeeb1fe96b7c3b64e6c495c16074b8864c7b82af202573bfb4ff98f`
- La verificación ocurre en el cliente (navegador) via `crypto.subtle.digest`
- La sesión persiste en `sessionStorage` (se cierra al cerrar la pestaña)
- **Nota**: Esta protección es para uso interno — no es seguridad criptográfica robusta. Cualquiera con el código fuente puede extraer el hash.

Para cambiar la contraseña, generar un nuevo SHA-256 y actualizar `HASH` en `index.html`.

---

## 15. Flujos operativos habituales

### Añadir un paper nuevo

1. Editar `papers_raw.csv` con el nuevo paper (12 columnas)
2. Ejecutar `score_papers.py` (o esperar al watcher si está corriendo)
3. Si el watcher está activo, el push ocurre automáticamente al guardar

### Añadir un PDF a un paper PAYWALL

**Opción A — Automática (con watcher corriendo):**
```
Copiar el PDF a pdfs/{rank}/archivo.pdf
→ watcher detecta el .pdf
→ regenera index.json + git push automático
→ ~30s después disponible en la web
```

**Opción B — Manual (todo en uno):**
```bash
bash add_pdf.sh 22 ~/Downloads/mi-paper.pdf
```

**Opción C — Paso a paso:**
```bash
cp ~/Downloads/mi-paper.pdf /Users/nomada/papers-page/pdfs/22/
cd /Users/nomada/papers-page
python3 build_pdf_index.py
git add pdfs/
git commit -m "PDF rank 22"
git push
```

### Iniciar el watcher

```bash
bash /Users/nomada/papers-page/watcher.sh
```

### Ver el estado del repo

```bash
cd /Users/nomada/papers-page
git status
git log --oneline -10
```

### Forzar actualización manual de la web

```bash
cd /Users/nomada/papers-page
git add papers.csv pdfs/
git commit -m "Actualización manual"
git push
```
