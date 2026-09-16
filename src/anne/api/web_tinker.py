"""Browser conversation surface for ANNE's cognitive learning loop.

Chrome is the human communication surface. ANNE owns the cognitive sequence.
Language models express ANNE's already-decided content only.
"""
from __future__ import annotations

import asyncio
import heapq
import json
import os
import threading
from concurrent.futures import Future
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.error import URLError
from urllib.request import Request, urlopen

try:
    from fastapi import FastAPI, HTTPException
    from fastapi.responses import HTMLResponse
    from pydantic import BaseModel, Field
except ImportError as exc:  # pragma: no cover
    raise RuntimeError(
        "Web Tinker requires the API extras: python -m pip install -e '.[api]'"
    ) from exc

from anne.api.console_html import CONSOLE_HTML
from anne.api.provider_factory import ProviderConfigurationError as FactoryProviderError
from anne.api.provider_factory import create_language_provider
from anne.core.conversation import CognitiveConversation, LanguageInterface
from anne.memory.local_memory import LocalMemory

PUBLIC_PRIORITY = 10
PRIORITY_OWNER = 0
DEFAULT_MAX_QUEUE = 32


def _load_local_config() -> None:
    path = Path.cwd() / "anne_config.env"
    if not path.is_file():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


_load_local_config()


@dataclass(order=True)
class _QueuedRequest:
    priority: int
    sequence: int
    future: Future[Any] = field(compare=False)
    actor: str = field(compare=False)
    prompt: str = field(compare=False)


class QueueFullError(RuntimeError):
    """Raised when the bounded queue is full."""


class ProviderConfigurationError(RuntimeError):
    """Raised when no supported language provider is configured."""


class ProviderLanguageInterface(LanguageInterface):
    """Adapt an existing provider to ANNE's language-only interface."""

    def __init__(self, provider: Any) -> None:
        self.provider = provider

    def express(self, content: str, *, language: str = "tr") -> str:
        prompt = (
            "Express the following content in natural Turkish. "
            "It is a message already decided by ANNE. Do not add facts, "
            "decisions, actions, tool calls, confidence, or learning. "
            "Preserve uncertainty exactly.\n\n"
            f"CONTENT:\n{content}"
        )
        return str(self.provider.ask(prompt)).strip()


