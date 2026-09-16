"""Chrome learning console for ANNE.

The browser is only ANNE's human-facing communication surface. Model inference
is delegated to an existing ANNE provider; Ollama is never selected implicitly.
The response exposes a compact learning/decision report so a human can review
what ANNE learned before treating it as durable knowledge.
"""
from __future__ import annotations

import asyncio
import heapq
import os
import threading
from concurrent.futures import Future
from dataclasses import dataclass, field
from typing import Any

try:
    from fastapi import FastAPI, HTTPException
    from fastapi.responses import HTMLResponse
    from pydantic import BaseModel, Field
except ImportError as exc:  # pragma: no cover
    raise RuntimeError(
        "Web Tinker requires the API extras: python -m pip install -e '.[api]'"
    ) from exc

from anne.agent.offline import create_offline_agent
from anne.providers.gemini import GeminiProvider
from anne.providers.openrouter import OpenRouterProvider

PUBLIC_PRIORITY = 10
PRIORITY_OWNER = 0
DEFAULT_MAX_QUEUE = 32


@dataclass(order=True)
class _QueuedRequest:
    priority: int
    sequence: int
    future: Future[Any] = field(compare=False)
    prompt: str = field(compare=False)


class QueueFullError(RuntimeError):
    """Raised when the bounded queue is full."""


class ProviderConfigurationError(RuntimeError):
    """Raised when no supported web inference provider is configured."""


def _create_agent():
    provider = os.getenv("ANNE_WEB_PROVIDER", "").strip().lower()
    db_path = os.getenv("ANNE_WEB_DB", "anne_web.db")

    if provider == "openrouter":
        return __import__("anne.agent.runtime", fromlist=["AnneAgent"]).AnneAgent(
            model=OpenRouterProvider(),
            memory=__import__("anne.memory.local_memory", fromlist=["LocalMemory"]).LocalMemory(db_path),
        )
    if provider == "gemini":
        return __import__("anne.agent.runtime", fromlist=["AnneAgent"]).AnneAgent(
            model=GeminiProvider(),
            memory=__import__("anne.memory.local_memory", fromlist=["LocalMemory"]).LocalMemory(db_path),
        )
    raise ProviderConfigurationError(
        "ANNE_WEB_PROVIDER must be 'openrouter' or 'gemini'. "
        "Ollama/local inference is intentionally not used by the web console."
    )


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

    def submit(self, prompt: str, *, priority: int = PUBLIC_PRIORITY) -> Future[Any]:
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
            heapq.heappush(self._heap, _QueuedRequest(priority, self._sequence, future, prompt))
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
        agent = None
        while True:
            with self._condition:
                while not self._heap and not self._stopping:
                    self._condition.wait()
                if self._stopping and not self._heap:
                    return
                request = heapq.heappop(self._heap)
                self._busy = True
            try:
                if agent is None:
                    agent = _create_agent()
                result = agent.run(request.prompt)
                request.future.set_result(result)
            except Exception as exc:  # noqa: BLE001 - returned at HTTP boundary
                request.future.set_exception(exc)
            finally:
                with self._condition:
                    self._busy = False


class ChatRequest(BaseModel):
    prompt: str = Field(min_length=1, max_length=8000)


class ChatResponse(BaseModel):
    response: str
    learning: str = "No new durable learning."
    confidence: float = 0.0
    verification: dict[str, Any] = Field(default_factory=dict)
    tools_used: list[str] = Field(default_factory=list)


MAX_QUEUE = int(os.getenv("ANNE_WEB_MAX_QUEUE", str(DEFAULT_MAX_QUEUE)))
runtime = PriorityRuntime(max_queue=MAX_QUEUE)
app = FastAPI(title="ANNE Learning Console", version="0.2.0")


