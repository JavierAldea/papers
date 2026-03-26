import csv, json, re, time, math, argparse, datetime as dt
from pathlib import Path
from typing import List, Dict, Any, Iterable

import requests

VALID_DOMAINS = {
    'Brewing & Process',
    'Byproducts & Circularity',
    'Materials & Packaging',
    'Water & Environment',
    'Biotech applied',
    'Analytics & Digital',
    'Neuroscience & Functional',
}
PAPERS_HEADER = [
    'Title','DateAdded','PaperRank','Domain','Authors','Year','DOI','PrimaryURL','Access','AbstractMini','WhyRelevant','Owner'
]
USER_AGENT = 'watch-agent/0.1 (technology watch workflow)'

DOMAIN_HINTS = {
    'Brewing & Process': ['beer','brewing','brewery','wort','hops','yeast','fermentation','non-alcoholic beer','dealcoholization'],
    'Byproducts & Circularity': ['spent grain','spent yeast','by-product','waste valorization','upcycling','circular','anaerobic digestion','bioenergy'],
    'Materials & Packaging': ['packaging','film','polymer','bottle','can coating','barrier','biodegradable','active packaging','smart packaging'],
    'Water & Environment': ['wastewater','effluent','water reuse','COD','BOD','microalgae','treatment','resource recovery'],
    'Biotech applied': ['biotechnology','enzyme','microbial','bioprocess','precision fermentation','lactic fermentation','biocatalysis'],
    'Analytics & Digital': ['sensor','digital twin','machine learning','artificial intelligence','spectroscopy','monitoring','chemometrics','IoT'],
    'Neuroscience & Functional': ['functional beverage','bioactive','gut-brain','sleep','cognition','mood','probiotic','nootropic','digestive comfort'],
}


def now_str() -> str:
    return dt.datetime.now().strftime('%d/%m/%Y %H:%M')


def normalize_title(title: str) -> str:
    t = title.lower()
    t = re.sub(r'[^a-z0-9]+', ' ', t)
    return re.sub(r'\s+', ' ', t).strip()


def truncate(text: str, limit: int) -> str:
    text = re.sub(r'\s+', ' ', text or '').strip()
    if len(text) <= limit:
        return text
    cut = text[:limit-1].rsplit(' ', 1)[0].rstrip(' ,;:.-')
    return cut + '.'


def clean_abstract(text: str) -> str:
    text = re.sub(r'<[^>]+>', ' ', text or '')
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def json_array_str(items: List[str]) -> str:
    return json.dumps(items, ensure_ascii=False)


def ensure_papers_file(path: Path) -> None:
    if not path.exists():
        with path.open('w', newline='', encoding='utf-8') as f:
            csv.writer(f).writerow(PAPERS_HEADER)


def load_existing(path: Path):
    ensure_papers_file(path)
    with path.open(newline='', encoding='utf-8') as f:
        rows = list(csv.DictReader(f))
    dois = {r['DOI'].strip().lower() for r in rows if r.get('DOI')}
    urls = {r['PrimaryURL'].strip().lower() for r in rows if r.get('PrimaryURL')}
    titles = {normalize_title(r['Title']) for r in rows if r.get('Title')}
    return dois, urls, titles


def load_watchtags(path: Path) -> List[Dict[str, Any]]:
    with path.open(newline='', encoding='utf-8-sig') as f:
        rows = list(csv.DictReader(f))
    active = [r for r in rows if (r.get('Active','').strip().lower() == 'yes' and 'paper' in r.get('EvidenceType','').lower())]
    today = dt.date.today()
    for r in active:
        try:
            last = dt.date.fromisoformat((r.get('LastReviewed') or '1900-01-01').strip())
        except Exception:
            last = dt.date(1900,1,1)
        tag = int(r.get('TagScore') or 0)
        cadence = int(r.get('CadenceDays') or 9999)
        recency = int(r.get('RecencyDays') or 9999)
        overdue = max((today - last).days - cadence, 0)
        r['_priority'] = (tag * 5) + (overdue * 2) + max(0, 30 - min(recency, 30))
        r['_last'] = last.isoformat()
    active.sort(key=lambda r: (-r['_priority'], r['_last']))
    return active


def build_query(tag: Dict[str, str]) -> str:
    bits = []
    for field in ['MustInclude', 'Synonyms']:
        val = (tag.get(field) or '').strip()
        if val:
            bits.extend([x.strip() for x in val.split(';') if x.strip()])
    query = ' '.join(dict.fromkeys(bits))
    return query[:220]