class HTTPResearchAdapter:
    """Call an ANNE-controlled research service."""

    def __init__(self, url: str, source_name: str) -> None:
        self.url = url
        self.source_name = source_name

    def _call(self, question: str) -> dict[str, Any]:
        payload = json.dumps({"question": question}, ensure_ascii=False).encode()
        request = Request(
            self.url,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urlopen(request, timeout=30) as response:  # noqa: S310
                data = json.loads(response.read().decode("utf-8"))
        except (OSError, URLError, json.JSONDecodeError) as exc:
            return {"source": self.source_name, "ok": False, "error": str(exc)}
        return {"source": self.source_name, "ok": True, "data": data}

    def research(self, question: str) -> dict[str, Any]:
        return self._call(question)

    def ask(self, question: str, context: dict[str, Any]) -> dict[str, Any]:
        payload_question = f"{question}\n\nCONTEXT:\n{json.dumps(context, ensure_ascii=False)}"
        return self._call(payload_question)


def _create_conversation() -> tuple[CognitiveConversation, LocalMemory]:
    db_path = os.getenv("ANNE_WEB_DB", "anne_web.db")
    memory = LocalMemory(db_path)
    try:
        provider = create_language_provider()
    except FactoryProviderError as exc:
        raise ProviderConfigurationError(str(exc)) from exc

    research_url = os.getenv("ANNE_MITOS_URL", "").strip()
    research_http = os.getenv("ANNE_CHATGPT_URL", "").strip()
    research = HTTPResearchAdapter(research_url, "MITOS") if research_url else None
    consultation = HTTPResearchAdapter(research_http, "RESEARCH") if research_http else None
    conversation = CognitiveConversation(
        language=ProviderLanguageInterface(provider),
        research=research,
        consultation=consultation,
    )
    return conversation, memory


class PriorityRuntime:
    """Single bounded ANNE worker; priority is server-assigned."""

    def __init__(self, *, max_queue: int = DEFAULT_MAX_QUEUE) -> None:
        if max_queue < 1:
            raise ValueError("max_queue must be positive")
        self.max_queue = max_queue
        self._condition = threading.Condition()
        self._heap: list[_QueuedRequest] = []
        self._sequence = 0
        self._stopping = False
        self._busy = False
        self._worker = threading.Thread(target=self._run, name="anne-worker", daemon=True)
        self._worker.start()

    def submit(self, actor: str, prompt: str, *, priority: int = PUBLIC_PRIORITY) -> Future[Any]:
        if priority < PRIORITY_OWNER:
            raise ValueError("invalid priority")
        future: Future[Any] = Future()
        with self._condition:
            if self._stopping:
                future.set_exception(RuntimeError("ANNE runtime is stopping"))
                return future
            if len(self._heap) >= self.max_queue:
                future.set_exception(QueueFullError("ANNE is busy; request queue is full"))
                return future
            self._sequence += 1
            heapq.heappush(
                self._heap, _QueuedRequest(priority, self._sequence, future, actor, prompt)
            )
            self._condition.notify()
        return future

    def snapshot(self) -> dict[str, int | bool]:
        with self._condition:
            return {
                "busy": self._busy,
                "queued": len(self._heap),
                "max_queue": self.max_queue,
                "public_priority": PUBLIC_PRIORITY,
                "owner_priority": PRIORITY_OWNER,
            }

    def stop(self) -> None:
        with self._condition:
            self._stopping = True
            self._condition.notify_all()

    def _run(self) -> None:
        conversation = None
        memory = None
        while True:
            with self._condition:
                while not self._heap and not self._stopping:
                    self._condition.wait()
                if self._stopping and not self._heap:
                    return
                request = heapq.heappop(self._heap)
                self._busy = True
            try:
                if conversation is None or memory is None:
                    conversation, memory = _create_conversation()
                previous = memory.find_previous_answer(request.prompt)
                recent_experiences = memory.recent_experiences(limit=8)
                known_context = memory.context(limit=8)
                result = conversation.handle(
                    request.actor,
                    request.prompt,
                    known_context=known_context,
                    previous_answer=previous,
                    recent_experiences=recent_experiences,
                )
                confidence = result.audit.confidence if result.audit is not None else 0.5
                memory.save(request.prompt, result.answer, result.learned, confidence)
                if result.experience is not None:
                    memory.save_experience(result.experience)
                request.future.set_result(result)
            except Exception as exc:  # noqa: BLE001
                request.future.set_exception(exc)
            finally:
                with self._condition:
                    self._busy = False


class ChatRequest(BaseModel):
    prompt: str = Field(min_length=1, max_length=8000)
    actor: str = Field(default="GÖKHAN", min_length=1, max_length=80)


class ChatResponse(BaseModel):
    source: str = "ANNE"
    response: str
    manager_summary: str
    benefit: str
    learned: str
    evidence_count: int = 0
    changed_since_previous: bool = False
    comparison_status: str = "INSUFFICIENT"
    experience: dict[str, Any] = Field(default_factory=dict)
    research_required: bool = False
    previous_knowledge_found: bool = False
    confidence: float = 0.0
    knowledge_state: str = "none"
    research_reason: str = ""


MAX_QUEUE = int(os.getenv("ANNE_WEB_MAX_QUEUE", str(DEFAULT_MAX_QUEUE)))
runtime = PriorityRuntime(max_queue=MAX_QUEUE)
app = FastAPI(title="ANNE Cognitive Learning Console", version="0.5.0")


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    return CONSOLE_HTML


@app.get("/health")
def health() -> dict[str, Any]:
    provider = (os.getenv("ANNE_WEB_PROVIDER") or "").strip().lower()
    if provider in {"chatgpt"}:
        provider = "openai"
    if provider in {"grok"}:
        provider = "xai"
    key_ok = False
    if provider == "openai":
        key_ok = bool(os.getenv("OPENAI_API_KEY") or os.getenv("CHATGPT_API_KEY"))
    elif provider == "xai":
        key_ok = bool(os.getenv("XAI_API_KEY") or os.getenv("GROK_API_KEY"))
    elif provider == "openrouter":
        key_ok = bool(os.getenv("OPENROUTER_API_KEY"))
    elif provider == "gemini":
        key_ok = bool(os.getenv("GEMINI_API_KEY"))
    status = "ok" if (provider and key_ok) else "degraded"
    return {
        "status": status,
        "runtime": "anne-cognitive-learning-console",
        "cognitive": "CognitiveConversation",
        "provider": provider or "not configured",
        "provider_key_configured": key_ok,
        "memory_db": os.getenv("ANNE_WEB_DB", "anne_web.db"),
        "research_mitos": bool(os.getenv("ANNE_MITOS_URL", "").strip()),
        "research_http": bool(os.getenv("ANNE_CHATGPT_URL", "").strip()),
        "ollama_required": False,
        **runtime.snapshot(),
    }


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    future = runtime.submit(request.actor, request.prompt, priority=PUBLIC_PRIORITY)
    try:
        result = await asyncio.wrap_future(future)
    except QueueFullError as exc:
        raise HTTPException(status_code=429, detail=str(exc)) from exc
    except ProviderConfigurationError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=503, detail=f"ANNE runtime unavailable: {exc}") from exc
    experience = result.experience.__dict__ if result.experience is not None else {}
    audit = result.audit
    manager_summary = (
        f"Karşılaştırma: {result.comparison_status}. "
        f"Yeni kanıt: {result.current_evidence}. "
        f"Önceki bilgi değişti: {'evet' if result.changed_since_previous else 'hayır'}. "
        f"Bilişsel güven: {audit.confidence:.2f}. "
        f"Araştırma: {'gerekli' if audit.research_required else 'gerekli değil'}"
        if audit is not None
        else result.benefit
    )
    return ChatResponse(
        response=result.answer,
        manager_summary=manager_summary,
        benefit=result.benefit,
        learned=result.learned,
        evidence_count=result.current_evidence,
        changed_since_previous=result.changed_since_previous,
        comparison_status=result.comparison_status,
        experience=experience,
        research_required=bool(audit.research_required) if audit is not None else False,
        previous_knowledge_found=bool(audit.previous_knowledge_found)
        if audit is not None
        else False,
        confidence=float(audit.confidence) if audit is not None else 0.0,
        knowledge_state=str(audit.knowledge_state) if audit is not None else "none",
        research_reason=str(audit.research_reason) if audit is not None else "",
    )


@app.on_event("shutdown")
def shutdown() -> None:
    runtime.stop()


__all__ = ["app", "PriorityRuntime", "PRIORITY_OWNER", "PUBLIC_PRIORITY"]
