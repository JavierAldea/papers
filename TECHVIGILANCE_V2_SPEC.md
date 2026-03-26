TechVigilance v2 — Especificación Completa para Claude Code



Objetivo: Reescribir index.html como mejora integral de la herramienta de vigilancia tecnológica.
Arquitectura: Vanilla HTML/CSS/JS. Un solo archivo. Cero dependencias externas. Cero build step.
Desplegado en: GitHub Pages (archivos estáticos).
Referencia de diseño: Estética tipo terminal de Anthropic / ChatGPT — moderna, minimalista, slate oscuro + blancos + grises neutros.



PALETA DE COLORES (OBLIGATORIA)

Abandonar el azul corporativo Microsoft. Usar paleta slate moderna:

Topbar:            #1e293b (slate-800)
Fondo página:      #f8fafc (slate-50)
Tarjetas:          #ffffff borde #e8ecf0
Texto principal:   #1e293b (slate-800)
Texto secundario:  #64748b (slate-500)
Texto muted:       #94a3b8 (slate-400)
Bordes:            #e2e8f0 (slate-200)
Hover highlight:   #f1f5f9 (slate-100)
Acento (links):    #0078d4 (solo para links y elementos activos)
Botones primarios: #1e293b (slate-800)
Botón PDF:         #475569 (slate-600)
Botón Paywall:     #1e293b
Bookmark activo:   #f59e0b (amber)
Chip NUEVO:        #eff6ff fondo, #2563eb texto

Score bars — colores MUY apagados con opacity 0.7:

Global bar:    #fdba74 (orange-300, opacity 0.7)
Internal bar:  #a5b4fc (indigo-300, opacity 0.7)
Combined bar:  #6ee7b7 (emerald-300, opacity 0.7)
Track:         #f1f5f9

Los labels de scores ("Global", "Internal", "Combined") van en #64748b (gris neutro), NO en el color de la barra.



CAMBIO 2: BARRA DE FILTROS — DROPDOWNS MULTI-SELECT

ANTES: Pills de dominio individuales (una fila larga), select simple de owner
DESPUÉS: Dropdowns compactos con multi-selección

┌──────────────────────────────────────────────────────────────┐
│ [▼ Todos los dominios] [▼ Todos los owners] │ Combined ≥ ──○── 0 │ ★ │
└──────────────────────────────────────────────────────────────┘

Dropdown de dominios:





Botón muestra: "Todos los dominios" si ninguno seleccionado, nombre si uno, "3 seleccionados" si varios



Click abre panel dropdown con checkboxes



Se pueden seleccionar VARIOS dominios simultáneamente



Opción "Todos los dominios" al inicio que limpia la selección



Click fuera cierra el dropdown

Dropdown de owners:





Mismo patrón que dominios



Opciones pobladas dinámicamente desde los datos

Slider de score:





Combined ≥ con rango 0-80



Valor mostrado en monospace



Color accent: #475569

Botón favoritos:





★ en botón simple



Activo: fondo amber, borde amber



Inactivo: gris claro

IMPORTANTE: Todos los filtros son combinables. El filtrado es AND:

papers.filter(p =>
  (dominios.size === 0 || p.domains.some(d => dominios.has(d))) &&
  (owners.size === 0 || owners.has(p.owner)) &&
  p.combinedScore >= minScore &&
  (!filterBookmarks || bookmarks.has(p._id)) &&
  matches(p, query)
)



CAMBIO 4: TARJETAS — DISEÑO REFINADO

Estructura de cada tarjeta:

┌─────────────────────────────────────────────────────────────────┐
│ [10]  ☆ Purification and characterization of novel barley...    │
│       ↑ rank     ↑ bookmark (★ si activo, ☆ si no)             │
│                                                                  │
│       Zhang, L.; Müller, K. · 2025 · PAYWALL                    │
│       [Brewing & Process] [Biotech applied]  Nuevo  📥 hoy      │
│                                                                  │
│       Global     ████████████████░░░░  92.1                      │
│       Internal   █████████████░░░░░░░  87.3                      │
│       Combined   ██████████████████░░  89.7                      │
│                                                                  │
│       This study presents a comprehensive analysis of newly...   │
│                                                                  │
│       8 tag matches ▸                                            │
│  ─────────────────────────────────────────────────────────────── │
│  ¿Por qué es relevante?    📝 ✓         [Javier]  [PDF] [web]   │
└─────────────────────────────────────────────────────────────────┘

Detalles:





Rank badge: #1e293b, border-radius 8px (más redondeado)



Título: #1e293b, hover → #0078d4



Sin emojis en "¿Por qué es relevante?" (texto plano, gris)



Sin emoji en tag matches (solo "8 tag matches ▸")