def search_crossref(query: str, rows: int = 8) -> List[Dict[str, Any]]:
    url = 'https://api.crossref.org/works'
    params = {
        'query': query,
        'filter': 'from-pub-date:2026-01-01,until-pub-date:2026-12-31,type:journal-article',
        'rows': rows,
        'select': 'title,DOI,URL,author,published-print,published-online,abstract,subject,container-title,license'
    }
    r = requests.get(url, params=params, headers={'User-Agent': USER_AGENT}, timeout=30)
    r.raise_for_status()
    return r.json()['message']['items']


def search_europepmc(query: str, rows: int = 8) -> List[Dict[str, Any]]:
    url = 'https://www.ebi.ac.uk/europepmc/webservices/rest/search'
    params = {'query': f'({query}) AND PUB_YEAR:2026', 'format': 'json', 'pageSize': rows, 'resultType': 'core'}
    r = requests.get(url, params=params, headers={'User-Agent': USER_AGENT}, timeout=30)
    r.raise_for_status()
    return r.json().get('resultList', {}).get('result', [])


def crossref_to_candidate(item: Dict[str, Any], tag: Dict[str, str]) -> Dict[str, Any] | None:
    title = ((item.get('title') or ['']) or [''])[0].strip()
    doi = (item.get('DOI') or '').strip()
    if not title or not doi:
        return None
    year = '2026'
    authors = '; '.join(' '.join(x for x in [a.get('given','').strip(), a.get('family','').strip()] if x) for a in item.get('author', []))
    abstract = clean_abstract(item.get('abstract', ''))
    subjects = ' '.join(item.get('subject') or [])
    domains = infer_domains(' '.join([title, abstract, subjects, tag.get('Domain',''), tag.get('Title','')]))
    access = ['OPEN'] if item.get('license') else ['PAYWALL']
    return {
        'Title': title,
        'Year': year,
        'DOI': doi,
        'PrimaryURL': f'https://doi.org/{doi}',
        'Authors': authors,
        'Domain': domains,
        'Access': access,
        'AbstractMini': truncate(abstract or title, 300),
        'WhyRelevant': truncate(build_relevance(title, abstract, domains, tag), 200),
        'Owner': ''
    }


def epmc_to_candidate(item: Dict[str, Any], tag: Dict[str, str]) -> Dict[str, Any] | None:
    title = (item.get('title') or '').strip()
    doi = (item.get('doi') or '').strip()
    if not title or not doi:
        return None
    authors = '; '.join([x.strip() for x in (item.get('authorString') or '').replace(', et al', '').split(',') if x.strip()])
    abstract = clean_abstract(item.get('abstractText') or '')
    domains = infer_domains(' '.join([title, abstract, tag.get('Domain',''), tag.get('Title','')]))
    access = ['OPEN'] if str(item.get('isOpenAccess','N')).upper().startswith('Y') else ['PAYWALL']
    return {
        'Title': title,
        'Year': '2026',
        'DOI': doi,
        'PrimaryURL': f'https://doi.org/{doi}',
        'Authors': authors,
        'Domain': domains,
        'Access': access,
        'AbstractMini': truncate(abstract or title, 300),
        'WhyRelevant': truncate(build_relevance(title, abstract, domains, tag), 200),
        'Owner': ''
    }


def infer_domains(text: str) -> List[str]:
    t = text.lower()
    scored = []
    for domain, hints in DOMAIN_HINTS.items():
        hits = sum(1 for h in hints if h in t)
        if hits:
            scored.append((hits, domain))
    scored.sort(reverse=True)
    domains = [d for _, d in scored[:2]]
    if not domains:
        domains = ['Biotech applied']
    return domains


def build_relevance(title: str, abstract: str, domains: List[str], tag: Dict[str, str]) -> str:
    if 'Brewing & Process' in domains:
        return 'Potentially relevant to brewing operations, product quality or NOLO process design with signals that may translate into industrial trials.'
    if 'Materials & Packaging' in domains:
        return 'Relevant to packaging innovation and sustainability scouting, especially where functionality, barrier performance or intelligent monitoring are involved.'
    if 'Water & Environment' in domains:
        return 'Relevant to brewery water strategy because it links effluent treatment or resource recovery to operational and environmental performance.'
    if 'Neuroscience & Functional' in domains:
        return 'Relevant to functional beverage innovation because it informs ingredient delivery, physiological mechanisms or consumer-perceived benefit design.'
    return 'Relevant to the watchlist because it aligns with active tags in WatchTags and may inform near-term R&D prioritization.'


