"""Experiment-only transport observability; request contract matches the frozen client."""
from dataclasses import dataclass, field
from datetime import datetime, timezone
import json
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from actionmail.reasoning.api_client import APIClient, MAX_OUTPUT_TOKENS, ModelCallError
from actionmail.reasoning.model_client import ModelReply


def utc_now():
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class ObservedAPIClient(APIClient):
    """Adds logs without changing messages, parameters, retries or parsing policy."""
    accounting: object = field(default=None, repr=False, compare=False)

    def complete(self, system_prompt, user_prompt):
        payload = {'model': self.model, 'messages': [
            {'role': 'system', 'content': system_prompt},
            {'role': 'user', 'content': user_prompt}],
            'temperature': 0, 'max_tokens': MAX_OUTPUT_TOKENS}
        exchange = {'started_utc': utc_now(), 'endpoint': self.api_url,
                    'request_payload': payload, 'streaming': False,
                    'ttft_ms': None, 'ttft_note': 'Unavailable with non-streaming transport'}
        object.__setattr__(self, 'last_exchange', exchange)
        audit_started = self.accounting.audit_wall_ms if self.accounting else 0
        if self.accounting:
            exchange['billing_before'] = self.accounting.snapshot()
        request = Request(self.api_url, data=json.dumps(payload).encode('utf-8'),
                          headers={'Authorization': f'Bearer {self.api_key}',
                                   'Content-Type': 'application/json', 'Accept': 'application/json'}, method='POST')
        started = time.perf_counter()
        try:
            try:
                with urlopen(request, timeout=self.timeout_seconds) as response:
                    exchange['http_status'] = getattr(response, 'status', None)
                    raw = response.read().decode('utf-8')
                    exchange['raw_response_text'] = raw
                    result = json.loads(raw)
            except HTTPError as exc:
                exchange['http_status'] = exc.code
                raise ModelCallError(f'Model API returned HTTP {exc.code}') from exc
            except (URLError, TimeoutError) as exc:
                raise ModelCallError('Model API connection failed or timed out') from exc
            except (ValueError, UnicodeError) as exc:
                raise ModelCallError('Model API returned invalid JSON') from exc
            latency_ms = (time.perf_counter() - started) * 1000
            exchange['response_json'] = result
            try:
                if not isinstance(result, dict):
                    raise TypeError('response must be an object')
                content = result['choices'][0]['message']['content']
                if not isinstance(content, str) or not content.strip():
                    raise TypeError('content must be text')
                usage = result.get('usage') or {}
                if not isinstance(usage, dict):
                    usage = {}
                inp, out = usage.get('prompt_tokens'), usage.get('completion_tokens')
                return ModelReply(content, str(result.get('model') or self.model),
                                  inp if isinstance(inp, int) else None,
                                  out if isinstance(out, int) else None, latency_ms)
            except (KeyError, IndexError, TypeError) as exc:
                choices = result.get('choices') if isinstance(result, dict) else None
                choice = choices[0] if isinstance(choices, list) and choices else {}
                reason = choice.get('finish_reason') if isinstance(choice, dict) else None
                usage = result.get('usage') if isinstance(result, dict) else None
                tokens = usage.get('completion_tokens') if isinstance(usage, dict) else None
                details = f' (finish_reason={reason}, completion_tokens={tokens})' if reason is not None or tokens is not None else ''
                raise ModelCallError('Model API response has no text completion' + details) from exc
        finally:
            exchange.update(ended_utc=utc_now(), transport_wall_ms=(time.perf_counter() - started) * 1000)
            if self.accounting:
                from billing import counter_delta
                exchange['billing_after'] = self.accounting.snapshot()
                exchange['key_usage_delta_usd'] = counter_delta(exchange['billing_before'], exchange['billing_after'], 'key_usage_usd')
                exchange['accounting_wall_ms'] = self.accounting.audit_wall_ms - audit_started
                exchange['delta_status'] = 'Observed window delta; provisional per-turn attribution until generation/account reconciliation'
