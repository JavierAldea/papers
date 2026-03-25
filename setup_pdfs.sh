#!/bin/bash
# setup_pdfs.sh — Crea carpetas para papers PAYWALL en pdfs/{rank}/
cd /Users/nomada/papers-page

echo "📂 Creando carpetas para papers PAYWALL..."

python3 -c "
import csv, os
with open('papers.csv', encoding='utf-8-sig') as f:
    for row in csv.DictReader(f):
        access = row.get('Access', '')
        rank = row.get('PaperRank', '').strip()
        title = row.get('Title', '')[:60]
        if 'PAYWALL' in access and rank:
            folder = f'pdfs/{rank}'
            if not os.path.exists(folder):
                os.makedirs(folder)
                with open(f'{folder}/README.txt', 'w') as r:
                    r.write(f'PaperRank: {rank}\nTitle: {title}\nDescarga el PDF aquí y nómbralo paper.pdf\n')
                print(f'  📁 Creada: {folder}/ → {title}')
            else:
                has_pdf = any(f.endswith('.pdf') for f in os.listdir(folder))
                status = '✅ PDF presente' if has_pdf else '⚠️  Sin PDF aún'
                print(f'  {status}: {folder}/ → {title}')
"

echo ""
echo "💡 Descarga los PDFs y ponlos en la carpeta correspondiente (nombra cada uno paper.pdf)"
