"""Small, laptop-first web Tinker for ANNE.

The server keeps the model local. Public requests use a bounded FIFO queue at
normal priority; reserved owner/test identities can later use the priority-0
lane once the identity layer is added. No public HTTP field is trusted to
claim priority.
"""
from __future__ import annotations

import asyncio
import heapq
import os
import threading
import time
from concurrent.futures import Future
from dataclasses import dataclass, field
from typing import Any

try:
    from fastapi import FastAPI, HTTPException
    from fastapi.responses import HTMLResponse
    from pydantic import BaseModel, Field
except ImportError as exc:  # pragma: no cover - exercised by installation checks
    raise RuntimeError(
        "Web Tinker requires the API extras: python -m pip install -e '.[api]'"
    ) from exc

from anne.agent.offline import create_offline_agent


PUBLIC_PRIORITY = 10
PRIORITY_OWNER = 0
DEFAULT_MAX_CONCURRENCY = 1
DEFAULT_MAX_QUEUE = 32


@dataclass(order=True)
class _QueuedRequest:
    priority: int
    sequence: int
    future: Future[str] = field(compare=False)
    prompt: str = field(compare=False)


class PriorityRuntime:
    """One bounded worker for a laptop-hosted ANNE runtime."""

    def __init__(self, *, max_concurrency: int = 1, max_queue: int = 32) -> None:
        if max_concurrency != 1:
            raise ValueError("the initial laptop runtime supports one model worker")
        if max_queue < 1:
            raise ValueError("max_queue must be positive")
        self.max_queue = max_queue
        self._condition = threading.Condition()
        self._heap: list[_QueuedRequest] = []
        self._sequence = 0
        self._stopping = False
        self._busy = False
        self._worker = threading.Thread(target=self._run, name="anne-model-worker", daemon=True)
        self._worker.start()

    def submit(self, prompt: str, *, priority: int = PUBLIC_PRIORITY) -> Future[str]:
        if priority < PRIORITY_OWNER:
            raise ValueError("invalid priority")
        future: Future[str] = Future()
        with self._condition:
            if self._stopping:
                future.set_exception(RuntimeError("ANNE runtime is stopping"))
                return future
            if len(self._heap) >= self.max_queue:
                future.set_exception(QueueFullError("ANNE is busy; the request queue is full"))
                return future
            self._sequence += 1
            heapq.heappush(
                self._heap,
                _QueuedRequest(priority, self._sequence, future, prompt),
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
                    agent = create_offline_agent(
                        model=os.getenv("ANNE_LOCAL_MODEL", "qwen2.5:3b"),
                        backend=os.getenv("ANNE_LOCAL_BACKEND", "ollama"),
                        endpoint=os.getenv("ANNE_LOCAL_ENDPOINT"),
                        db_path=os.getenv("ANNE_WEB_DB", "anne_web.db"),
                    )
                result = agent.run(request.prompt)
                request.future.set_result(result.response)
            except Exception as exc:  # noqa: BLE001 - returned to the HTTP caller
                request.future.set_exception(exc)
            finally:
                with self._condition:
                    self._busy = False


class QueueFullError(RuntimeError):
    """Raised when the bounded laptop queue cannot accept another public request."""


class ChatRequest(BaseModel):
    prompt: str = Field(min_length=1, max_length=8000)


class ChatResponse(BaseModel):
    response: str
    queued: bool = False


MAX_QUEUE = int(os.getenv("ANNE_WEB_MAX_QUEUE", str(DEFAULT_MAX_QUEUE)))
runtime = PriorityRuntime(max_concurrency=1, max_queue=MAX_QUEUE)
app = FastAPI(title="ANNE Web Tinker", version="0.1.0")


HTML = """<!doctype html>
<html lang="tr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>ANNE AI — Tinker</title>
<style>
body{font-family:system-ui,sans-serif;max-width:900px;margin:0 auto;padding:24px;background:#f6f7f9;color:#17202a}
main{background:white;border:1px solid #ddd;border-radius:18px;padding:22px;box-shadow:0 8px 30px #0000000d}
h1{margin-top:0}#chat{min-height:360px;white-space:pre-wrap;border:1px solid #ddd;border-radius:12px;padding:14px;margin-bottom:12px;overflow:auto}
textarea{width:100%;box-sizing:border-box;border:1px solid #bbb;border-radius:12px;padding:12px;font:inherit}button{margin-top:10px;padding:10px 18px;border:0;border-radius:10px;cursor:pointer}
.small{font-size:.9rem;color:#667085}
</style></head>
<body><main><h1>ANNE AI</h1><p class="small">Laptop-first ücretsiz araştırma Tinker'ı · kapasite sınırlıdır.</p>
<div id="chat">ANNE: Merhaba. Sorunu yazabilirsin.</div>
<textarea id="prompt" rows="5" placeholder="ANNE'ye bir şey sor..."></textarea><br>
<button onclick="send()">Gönder</button><p id="status" class="small"></p></main>
<script>
async function send(){const p=document.getElementById('prompt'),c=document.getElementById('chat'),s=document.getElementById('status');
const prompt=p.value.trim();if(!prompt)return;c.textContent+='\\n\\nSEN: '+prompt;p.value='';s.textContent='ANNE düşünüyor...';
try{const r=await fetch('/chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({prompt})});
const d=await r.json();if(!r.ok)throw new Error(d.detail||'İstek başarısız');c.textContent+='\\n\\nANNE: '+d.response;s.textContent='Hazır.';}
catch(e){c.textContent+='\\n\\nSİSTEM: '+e.message;s.textContent='';}}
</script></body></html>"""


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    return HTML


@app.get("/health")
def health() -> dict[str, Any]:
    return {"status": "ok", "runtime": "laptop-local", **runtime.snapshot()}


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    # Public HTTP callers never choose priority. Identity-aware priority will be
    # added by the future central identity layer.
    future = runtime.submit(request.prompt, priority=PUBLIC_PRIORITY)
    try:
        response = await asyncio.wrap_future(future)
    except QueueFullError as exc:
        raise HTTPException(status_code=429, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001 - safe server boundary
        raise HTTPException(status_code=503, detail=f"ANNE runtime unavailable: {exc}") from exc
    return ChatResponse(response=response)


@app.on_event("shutdown")
def shutdown() -> None:
    runtime.stop()


__all__ = ["app", "PriorityRuntime", "PRIORITY_OWNER", "PUBLIC_PRIORITY"]