Separador fino (border-top: 1px solid #f1f5f9) antes del footer



Domain tags: fondo #f1f5f9, texto #475569 (neutros, no azules)



Access badge: Open = #f0fdf4 fondo #16a34a texto. Paywall = #fefce8 fondo #a16207 texto



Chip NUEVO: #eff6ff fondo, #2563eb texto, animación pulse suave, texto "Nuevo" (no "NUEVO")



Botón notas: 📝 gris, si tiene nota → #475569 + " ✓"



Botones de acción (PDF, Acceder, Abrir): fondo #1e293b o #475569, border-radius 6px



Owner chip: fondo #f8fafc, borde #f1f5f9, border-radius 6px



Animación fade-in escalonada al renderizar la lista

Caja "¿Por qué?":

fondo: #fafbfc (NO amarillo)
borde izquierdo: 3px solid #cbd5e1 (gris, NO amarillo)
texto: #475569



CAMBIO 6: HEATMAP CON PAGINACIÓN

ANTES: Top 15 fijo
DESPUÉS: Todos los papers filtrados, 15 por página

┌──────────────────────────────────────────────────┐
│ 🔥 Heatmap Papers × Dominios     « ‹ 1/4 › »    │
│                                                    │
│ Paper            Brewing Byprod. Material... C     │
│ ─────────────────────────────────────────────     │
│ Purification...   27     100              92.8    │
│ Recent advances          100    100       78.5    │
│ ...                                               │
│                                                    │
│ 42 papers · Pág. 1 de 4                           │
└──────────────────────────────────────────────────┘





Paginación: « ‹ 1/4 › » botones



Cross-highlight: hover en fila resalta el dot en scatter (y viceversa)



Click en título → scroll a la tarjeta en vista lista



Click en celda de dominio → filtra por ese dominio



CAMBIO 8: SISTEMA MULTI-USUARIO

Mismo flujo de login (pantalla password), pero códigos personales:

const USERS = {
  "d1325278ceeeb1fe96b7c3b64e6c495c16074b8864c7b82af202573bfb4ff98f": "Javier"
  // Más usuarios se añaden con add_user.py
};

Login: sha256(input) → buscar en USERS → si existe, currentUser = USERS[hash].

Todas las funciones de localStorage se prefijan por usuario:

function lsKey(k) { return "tv_" + currentUser + "_" + k; }
function lsGet(k, def) { try { return JSON.parse(localStorage.getItem(lsKey(k))); } catch { return def; } }
function lsSet(k, v) { localStorage.setItem(lsKey(k), JSON.stringify(v)); }

Esto separa: bookmarks, notas, última visita → por persona.

Texto del login: "Introduce tu código de acceso personal" (no "contraseña").



CAMBIO 10: CHIP "NUEVO"

Papers añadidos después de la última visita del usuario.

let lastVisit = lsGet("lastvisit", 0);
function isNewPaper(p) {
  const d = parseDate(p.date);
  return d && lastVisit && d.getTime() > lastVisit;
}
// Actualizar lastVisit 3 segundos después de cargar (para que el chip se vea):
setTimeout(() => lsSet("lastvisit", Date.now()), 3000);

Chip: texto "Nuevo", fondo #eff6ff, texto #2563eb, animación pulse 2.5s.



CAMBIO 12: EXPORTAR CSV

Botón "Exportar" en la command bar.
Descarga CSV de la vista filtrada actual con columnas:
Rank, Title, Authors, Year, Domains, GlobalScore, InternalScore, CombinedScore, Access, Owner

function exportCSV() {
  const list = getSorted(getFiltered());
  let csv = "Rank,Title,Authors,Year,Domains,GlobalScore,InternalScore,CombinedScore,Access,Owner\n";
  list.forEach(p => {
    csv += [p.rank, '"'+p.title.replace(/"/g,'""')+'"', ...].join(",") + "\n";
  });
  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = 'techvigilance_export_' + new Date().toISOString().slice(0,10) + '.csv';
  a.click();
}



CAMBIO 14: MOBILE RESPONSIVE

Breakpoints:





@media(max-width: 900px): radar grid → 1 columna, timeline ocupa full width



@media(max-width: 600px): topbar compacto (ocultar nombre usuario), cards padding reducido, rank badge más pequeño, panel de notas full width, dropdowns de filtro más compactos



CAMBIO 16: RSS FEED GENERATOR

Generar script generate_feed.py que:





Lee papers.csv



Genera feed.xml (Atom) con los últimos 50 papers



Incluye: título, link, abstract, scores, dominios

Uso: python3 generate_feed.py (ejecutar después de actualizar papers.csv).



ARCHIVOS A GENERAR





index.html — REESCRIBIR completo con todos los cambios



manifest.json — PWA manifest



sw.js — Service Worker



add_user.py — Generador de códigos de acceso



generate_feed.py — Generador de RSS feed



VERIFICACIÓN FINAL

Tras generar todos los archivos, verifica que:





La web carga con la contraseña haka_2026 y identifica al usuario como "Javier"



Los dropdowns de dominio y owner permiten multi-selección



El slider de Combined Score filtra correctamente



Las barras de score muestran "Global", "Internal", "Combined" en gris



Los tooltips de scores aparecen al hover



El botón ★ guarda/quita bookmarks



El chip "Nuevo" aparece en papers recientes



El panel de notas se abre/cierra con animación



Los atajos de teclado funcionan (/, j, k, s, n, Esc, ?)



El botón Exportar descarga un CSV



El radar muestra labels en las esquinas, no tapados



El zoom por cuadrante funciona al hacer click en un label



El heatmap tiene paginación



El timeline muestra papers por semana



Cross-highlight funciona entre scatter y heatmap



La web es responsive (probar a 600px de ancho)



Todos los colores siguen la paleta slate definida



No hay emojis innecesarios (solo 📥, 📝, 🔒, ★/☆)



manifest.json y sw.js se generaron correctamente



add_user.py y generate_feed.py se generaron correctamente

