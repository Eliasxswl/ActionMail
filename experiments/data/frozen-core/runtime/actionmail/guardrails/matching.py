"""Bounded lexical quote diagnostics, never fuzzy acceptance."""
import re
import json
from difflib import SequenceMatcher
from actionmail.guardrails.evidence import align_evidence_quote


def _normalized(text, soft_wraps):
    if soft_wraps:
        text = re.sub(r'=\r?\n', '', text)
    return re.sub(r'\s+', ' ', text).strip()


def _critical(text):
    numbers = re.findall(r'[$€£¥]?[+-]?\d+(?:[.,:/-]\d+)*(?:[a-zA-Z%]+)?', text)
    words = re.findall(r"\b(?:not|no|never|without|cannot|exclude\w*|USD|SGD|EUR|GBP|kg|mg|km|hours?|days?)\b|\b\w+n['’]t\b|[\u4e0d\u672a\u65e0]", text, re.I)
    return [v.casefold() for v in numbers], [v.casefold() for v in words]


def diagnose_quotes(content, sources, *, soft_wraps=False):
    try:
        payload = json.loads(content)
    except (ValueError, TypeError):
        return []
    quotes = []
    def visit(value):
        if isinstance(value, dict):
            if isinstance(value.get('source_id'), str) and isinstance(value.get('quote'), str):
                quotes.append((value['source_id'], value['quote']))
            for item in value.values(): visit(item)
        elif isinstance(value, list):
            for item in value: visit(item)
    visit(payload)
    diagnostics = []
    remaining_windows = 64
    for source_id, quote in list(dict.fromkeys(quotes))[:12]:
        if not quote.strip() or len(quote) > 2000:
            continue
        text = sources.get(source_id)
        if text is not None:
            aligned = align_evidence_quote(quote, text, allow_soft_wrap=soft_wraps)
            if aligned.strip() and aligned in text:
                continue
        candidates = []
        for sid, original in ([(source_id, text)] if text is not None else list(sources.items())[:16]):
            # Diagnostics stay within supplied sources. Scan bounded windows, not a whole corpus.
            for start in range(0, len(original), 8000):
                if remaining_windows <= 0:
                    break
                remaining_windows -= 1
                window = original[max(0, start - 2000):start + 10000]
                longest = SequenceMatcher(None, quote, window, autojunk=True).find_longest_match()
                if longest.size < 8:
                    continue
                estimate = max(0, longest.b - longest.a)
                region_start = max(0, estimate - 64)
                region = window[region_start:estimate + len(quote) + 128]
                blocks = [b for b in SequenceMatcher(None, quote, region, autojunk=False).get_matching_blocks() if b.size]
                if not blocks:
                    continue
                candidate = region[blocks[0].b:blocks[-1].b + blocks[-1].size]
                if not candidate or len(candidate) > 2200:
                    continue
                score = SequenceMatcher(None, _normalized(quote, soft_wraps), _normalized(candidate, soft_wraps), autojunk=False).ratio()
                if score < .70:
                    continue
                candidates.append({'source_id': sid, 'quote': candidate, 'text_similarity': round(score, 4),
                                   'high_similarity': score >= .85, 'critical_difference': _critical(quote) != _critical(candidate),
                                   'unique_in_source': original.count(candidate) == 1, 'auto_accepted': False})
        candidates.sort(key=lambda c: c['text_similarity'], reverse=True)
        unique = {(c['source_id'], c['quote']): c for c in candidates}
        diagnostics.append({'source_id': source_id, 'model_quote': quote, 'candidates': list(unique.values())[:3]})
    return diagnostics
