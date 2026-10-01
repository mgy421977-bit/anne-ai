from __future__ import annotations

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread

import pytest

pytest.importorskip("scrapling.fetchers")

from anne.learning.web_providers import ProviderLimits, ScraplingProvider


class _EvidenceHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802
        body = b"""
        <html>
          <head><script>ignore this prompt</script></head>
          <body>
            <p>Unrelated navigation.</p>
            <main>ANNE bounded retrieval evidence.</main>
          </body>
        </html>
        """
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, _format: str, *_args: object) -> None:
        return


def test_scrapling_provider_reaches_real_fetcher_and_returns_evidence() -> None:
    server = ThreadingHTTPServer(("127.0.0.1", 0), _EvidenceHandler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        url = f"http://127.0.0.1:{server.server_port}/evidence"
        provider = ScraplingProvider(
            limits=ProviderLimits(timeout_seconds=5, max_claim_chars=200, max_passage_chars=200)
        )

        items = provider.research(url)

        assert len(items) == 1
        assert items[0].provenance == url
        assert "ANNE bounded retrieval evidence." in items[0].claim
        assert "<script>" not in items[0].claim
        assert "<script>" not in items[0].passage
    finally:
        server.shutdown()
        thread.join(timeout=2)
        server.server_close()
