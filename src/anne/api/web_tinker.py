"""Browser conversation surface for ANNE's cognitive learning loop.

Chrome is only the human communication surface. ANNE owns the cognitive
sequence. Language models express ANNE's already-decided content; they do not
select tools, make decisions, or generate ANNE's learning records.

External research and consultation are explicit adapters configured by ANNE,
not model tool-calls. MITOS can be connected through ANNE_MITOS_URL and an
external ChatGPT-compatible consultation service through ANNE_CHATGPT_URL.
"""
from __future__ import annotations

import asyncio
import heapq
import json
import os
import threading
from concurrent.futures import Future
from dataclasses import dataclass, field
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

from anne.core.conversation import CognitiveConversation, LanguageInterface
from anne.memory.local_memory import LocalMemory
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
    """Call an ANNE-controlled research service such as MITOS."""

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
            with urlopen(request, timeout=30) as response:  # noqa: S310 - configured endpoint
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
    provider_name = os.getenv("ANNE_WEB_PROVIDER", "").strip().lower()
    db_path = os.getenv("ANNE_WEB_DB", "anne_web.db")
    memory = LocalMemory(db_path)

    if provider_name == "openrouter":
        provider = OpenRouterProvider()
    elif provider_name == "gemini":
        provider = GeminiProvider()
    else:
        raise ProviderConfigurationError(
            "ANNE_WEB_PROVIDER must be 'openrouter' or 'gemini'. "
            "The web console does not use Ollama as ANNE's cognitive engine."
        )

    research_url = os.getenv("ANNE_MITOS_URL", "").strip()
    chatgpt_url = os.getenv("ANNE_CHATGPT_URL", "").strip()
    research = HTTPResearchAdapter(research_url, "MITOS") if research_url else None
    consultation = HTTPResearchAdapter(chatgpt_url, "CHATGPT") if chatgpt_url else None
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
            heapq.heappush(self._heap, _QueuedRequest(priority, self._sequence, future, actor, prompt))
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

                # Epistemic decisions must consume structured memory. The legacy
                # context string remains presentation/debug context only and is
                # never the primary previous-answer source.
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
            except Exception as exc:  # noqa: BLE001 - returned at HTTP boundary
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


MAX_QUEUE = int(os.getenv("ANNE_WEB_MAX_QUEUE", str(DEFAULT_MAX_QUEUE)))
runtime = PriorityRuntime(max_queue=MAX_QUEUE)
app = FastAPI(title="ANNE Cognitive Learning Console", version="0.4.0")


HTML = """<!doctype html>
<html lang="tr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>ANNE AI — Cognitive Learning Console</title>
<style>
body{font-family:system-ui,sans-serif;max-width:980px;margin:0 auto;padding:20px;background:#f5f6f8;color:#17202a}
main{background:#fff;border:1px solid #ddd;border-radius:18px;padding:20px}
#chat{height:430px;overflow:auto;border:1px solid #ddd;border-radius:12px;padding:14px;white-space:pre-wrap}
.msg{margin:0 0 16px}.who{font-weight:700}.anne{background:#f1f3f5;padding:10px;border-radius:10px}
.badge{font-size:.75rem;border:1px solid #ccc;border-radius:999px;padding:2px 7px;margin-right:5px}
textarea{width:100%;box-sizing:border-box;border:1px solid #bbb;border-radius:12px;padding:12px;font:inherit;margin-top:12px}
button{margin-top:10px;padding:10px 18px;border:0;border-radius:10px;cursor:pointer}.report{margin-top:14px;border:1px solid #ddd;border-radius:12px;padding:14px;background:#fafafa}
.small{font-size:.9rem;color:#667085}.warn{color:#8a5a00}
</style></head><body><main>
<h1>ANNE AI</h1><p class="small">Chrome iletişim yüzeyidir. Bilişsel akış ANNE'ye aittir; MITOS ve harici danışma ANNE tarafından çağrılır.</p>
<div id="chat"><div class="msg anne"><span class="badge">ANNE</span><br>Merhaba. Ben ANNE AI. Bir soru ver; bilgi durumumu kontrol edip gerektiğinde araştırma ve öğrenme döngümü çalıştıracağım.</div></div>
<textarea id="prompt" rows="4" placeholder="ANNE'ye mesaj yaz..."></textarea><button id="send" type="button">Gönder</button>
<div id="report" class="report small">Yönetici özeti ve edinilmek istenen fayda burada görünecek.</div>
</main><script>
const esc=s=>String(s).replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;');
async function send(){const p=document.getElementById('prompt'),c=document.getElementById('chat'),rpt=document.getElementById('report'),b=document.getElementById('send');const prompt=p.value.trim();if(!prompt)return;b.disabled=true;
c.innerHTML+=`<div class="msg"><span class="badge">GÖKHAN</span><br>${esc(prompt)}</div>`;p.value='';rpt.textContent='ANNE bilişsel döngüyü çalıştırıyor...';
try{const r=await fetch('/chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({prompt,actor:'GÖKHAN'})});const d=await r.json();if(!r.ok)throw new Error(d.detail||'İstek başarısız');
c.innerHTML+=`<div class="msg anne"><span class="badge">ANNE</span><br>${esc(d.response)}</div>`;
rpt.innerHTML=`<b>YÖNETİCİ ÖZETİ</b><br>${esc(d.manager_summary)}<br><br><b>EDİNİLMEK İSTENEN FAYDA</b><br>${esc(d.benefit)}<br><br><b>ÖĞRENME</b><br>${esc(d.learned)}<br><br><b>KARŞILAŞTIRMA</b>: ${esc(d.comparison_status)}<br><b>DIŞ KANIT</b>: ${d.evidence_count}<br><b>ÖNCEKİ BİLGİ DEĞİŞTİ</b>: ${d.changed_since_previous?'Evet':'Hayır'}<br><b>TECRÜBE</b>: ${esc(JSON.stringify(d.experience))}`;
c.scrollTop=c.scrollHeight;}catch(e){rpt.innerHTML='<span class="warn">'+esc(e.message)+'</span>';}finally{b.disabled=false;}}
document.getElementById('send').addEventListener('click',send);
document.getElementById('prompt').addEventListener('keydown',e=>{if(e.key==='Enter'&&(e.ctrlKey||e.metaKey)){e.preventDefault();send();}});
</script></body></html>"""


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    return HTML


@app.get("/health")
def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "runtime": "anne-cognitive-learning-console",
        "provider": os.getenv("ANNE_WEB_PROVIDER", "not configured"),
        "mitos_configured": bool(os.getenv("ANNE_MITOS_URL", "").strip()),
        "chatgpt_configured": bool(os.getenv("ANNE_CHATGPT_URL", "").strip()),
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
    except Exception as exc:  # noqa: BLE001 - safe server boundary
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
    )


@app.on_event("shutdown")
def shutdown() -> None:
    runtime.stop()


__all__ = ["app", "PriorityRuntime", "PRIORITY_OWNER", "PUBLIC_PRIORITY"]
