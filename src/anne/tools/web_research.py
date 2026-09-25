"""Public web research tools for MITOS.

The implementation is intentionally provider-light: no paid search API is required.
MITOS may query a public HTML search endpoint and then fetch public HTTP(S) pages.
All network reads are bounded, read-only, provenance-preserving, and fail closed.
"""

from __future__ import annotations

import html
import ipaddress
import re
import socket
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from html.parser import HTMLParser
from typing import Any


DEFAULT_SEARCH_URL = "https://noai.duckduckgo.com/html/"


@dataclass(frozen=True)
class WebSearchResult:
    title: str
    url: str
    snippet: str = ""


@dataclass(frozen=True)
class WebPageEvidence:
    url: str
    final_url: str
    title: str
    text: str
    content_type: str
    status: int


class _SearchParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.results: list[WebSearchResult] = []
        self._anchor: str | None = None
        self._href: str = ""
        self._text: list[str] = []
        self._snippet: list[str] = []
        self._in_snippet = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr = dict(attrs)
        classes = set((attr.get("class") or "").split())
        if tag == "a" and "result__a" in classes:
            self._anchor = "result"
            self._href = html.unescape(attr.get("href") or "")
            self._text = []
        elif tag in {"a", "div", "span"} and (
            "result__snippet" in classes or "result__snippet" in (attr.get("data-testid") or "")
        ):
            self._in_snippet = True
            self._snippet = []

    def handle_data(self, data: str) -> None:
        if self._anchor == "result":
            self._text.append(data)
        if self._in_snippet:
            self._snippet.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "a" and self._anchor == "result":
            title = " ".join(" ".join(self._text).split())
            url = self._normalize_result_url(self._href)
            if title and url:
                self.results.append(
                    WebSearchResult(
                        title=title,
                        url=url,
                        snippet=" ".join(" ".join(self._snippet).split()),
                    )
                )
            self._anchor = None
            self._href = ""
            self._text = []
        if tag in {"a", "div", "span"} and self._in_snippet:
            self._in_snippet = False

    @staticmethod
    def _normalize_result_url(value: str) -> str:
        if not value:
            return ""
        parsed = urllib.parse.urlparse(value)
        if parsed.scheme in {"http", "https"} and parsed.netloc:
            return value
        query = urllib.parse.parse_qs(parsed.query)
        target = query.get("uddg", [None])[0]
        if target:
            return urllib.parse.unquote(target)
        if value.startswith("//"):
            return "https:" + value
        return ""


