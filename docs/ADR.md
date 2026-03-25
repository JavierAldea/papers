# ADR — Architecture Decision Records · TechVigilance

---

## ADR-001: Arquitectura vanilla (HTML/CSS/JS puro, sin framework)

**Estado**: Aceptado
**Fecha**: 2026-03-25
**Contexto**: La app muestra papers desde un CSV. No hay interacciones complejas de estado.
**Decisión**: Un solo `index.html` con CSS y JS inline. Cero dependencias, cero build step.
**Consecuencias**: Despliegue trivial (solo servir archivos estáticos). Cualquier persona puede entender y modificar el código. No escala bien si la app crece a >2000 LOC de JS, pero para este caso es ideal.

---

## ADR-002: Pipeline de scoring automático (papers_raw -> score_papers.py -> papers.csv)

**Estado**: Aceptado
**Fecha**: 2026-03-25
**Contexto**: Los papers necesitan 3 scores calculados (GlobalScore, InternalScore, CombinedScore) que dependen de cruzar datos con WatchTags.csv.
**Decisión**:
- `papers_raw.csv` (12 cols) es el archivo fuente que se edita manualmente o por otra IA
- `WatchTags.csv` (14 cols) son las antenas de vigilancia con keywords y pesos
- `score_papers.py` lee ambos, calcula scores, genera `papers.csv` (17 cols)
- `watcher.sh` con fswatch detecta cambios en papers_raw.csv o WatchTags.csv, ejecuta score_papers.py, hace git push

**Consecuencias**: El usuario nunca edita `papers.csv` directamente. Los scores se recalculan automaticamente. WatchTags.csv se puede editar para cambiar prioridades sin tocar codigo.

---

## ADR-003: Scoring dual — GlobalScore x InternalScore -> CombinedScore

**Estado**: Aceptado
**Fecha**: 2026-03-25
**Contexto**: Necesitamos distinguir "relevante para el mundo" de "relevante para nosotros".
**Decisión**:
- **GlobalScore (0-100)**: Recencia 45% + Riqueza abstract 25% + Riqueza WhyRelevant 18% + Tiene owner 12%. No incluye accesibilidad (OPEN/PAYWALL) porque se paga y punto.
- **InternalScore (0-100)**: Cruce semantico de Title+Abstract+WhyRelevant del paper contra las 104 WatchTags. Matching por keyword phrases, con bonus x1.4 si el Domain coincide. Normalizado 0-100 sobre el rango observado.
- **CombinedScore**: Media geometrica sqrt(G*I) que premia el equilibrio sobre valores extremos en un solo eje.

**Consecuencias**: Un paper puede ser GlobalScore=100 (muy reciente, bien documentado) pero InternalScore=0 (no toca ningun tema nuestro). El CombinedScore baja ese paper frente a uno con G=70 I=70.

---

## ADR-004: PDFs de papers PAYWALL servidos desde GitHub Pages

**Estado**: Aceptado
**Fecha**: 2026-03-25
**Contexto**: Los papers PAYWALL no tienen URL publica. Necesitamos servirlos de alguna forma gratuita.
**Decisión**:
- Los PDFs se almacenan en `pdfs/{PaperRank}/paper.pdf` dentro del repo
- GitHub Pages sirve estos archivos estaticamente
- Limite: 1GB por repo, ~25MB por archivo. Con ~10 papers PAYWALL x ~3MB = ~30MB, muy dentro del limite
- El boton "Abrir" de papers PAYWALL apunta a `pdfs/{rank}/paper.pdf`
- `build_pdf_index.py` genera `pdfs/index.json` con la lista de PDFs disponibles
- La web carga el indice y solo muestra el boton PDF si el archivo existe

**Alternativas descartadas**:
- Google Drive: requiere autenticacion, URLs cambiantes
- Carpeta local: solo funciona en el Mac del usuario, no es web funcional
- .gitignore de PDFs: rompe GitHub Pages (404)

**Consecuencias**: El repo es un poco mas pesado, pero la web es completamente funcional y gratuita desde cualquier dispositivo.

---

## ADR-005: Diseño minimalista limpio (tipo interfaz de Claude)

**Estado**: Aceptado
**Fecha**: 2026-03-25
**Contexto**: La primera iteracion de las barras de score era demasiado gruesa y agresiva visualmente.
**Decisión**:
- Barras de score: 3px de alto, colores suaves, compactas en una sola linea por score
- Mucho aire (padding generoso, spacing entre elementos)
- Tipografia limpia sin negrita excesiva
- Chips y badges pequeños, bordes sutiles
- Tag matches ocultos por defecto, expandibles con click discreto
- Paleta restringida: gris slate para texto, naranja/violeta/verde solo para los 3 scores

**Consecuencias**: La informacion de scoring esta presente pero no domina la tarjeta. El foco visual sigue en el titulo y el abstract del paper.

---

## ADR-006: Estructura de archivos del proyecto

**Estado**: Aceptado
**Fecha**: 2026-03-25

```
papers-page/
  index.html            <- App web (HTML+CSS+JS inline)
  papers_raw.csv        <- FUENTE: papers sin scores (12 cols) - se edita
  WatchTags.csv         <- FUENTE: antenas de vigilancia (104 tags) - se edita
  score_papers.py       <- PIPELINE: calcula scores
  papers.csv            <- GENERADO: papers con scores (17 cols) - NO editar
  watcher.sh            <- AUTOMATION: fswatch -> score -> git push
  watcher.log           <- Log del watcher
  setup_pdfs.sh         <- UTILITY: crea carpetas para PDFs
  build_pdf_index.py    <- UTILITY: genera pdfs/index.json
  add_pdf.sh            <- UTILITY: copia un PDF y hace push
  pdfs/                 <- PDFs de papers PAYWALL
    index.json          <- Indice de PDFs disponibles (generado)
    {rank}/paper.pdf
  docs/                 <- Documentacion
    ADR.md              <- Este archivo
  .gitignore            <- Solo ignora watcher.log y .DS_Store
```

---

## ADR-007: Vista Radar (scatter + heatmap) como segunda vista

**Estado**: Aceptado
**Fecha**: 2026-03-25
**Contexto**: La lista de papers es buena para lectura secuencial pero no para ver patrones.
**Decisión**:
- Toggle Lista/Radar en el topbar
- Scatter plot SVG inline (cero dependencias): X=GlobalScore, Y=InternalScore, tamaño=CombinedScore, color=Dominio
- Heatmap HTML table: top 15 papers x 7 dominios, intensidad = matching strength
- Lineas de mediana que dividen en cuadrantes GOLD/WATCH/NICHE/BACKLOG

**Consecuencias**: Vista complementaria que permite identificar rapidamente papers desalineados (alto Global pero bajo Internal) y clusters por dominio.
