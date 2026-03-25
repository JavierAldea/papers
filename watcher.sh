#!/bin/bash
# Vigila papers.csv en esta carpeta.
# Cuando detecta un cambio, hace commit y push automáticamente a GitHub Pages.

REPO="$(cd "$(dirname "$0")" && pwd)"
CSV="$REPO/papers.csv"

echo "👁  Vigilando: $CSV"
echo "    Cada vez que guardes el CSV, la web se actualizará sola."
echo "    Pulsa Ctrl+C para detener."
echo ""

fswatch -0 "$CSV" | while IFS= read -r -d "" _event; do
  echo "$(date '+%H:%M:%S')  Cambio detectado — subiendo a GitHub..."
  cd "$REPO"
  git add papers.csv
  git commit -m "Actualizar papers — $(date '+%d/%m/%Y %H:%M')"
  git push
  echo "$(date '+%H:%M:%S')  ✓ Listo. Web actualizada en ~30 segundos."
  echo ""
done