class PublicWebResearchTool:
    """Bounded read-only public-web search and page fetcher."""

    def __init__(
        self,
        *,
        search_url: str = DEFAULT_SEARCH_URL,
        timeout: float = 10.0,
        max_bytes: int = 1_000_000,
        user_agent: str = "ANNE-MITOS-WebResearch/1.0",
    ) -> None:
        self.search_url = search_url
        self.timeout = timeout
        self.max_bytes = max_bytes
        self.user_agent = user_agent

    @staticmethod
    def _assert_public_url(url: str) -> None:
        parsed = urllib.parse.urlparse(url)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            raise ValueError("Only public HTTP(S) URLs are allowed")
        if parsed.username or parsed.password:
            raise ValueError("URL credentials are not allowed")
        try:
            addresses = socket.getaddrinfo(parsed.hostname, None)
        except OSError as exc:
            raise ValueError("Host could not be resolved") from exc
        for entry in addresses:
            address = ipaddress.ip_address(entry[4][0])
            if (
                address.is_private
                or address.is_loopback
                or address.is_link_local
                or address.is_multicast
                or address.is_reserved
                or address.is_unspecified
            ):
                raise ValueError("Private or non-public network target blocked")

    def _get(self, url: str) -> tuple[bytes, str, str, int]:
        self._assert_public_url(url)
        request = urllib.request.Request(
            url,
            headers={
                "User-Agent": self.user_agent,
                "Accept": "text/html,application/xhtml+xml,application/json;q=0.8,text/plain;q=0.7,*/*;q=0.2",
            },
            method="GET",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                content_type = response.headers.get("Content-Type", "")
                status = int(getattr(response, "status", 200))
                final_url = response.geturl()
                data = response.read(self.max_bytes + 1)
        except (urllib.error.URLError, TimeoutError, ValueError) as exc:
            raise RuntimeError(f"Web fetch failed: {exc}") from exc
        if len(data) > self.max_bytes:
            data = data[: self.max_bytes]
        return data, final_url, content_type, status

    @staticmethod
    def _decode(data: bytes, content_type: str) -> str:
        match = re.search(r"charset=([^;]+)", content_type, flags=re.I)
        encoding = match.group(1).strip() if match else "utf-8"
        try:
            return data.decode(encoding, errors="replace")
        except LookupError:
            return data.decode("utf-8", errors="replace")

    def search(self, query: str, *, max_results: int = 8) -> list[WebSearchResult]:
        query = " ".join(query.split())
        if not query:
            raise ValueError("query is required")
        if not 1 <= max_results <= 20:
            raise ValueError("max_results must be between 1 and 20")
        parsed = urllib.parse.urlparse(self.search_url)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            raise ValueError("search_url must be HTTP(S)")
        params = urllib.parse.parse_qs(parsed.query)
        params["q"] = [query]
        search_url = urllib.parse.urlunparse(
            parsed._replace(query=urllib.parse.urlencode(params, doseq=True))
        )
        data, _, content_type, _ = self._get(search_url)
        parser = _SearchParser()
        parser.feed(self._decode(data, content_type))
        unique: list[WebSearchResult] = []
        seen: set[str] = set()
        for result in parser.results:
            if result.url in seen:
                continue
            seen.add(result.url)
            unique.append(result)
            if len(unique) >= max_results:
                break
        return unique

    def fetch(self, url: str) -> WebPageEvidence:
        data, final_url, content_type, status = self._get(url)
        if not final_url:
            raise RuntimeError("Web fetch returned no final URL")
        text = self._decode(data, content_type)
        # Keep source pages human-readable while avoiding script/style noise.
        text = re.sub(r"(?is)<(script|style|noscript|svg).*?</\1>", " ", text)
        title_match = re.search(r"(?is)<title[^>]*>(.*?)</title>", text)
        title = " ".join(html.unescape(title_match.group(1)).split()) if title_match else ""
        visible = re.sub(r"(?s)<[^>]+>", " ", text)
        visible = " ".join(html.unescape(visible).split())
        return WebPageEvidence(
            url=url,
            final_url=final_url,
            title=title[:500],
            text=visible[:20000],
            content_type=content_type,
            status=status,
        )

    def research(
        self,
        query: str,
        *,
        max_results: int = 8,
        fetch_pages: int = 4,
    ) -> dict[str, Any]:
        if not 1 <= fetch_pages <= max_results:
            raise ValueError("fetch_pages must be between 1 and max_results")
        results = self.search(query, max_results=max_results)
        pages: list[dict[str, Any]] = []
        for result in results[:fetch_pages]:
            try:
                page = self.fetch(result.url)
                pages.append(
                    {
                        "source": result.url,
                        "title": page.title or result.title,
                        "snippet": result.snippet,
                        "final_url": page.final_url,
                        "content_type": page.content_type,
                        "status": page.status,
                        "text": page.text,
                        "provenance": "public_web_fetch",
                    }
                )
            except Exception as exc:
                pages.append(
                    {
                        "source": result.url,
                        "title": result.title,
                        "snippet": result.snippet,
                        "error": str(exc),
                        "provenance": "public_web_search_only",
                    }
                )
        return {
            "query": query,
            "search_provider": "public_html_search",
            "results": [
                {"title": r.title, "url": r.url, "snippet": r.snippet}
                for r in results
            ],
            "pages": pages,
        }


__all__ = ["PublicWebResearchTool", "WebPageEvidence", "WebSearchResult"]
