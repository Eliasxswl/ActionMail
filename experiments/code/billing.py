"""Read-only OpenRouter accounting; never derives billed charges from token prices."""
from datetime import datetime, timezone
import json
import time
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


def numeric(value):
    return value if isinstance(value, (float, int)) and not isinstance(value, bool) else None


def counter_delta(before, after, name):
    a, b = numeric(before.get(name)), numeric(after.get(name))
    return b - a if a is not None and b is not None else None


class Accounting:
    def __init__(self, key, management_key=None):
        self._key, self._management_key = key, management_key
        self.audit_wall_ms = 0

    def get(self, path, management=False):
        key = self._management_key if management else self._key
        if not key:
            return {'available': False, 'error': 'management_key_not_configured'}
        started = time.perf_counter()
        try:
            request = Request('https://openrouter.ai/api/v1/' + path,
                              headers={'Authorization': 'Bearer ' + key, 'Accept': 'application/json'})
            with urlopen(request, timeout=10) as response:
                value = json.load(response)
            if not isinstance(value, dict) or not isinstance(value.get('data'), dict):
                return {'available': False, 'error': 'invalid_accounting_response'}
            return {'available': True, 'data': value['data']}
        except HTTPError as exc:
            return {'available': False, 'error': f'http_{exc.code}'}
        except (OSError, ValueError, UnicodeError):
            return {'available': False, 'error': 'accounting_connection_or_decode_failure'}
        finally:
            self.audit_wall_ms += (time.perf_counter() - started) * 1000

    def snapshot(self):
        key = self.get('key'); data = key.get('data', {})
        result = {'observed_utc': datetime.now(timezone.utc).isoformat(),
                  'key_usage_usd': numeric(data.get('usage')), 'key_byok_usage_usd': numeric(data.get('byok_usage')),
                  'key_error': key.get('error')}
        # The management endpoint is optional; only numeric credit fields are persisted.
        if self._management_key:
            credits = self.get('credits', management=True); data = credits.get('data', {})
            result.update(account_usage_usd=numeric(data.get('total_usage')),
                          account_total_credits_usd=numeric(data.get('total_credits')), credits_error=credits.get('error'))
            if result['account_usage_usd'] is not None and result['account_total_credits_usd'] is not None:
                result['account_remaining_usd'] = result['account_total_credits_usd'] - result['account_usage_usd']
        return result

    def generation(self, response_id):
        if not isinstance(response_id, str) or not response_id.startswith('gen-') or len(response_id) > 128:
            return {'available': False, 'error': 'missing_or_invalid_generation_id'}
        return self.get('generation?' + urlencode({'id': response_id}))

    def reconcile(self, folder, before, calls):
        generations = []
        for c in calls:
            raw = (c.get('transport') or {}).get('response_json') or {}
            raw = raw if isinstance(raw, dict) else {}
            record = self.generation(raw.get('id'))
            generations.append({'arm': c['arm'], 'case_id': c['case_id'], 'trial': c['trial'],
                                'call': c['call'], 'turn_id': c.get('turn_id'),
                                'response_id': raw.get('id'), 'observed_utc': datetime.now(timezone.utc).isoformat(), **record})
        with (folder / 'generations.jsonl').open('w', encoding='utf-8') as f:
            for record in generations: f.write(json.dumps(record, ensure_ascii=False) + '\n')
        after = self.snapshot()
        charged = [numeric(r.get('data', {}).get('total_cost')) for r in generations]
        known = [v for v in charged if v is not None]
        delta = counter_delta(before, after, 'key_usage_usd')
        account_delta = counter_delta(before, after, 'account_usage_usd')
        remaining_delta = counter_delta(before, after, 'account_remaining_usd')
        report = {'before': before, 'after': after, 'key_usage_delta_usd': delta,
                  'account_usage_delta_usd': account_delta,
                  'account_balance_decrease_usd': -remaining_delta if remaining_delta is not None else None,
                  'credits_added_usd': counter_delta(before, after, 'account_total_credits_usd'),
                  'generation_cost_known_sum_usd': sum(known), 'generation_cost_calls': len(known),
                  'missing_generation_cost_calls': len(calls) - len(known),
                  'key_delta_minus_generation_sum_usd': delta - sum(known) if delta is not None else None,
                  'reconciled': bool(delta is not None and len(known) == len(calls) and abs(delta - sum(known)) <= .000001),
                  'attribution': 'Counter delta is observed actual consumption in this time window. Concurrent use can contaminate attribution; isolated key required for experiment-only attribution.',
                  'settlement': 'A mismatch or missing record is pending, not replaced with token-price estimates. Reconcile later without new inference.',
                  'audit_wall_ms': self.audit_wall_ms}
        (folder / 'billing.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
        return report
