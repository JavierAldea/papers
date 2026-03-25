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
