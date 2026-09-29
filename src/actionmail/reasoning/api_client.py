import json
import time
from dataclasses import dataclass, field
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from actionmail.reasoning.model_client import ModelReply


class ModelCallError(RuntimeError):
    pass


@dataclass(frozen=True)
class APIClient:
    api_url: str
    api_key: str = field(repr=False)
    model: str
    timeout_seconds: float = 30.0

    def __post_init__(self) -> None:
        parsed = urlparse(self.api_url)
        local_http = parsed.scheme == "http" and parsed.hostname == "127.0.0.1"
        if (parsed.scheme != "https" and not local_http) or not parsed.hostname or parsed.username or parsed.password:
            raise ValueError("api_url must use HTTPS or a local test server")
        if not self.api_key.strip():
            raise ValueError("api_key is required")
        if not self.model.strip():
            raise ValueError("model is required")

    def complete(self, system_prompt: str, user_prompt: str) -> ModelReply:
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0,
            "max_tokens": 800,
        }
        request = Request(
            self.api_url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            method="POST",
        )
        started = time.perf_counter()
        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                result = json.load(response)
        except HTTPError as exc:
            raise ModelCallError(f"Model API returned HTTP {exc.code}") from exc
        except (URLError, TimeoutError) as exc:
            raise ModelCallError("Model API connection failed or timed out") from exc
        except (ValueError, UnicodeError) as exc:
            raise ModelCallError("Model API returned invalid JSON") from exc
        latency_ms = (time.perf_counter() - started) * 1000

        try:
            if not isinstance(result, dict):
                raise TypeError("response must be an object")
            content = result["choices"][0]["message"]["content"]
            if not isinstance(content, str) or not content.strip():
                raise TypeError("content must be text")
            usage = result.get("usage") or {}
            if not isinstance(usage, dict):
                usage = {}
            input_tokens = usage.get("prompt_tokens")
            output_tokens = usage.get("completion_tokens")
            return ModelReply(
                content=content,
                model=str(result.get("model") or self.model),
                input_tokens=input_tokens if isinstance(input_tokens, int) else None,
                output_tokens=output_tokens if isinstance(output_tokens, int) else None,
                latency_ms=latency_ms,
            )
        except (KeyError, IndexError, TypeError) as exc:
            choices = result.get("choices") if isinstance(result, dict) else None
            choice = choices[0] if isinstance(choices, list) and choices else {}
            reason = choice.get("finish_reason") if isinstance(choice, dict) else None
            usage = result.get("usage") if isinstance(result, dict) else None
            tokens = usage.get("completion_tokens") if isinstance(usage, dict) else None
            details = f" (finish_reason={reason}, completion_tokens={tokens})" if reason is not None or tokens is not None else ""
            raise ModelCallError("Model API response has no text completion" + details) from exc
