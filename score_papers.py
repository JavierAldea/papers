#!/usr/bin/env python3
"""
score_papers.py — Recalcula GlobalScore, InternalScore y CombinedScore
para cada paper cruzándolo con WatchTags.csv.

USO:
  python3 score_papers.py

LEE:
  papers_raw.csv   ← tu CSV de siempre (12 columnas)
  WatchTags.csv    ← tus antenas/dominios de interés

ESCRIBE:
  papers.csv       ← CSV final con 17 columnas (el que consume la web)

Flujo pensado para el watcher:
  1. Tú editas papers_raw.csv (añades/quitas papers)
  2. watcher.sh detecta el cambio
  3. watcher.sh ejecuta: python3 score_papers.py
  4. Se genera papers.csv con scores actualizados
  5. watcher.sh hace git add + commit + push
"""

import csv
import json
import re
import math
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
RAW_FILE = os.path.join(SCRIPT_DIR, "papers_raw.csv")
TAGS_FILE = os.path.join(SCRIPT_DIR, "WatchTags.csv")
OUT_FILE = os.path.join(SCRIPT_DIR, "papers.csv")


def read_csv(path):
    """Lee CSV manejando BOM y comillas."""
    with open(path, encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def parse_domains(val):
    """Parsea el campo Domain que viene como JSON array con comillas escapadas."""
    if not val or val.strip() == "":
        return []
    try:
        clean = val.replace('""', '"').strip('"')
        if clean.startswith("["):
            return json.loads(clean)
        return [clean]
    except:
        return [val.strip('"[] ')]


def extract_phrases(text):
    """Extrae frases de búsqueda separadas por ; o ,"""
    return [p.strip() for p in re.split(r"[;,]", text) if len(p.strip()) > 2]


def build_tag_index(tags):
    """Prepara las WatchTags con sus frases de búsqueda."""
    for tag in tags:
        blob_parts = []
        for col in ["Title", "Synonyms", "MustInclude", "Theme"]:
            if tag.get(col, "").strip():
                blob_parts.append(tag[col].lower())
        tag["_blob"] = " ".join(blob_parts)
        tag["_phrases"] = extract_phrases(tag["_blob"])
        tag["_score"] = int(tag.get("TagScore", 0))
        tag["_domain"] = tag.get("Domain", "")
    return tags


def calc_internal_score(paper_text, paper_domains, tags):
    """Calcula el InternalScore cruzando texto del paper con WatchTags."""
    matched = []
    total = 0.0

    for tag in tags:
        hits = [p for p in tag["_phrases"] if p in paper_text]
        if not hits:
            continue

        ratio = len(hits) / max(len(tag["_phrases"]), 1)
        strength = min(ratio * 2.5, 1.0)

        domain_match = tag["_domain"] in paper_domains if paper_domains else False
        if domain_match:
            strength = min(strength * 1.4, 1.0)

        weighted = strength * tag["_score"]
        total += weighted

        if strength > 0.05:
            matched.append({
                "tag": tag["Title"][:65],
                "domain": tag["_domain"],
                "theme": tag.get("Theme", ""),
                "strength": round(strength, 3),
                "tagScore": tag["_score"],
                "phrases": hits[:4],
                "domainMatch": domain_match,
            })

    matched.sort(key=lambda x: x["strength"] * x["tagScore"], reverse=True)
    return total, matched[:8], len(matched)


def calc_global_score(paper):
    """Calcula el GlobalScore basado en recencia, riqueza del abstract, etc."""
    s = 0.0

    # Recencia (45%)
    try:
        year = int(str(paper.get("Year", "0")).replace(".", "").replace(",", ""))
    except:
        year = 0
    if year >= 2026:
        s += 0.45 * 100
    elif year >= 2025:
        s += 0.45 * 80
    elif year >= 2024:
        s += 0.45 * 60
    else:
        s += 0.45 * 40

    # Riqueza del abstract (25%)
    abstract = paper.get("AbstractMini", "") or ""
    s += 0.25 * min(len(abstract) / 200, 1.0) * 100

    # Riqueza del WhyRelevant (18%)
    why = paper.get("WhyRelevant", "") or ""
    s += 0.18 * min(len(why) / 150, 1.0) * 100

    # Tiene owner (12%)
    owner = paper.get("Owner", "") or ""
    if owner.strip():
        s += 0.12 * 100

    return round(s, 1)


def main():
    # Verificar archivos
    if not os.path.exists(RAW_FILE):
        print(f"❌ No encuentro {RAW_FILE}")
        print(f"   Renombra tu papers.csv actual a papers_raw.csv")
        return

    if not os.path.exists(TAGS_FILE):
        print(f"❌ No encuentro {TAGS_FILE}")
        return

    # Leer datos
    papers = read_csv(RAW_FILE)
    tags = build_tag_index(read_csv(TAGS_FILE))

    print(f"📄 {len(papers)} papers leídos de papers_raw.csv")
    print(f"🏷️  {len(tags)} WatchTags leídos")

    # Calcular scores
    raw_internals = []
    paper_results = []

    for paper in papers:
        domains = parse_domains(paper.get("Domain", ""))

        # Texto para matching semántico
        text_parts = []
        for col in ["Title", "AbstractMini", "WhyRelevant"]:
            val = paper.get(col, "") or ""
            if val.strip():
                text_parts.append(val.lower())
        paper_text = " ".join(text_parts)

        int_raw, matched_tags, n_matches = calc_internal_score(paper_text, domains, tags)
        global_score = calc_global_score(paper)

        raw_internals.append(int_raw)
        paper_results.append({
            "int_raw": int_raw,
            "matched_tags": matched_tags,
            "n_matches": n_matches,
            "global_score": global_score,
        })

    # Normalizar InternalScore a 0-100
    max_raw = max(raw_internals) if raw_internals else 1
    min_raw = min(raw_internals) if raw_internals else 0
    spread = max_raw - min_raw if max_raw > min_raw else 1

    for r in paper_results:
        r["internal_score"] = round((r["int_raw"] - min_raw) / spread * 100, 1)
        g = r["global_score"]
        i = r["internal_score"]
        r["combined_score"] = round(math.sqrt(g * i), 1)

    # Escribir CSV de salida (12 columnas originales + 5 nuevas)
    original_fields = [
        "Title", "DateAdded", "PaperRank", "Domain", "Authors",
        "Year", "DOI", "PrimaryURL", "Access", "AbstractMini",
        "WhyRelevant", "Owner",
    ]
    new_fields = ["GlobalScore", "InternalScore", "CombinedScore", "TagMatches", "MatchedTags"]
    all_fields = original_fields + new_fields

    with open(OUT_FILE, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=all_fields, quoting=csv.QUOTE_ALL)
        writer.writeheader()

        for paper, result in zip(papers, paper_results):
            row = {}
            for col in original_fields:
                row[col] = paper.get(col, "")
            row["GlobalScore"] = result["global_score"]
            row["InternalScore"] = result["internal_score"]
            row["CombinedScore"] = result["combined_score"]
            row["TagMatches"] = result["n_matches"]
            row["MatchedTags"] = json.dumps(result["matched_tags"])
            writer.writerow(row)

    # Stats
    scores = paper_results
    avg_g = sum(r["global_score"] for r in scores) / len(scores)
    avg_i = sum(r["internal_score"] for r in scores) / len(scores)
    avg_c = sum(r["combined_score"] for r in scores) / len(scores)

    gold = sum(1 for r in scores if r["global_score"] >= avg_g and r["internal_score"] >= avg_i)

    print(f"\n✅ papers.csv generado con {len(papers)} papers × {len(all_fields)} columnas")
    print(f"   Global avg:   {avg_g:.1f}")
    print(f"   Internal avg: {avg_i:.1f}")
    print(f"   Combined avg: {avg_c:.1f}")
    print(f"   Gold papers:  {gold}")


if __name__ == "__main__":
    main()