def candidate_quality(c: Dict[str, Any], tag: Dict[str, str]) -> float:
    score = float(tag.get('_priority', 0))
    score += 8 if c['Access'] == ['OPEN'] else 0
    score += 6 if len(c['Authors'].split(';')) >= 2 else 0
    score += 10 if any(d == tag.get('Domain','').strip() for d in c['Domain']) else 0
    score += 4 if 'review' in c['AbstractMini'].lower() or 'review' in c['Title'].lower() else 0
    return score


def is_valid_candidate(c: Dict[str, Any]) -> bool:
    if c['Year'] != '2026':
        return False
    if not c['Title'] or not c['DOI'] or not c['PrimaryURL'] or not c['Authors']:
        return False
    if c['PrimaryURL'] != f"https://doi.org/{c['DOI']}":
        return False
    if any(d not in VALID_DOMAINS for d in c['Domain']):
        return False
    if len(c['AbstractMini']) > 300 or len(c['WhyRelevant']) > 200:
        return False
    return True


def append_rows(papers_path: Path, candidates: Iterable[Dict[str, Any]]) -> int:
    dois, urls, titles = load_existing(papers_path)
    appended = 0
    with papers_path.open('a', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        for c in candidates:
            norm = normalize_title(c['Title'])
            if c['DOI'].lower() in dois or c['PrimaryURL'].lower() in urls or norm in titles:
                continue
            w.writerow([
                c['Title'], now_str(), '', json_array_str(c['Domain']), c['Authors'], c['Year'], c['DOI'], c['PrimaryURL'],
                json_array_str(c['Access']), c['AbstractMini'], c['WhyRelevant'], c['Owner']
            ])
            appended += 1
            dois.add(c['DOI'].lower())
            urls.add(c['PrimaryURL'].lower())
            titles.add(norm)
    return appended


def choose_balanced(candidates: List[Dict[str, Any]], top_n: int) -> List[Dict[str, Any]]:
    selected, domain_counts = [], {}
    for c in sorted(candidates, key=lambda x: x['_score'], reverse=True):
        main = c['Domain'][0]
        if domain_counts.get(main, 0) >= math.ceil(top_n / 3):
            continue
        selected.append(c)
        domain_counts[main] = domain_counts.get(main, 0) + 1
        if len(selected) >= top_n:
            break
    if len(selected) < top_n:
        seen = {c['DOI'] for c in selected}
        for c in sorted(candidates, key=lambda x: x['_score'], reverse=True):
            if c['DOI'] in seen:
                continue
            selected.append(c)
            seen.add(c['DOI'])
            if len(selected) >= top_n:
                break
    return selected


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--watchtags', default='WatchTags.csv')
    ap.add_argument('--papers', default='papers_raw.csv')
    ap.add_argument('--top-tags', type=int, default=20)
    ap.add_argument('--daily-target', type=int, default=10)
    ap.add_argument('--sleep', type=float, default=0.2)
    args = ap.parse_args()

    watchtags = load_watchtags(Path(args.watchtags))[:args.top_tags]
    all_candidates: List[Dict[str, Any]] = []
    seen_dois = set()

    for tag in watchtags:
        query = build_query(tag)
        if not query:
            continue
        for source in ('crossref', 'europepmc'):
            try:
                raw = search_crossref(query) if source == 'crossref' else search_europepmc(query)
            except Exception:
                continue
            for item in raw:
                cand = crossref_to_candidate(item, tag) if source == 'crossref' else epmc_to_candidate(item, tag)
                if not cand or not is_valid_candidate(cand):
                    continue
                if cand['DOI'].lower() in seen_dois:
                    continue
                cand['_score'] = candidate_quality(cand, tag)
                all_candidates.append(cand)
                seen_dois.add(cand['DOI'].lower())
            time.sleep(args.sleep)

    chosen = choose_balanced(all_candidates, args.daily_target)
    appended = append_rows(Path(args.papers), chosen)
    print(json.dumps({'found_candidates': len(all_candidates), 'selected': len(chosen), 'appended': appended}, ensure_ascii=False))

if __name__ == '__main__':
    main()