HTML = """<!doctype html>
<html lang="tr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>ANNE AI — Learning Console</title>
<style>
body{font-family:system-ui,sans-serif;max-width:980px;margin:0 auto;padding:20px;background:#f5f6f8;color:#17202a}
main{background:#fff;border:1px solid #ddd;border-radius:18px;padding:20px;box-shadow:0 8px 30px #0001}
#chat{height:430px;overflow:auto;border:1px solid #ddd;border-radius:12px;padding:14px;white-space:pre-wrap}
.msg{margin:0 0 16px}.who{font-weight:700}.anne{background:#f1f3f5;padding:10px;border-radius:10px}
textarea{width:100%;box-sizing:border-box;border:1px solid #bbb;border-radius:12px;padding:12px;font:inherit;margin-top:12px}
button{margin-top:10px;padding:10px 18px;border:0;border-radius:10px;cursor:pointer}.report{margin-top:14px;border:1px solid #ddd;border-radius:12px;padding:14px;background:#fafafa}
.small{font-size:.9rem;color:#667085}.warn{color:#8a5a00}
</style></head><body><main>
<h1>ANNE AI</h1><p class="small">Learning Console · Chrome yalnızca iletişim arayüzüdür; çıkarım ANNE'nin provider katmanından gelir.</p>
<div id="chat"><div class="msg anne"><span class="who">ANNE</span><br>Merhaba. Ben ANNE AI. Bana bir konu ver; araştırma, değerlendirme ve öğrenme döngümü birlikte test edelim.</div></div>
<textarea id="prompt" rows="4" placeholder="ANNE'ye mesaj yaz..."></textarea><button onclick="send()">Gönder</button>
<div id="report" class="report small">Yönetici özeti ve edinilmek istenen fayda, her yanıtla burada görünecek.</div>
</main><script>
const esc=s=>String(s).replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;');
async function send(){const p=document.getElementById('prompt'),c=document.getElementById('chat'),rpt=document.getElementById('report');const prompt=p.value.trim();if(!prompt)return;
c.innerHTML+=`<div class="msg"><span class="who">SEN</span><br>${esc(prompt)}</div>`;p.value='';rpt.textContent='ANNE çalışıyor...';
try{const r=await fetch('/chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({prompt})});const d=await r.json();if(!r.ok)throw new Error(d.detail||'İstek başarısız');
c.innerHTML+=`<div class="msg anne"><span class="who">ANNE</span><br>${esc(d.response)}</div>`;
rpt.innerHTML=`<b>YÖNETİCİ ÖZETİ</b><br>${esc(d.response)}<br><br><b>EDİNİLMEK İSTENEN FAYDA</b><br>${esc(d.learning)}<br><br><b>GÜVEN</b>: ${Number(d.confidence).toFixed(2)}<br><b>DOĞRULAMA</b>: ${esc(JSON.stringify(d.verification))}<br><b>ARAÇLAR</b>: ${esc((d.tools_used||[]).join(', ')||'Yok')}`;
c.scrollTop=c.scrollHeight;}catch(e){rpt.innerHTML='<span class="warn">'+esc(e.message)+'</span>';}}
</script></body></html>"""


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    return HTML


@app.get("/health")
def health() -> dict[str, Any]:
    provider = os.getenv("ANNE_WEB_PROVIDER", "not configured")
    return {"status": "ok", "runtime": "anne-learning-console", "provider": provider, **runtime.snapshot()}


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    future = runtime.submit(request.prompt, priority=PUBLIC_PRIORITY)
    try:
        result = await asyncio.wrap_future(future)
    except QueueFullError as exc:
        raise HTTPException(status_code=429, detail=str(exc)) from exc
    except ProviderConfigurationError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001 - safe server boundary
        raise HTTPException(status_code=503, detail=f"ANNE runtime unavailable: {exc}") from exc
    return ChatResponse(
        response=result.response,
        learning=result.learning,
        confidence=result.confidence,
        verification=result.verification,
        tools_used=result.tools_used,
    )


@app.on_event("shutdown")
def shutdown() -> None:
    runtime.stop()


__all__ = ["app", "PriorityRuntime", "PRIORITY_OWNER", "PUBLIC_PRIORITY"]
