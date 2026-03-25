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
