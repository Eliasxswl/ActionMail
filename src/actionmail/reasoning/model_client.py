from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class ModelReply:
    content: str
    model: str
    input_tokens: int | None = None
    output_tokens: int | None = None
    latency_ms: float | None = None


class ModelClient(Protocol):
    def complete(self, system_prompt: str, user_prompt: str) -> ModelReply: ...
