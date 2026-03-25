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
