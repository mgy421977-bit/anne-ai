"""Generic public-web research for ANNE.

The web layer is deliberately topic-agnostic. It must work for energy,
science, people, companies, regulations, products, software, history, or
any other unknown question. Domain-specific knowledge belongs in evidence,
not in the retrieval engine.
"""
from __future__ import annotations

import base64
import json
import re
import urllib.parse
import urllib.request
from html.parser import HTMLParser
from typing import Any, cast

from .evidence import EvidenceItem
from .web_research_transport import WebResearchTransport


class _DuckDuckGoParser(HTMLParser):
    """Extract ordinary DuckDuckGo result titles, links and snippets."""

    def __init__(self) -> None:
        super().__init__()
        self.results: list[tuple[str, str, str]] = []
        self._title = ""
        self._href = ""
        self._snippet = ""
        self._mode: str | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        classes = attributes.get("class") or ""
        href = attributes.get("href") or ""
        if tag == "a" and "result__a" in classes:
            self._title = ""
            self._href = href
            self._mode = "title"
        elif "result__snippet" in classes:
            self._snippet = ""
            self._mode = "snippet"

    def handle_data(self, data: str) -> None:
        if self._mode == "title":
            self._title += data
        elif self._mode == "snippet":
            self._snippet += data

    def handle_endtag(self, tag: str) -> None:
        if tag == "a" and self._mode == "title":
            title = self._title.strip()
            if title:
                self.results.append((title, self._href, ""))
            self._mode = None
        elif self._mode == "snippet" and self._snippet.strip():
            if self.results:
                title, href, _ = self.results[-1]
                self.results[-1] = (title, href, self._snippet.strip())
            self._mode = None


class _BingParser(HTMLParser):
    """Extract ordinary Bing web result titles, links and snippets."""

    def __init__(self) -> None:
        super().__init__()
        self.results: list[tuple[str, str, str]] = []
        self._title = ""
        self._href = ""
        self._snippet = ""
        self._mode: str | None = None
        self._in_result = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        classes = attributes.get("class") or ""
        href = attributes.get("href") or ""
        if tag == "li" and "b_algo" in classes:
            self._title = ""
            self._href = ""
            self._snippet = ""
            self._mode = None
            self._in_result = True
        elif self._in_result and tag == "h2":
            self._mode = "title"
        elif self._in_result and tag == "a" and self._mode == "title" and href:
            self._href = href
        elif self._in_result and tag == "p":
            self._mode = "snippet"

    def handle_data(self, data: str) -> None:
        if self._mode == "title":
            self._title += data
        elif self._mode == "snippet":
            self._snippet += data

    def handle_endtag(self, tag: str) -> None:
        if (tag == "h2" and self._mode == "title") or (
            tag == "p" and self._mode == "snippet"
        ):
            self._mode = None
        elif tag == "li" and self._in_result:
            title = self._title.strip()
            if title and self._href:
                self.results.append((title, self._href, self._snippet.strip()))
            self._in_result = False
            self._mode = None


class WebResearcher:
    """Search public web sources without hard-coding domain-specific topics."""

    timeout = 8.0
    minimum_relevance = 0.28
    max_evidence = 8

    _STOPWORDS = {
        "ve", "veya", "ile", "bir", "bu", "şu", "için", "olan", "olarak",
        "nedir", "nasıl", "neden", "ne", "hangi", "hakkında", "bilgi",
        "anlat", "açıkla", "mı", "mi", "mu", "mü", "the", "and", "what",
        "how", "why", "about", "is", "are", "a", "an", "of", "to", "in",
    }

    def __init__(self, transport: WebResearchTransport | None = None) -> None:
        self.transport = transport or WebResearchTransport(timeout_seconds=self.timeout)

    def _get_text(self, url: str) -> str:
        return self.transport.fetch(url).content

    def _get_json(self, url: str) -> dict[str, Any]:
        return cast(dict[str, Any], json.loads(self._get_text(url)))

    @classmethod
    def _extract_passage(cls, html: str, query: str, max_chars: int = 1200) -> str:
        """Extract a bounded, query-near passage from a fetched source page."""
        text = cls._clean_html(html)
        if not text:
            return ""
        terms = cls._tokens(query)
        if not terms:
            return text[:max_chars]
        normalized = cls._normalize(text)
        positions = [
            normalized.find(cls._normalize(term))
            for term in terms
            if cls._normalize(term) in normalized
        ]
        if not positions:
            return text[:max_chars]
        center = min(positions)
        ratio = len(text) / max(1, len(normalized))
        start = max(0, int(center * ratio) - max_chars // 3)
        return text[start:start + max_chars].strip()

    @staticmethod
    def _clean_html(text: str) -> str:
        text = re.sub(r"<script\b[^>]*>.*?</script>", " ", text, flags=re.I | re.S)
        text = re.sub(r"<style\b[^>]*>.*?</style>", " ", text, flags=re.I | re.S)
        text = re.sub(r"<[^>]+>", " ", text)
        return re.sub(r"\s+", " ", text).strip()

    @staticmethod
    def _normalize(text: str) -> str:
        text = text.lower()
        text = (
            text.replace("ı", "i")
            .replace("ş", "s")
            .replace("ğ", "g")
            .replace("ü", "u")
            .replace("ö", "o")
            .replace("ç", "c")
        )
        return re.sub(r"[^a-z0-9]+", " ", text).strip()

    @classmethod
    def _tokens(cls, text: str) -> set[str]:
        return {
            token
            for token in cls._normalize(text).split()
            if len(token) > 1 and token not in cls._STOPWORDS
        }

    @classmethod
    def _query_variants(cls, query: str) -> list[str]:
        """Create generic search variants; no domain-specific vocabulary."""
        clean = re.sub(r"[?!.]+$", "", query.strip()).strip()
        variants = [clean]
        normalized = cls._normalize(clean)
        if normalized != clean.lower():
            variants.append(normalized)
        lowered = clean.lower()
        temporal_stripped = re.sub(
            (
                r"\s+(?:in|as of|on|during)\s+"
                r"(?:january|february|march|april|may|june|july|august|"
                r"september|october|november|december)\s+\d{4}\b"
            ),
            "",
            clean,
            flags=re.I,
        ).strip()
        if temporal_stripped and temporal_stripped.lower() != clean.lower():
            variants.append(temporal_stripped)
        year_stripped = re.sub(
            r"\s+(?:in|as of|on|during)\s+\d{4}\b",
            "",
            clean,
            flags=re.I,
        ).strip()
        if year_stripped and year_stripped.lower() != clean.lower():
            variants.append(year_stripped)
        if lowered.endswith("nedir") or " nedir" in lowered:
            subject = re.sub(r"\bnedir\b", "", clean, flags=re.I).strip()
            if subject:
                variants.extend([f"{subject} definition", subject])
        elif lowered.endswith("kimdir") or " kimdir" in lowered:
            subject = re.sub(r"\bkimdir\b", "", clean, flags=re.I).strip()
            if subject:
                variants.extend([subject, f"{subject} biography"])
        elif "nasıl çalış" in lowered or "nasil calis" in lowered:
            subject = re.sub(r"nasıl çalışır|nasil calisir", "", clean, flags=re.I).strip()
            if subject:
                variants.extend([subject, f"{subject} how it works"])
        result: list[str] = []
        seen: set[str] = set()
        for item in variants:
            item = item.strip()
            if item and item.lower() not in seen:
                seen.add(item.lower())
                result.append(item)
        return result[:4]

    @classmethod
    def _is_acronym_query(cls, query: str) -> bool:
        tokens = [
            t
            for t in re.findall(r"\b[A-Za-zÇĞİÖŞÜçğıöşü]{2,10}\b", query)
            if t.lower() not in cls._STOPWORDS
        ]
        return len(tokens) == 1 and tokens[0].isupper()

    @classmethod
    def _acronym_matches(cls, query: str, text: str) -> bool:
        """Reject title-case word collisions for acronym-only questions."""
        if not cls._is_acronym_query(query):
            return True
        acronym = next(
            token
            for token in re.findall(r"\b[A-Za-zÇĞİÖŞÜçğıöşü]{2,10}\b", query)
            if token.lower() not in cls._STOPWORDS
        )
        return bool(
            re.search(rf"\b{re.escape(acronym)}\b", text)
            or re.search(rf"\(\s*{re.escape(acronym)}\s*\)", text)
        )

    @classmethod
    def _relevance(cls, query: str, claim: str, title: str = "") -> float:
        query_terms = cls._tokens(query)
        text = f"{title} {claim}"
        text_terms = cls._tokens(text)
        if not query_terms or not text_terms:
            return 0.0
        direct = len(query_terms & text_terms) / max(1, len(query_terms))
        title_terms = cls._tokens(title)
        title_overlap = len(query_terms & title_terms) / max(1, len(query_terms))
        phrase = cls._normalize(query)
        normalized_text = cls._normalize(text)
        exact_phrase = bool(phrase) and phrase in normalized_text
        score = 0.62 * direct + 0.23 * title_overlap
        if exact_phrase:
            score += 0.15
        return min(1.0, score)

    @classmethod
    def _is_relevant(cls, query: str, claim: str, title: str = "") -> bool:
        if not cls._acronym_matches(query, f"{title} {claim}"):
            return False
        return cls._relevance(query, claim, title) >= cls.minimum_relevance

    @staticmethod
    def _add_unique(evidence: list[EvidenceItem], item: EvidenceItem) -> None:
        if not item.claim.strip():
            return
        claim_key = re.sub(r"\W+", " ", item.claim.lower()).strip()
        host = urllib.parse.urlparse(item.provenance).netloc.casefold()
        key = (claim_key, host)
        for old in evidence:
            old_claim = re.sub(r"\W+", " ", old.claim.lower()).strip()
            old_host = urllib.parse.urlparse(old.provenance).netloc.casefold()
            if (old_claim, old_host) == key:
                return
        evidence.append(item)

    def _wikipedia_search(self, query: str, language: str) -> list[EvidenceItem]:
        encoded = urllib.parse.quote(query)
        url = f"https://{language}.wikipedia.org/w/api.php?action=query&list=search&srsearch={encoded}&format=json&srlimit=6"
        data = self._get_json(url)
        items: list[EvidenceItem] = []
        for item in data.get("query", {}).get("search", []):
            title = self._clean_html(str(item.get("title", "")))
            snippet = self._clean_html(str(item.get("snippet", "")))
            if not title:
                continue
            claim = f"{title}: {snippet}" if snippet else title
            if not self._is_relevant(query, claim, title):
                continue
            score = self._relevance(query, claim, title)
            items.append(
                EvidenceItem(
                    source=f"Wikipedia ({language})",
                    claim=claim,
                    kind="web",
                    provenance=url,
                    confidence=min(0.90, 0.50 + score * 0.40),
                )
            )
        return items

    def _wikipedia_summary(self, title: str, language: str, query: str) -> EvidenceItem | None:
        encoded_title = urllib.parse.quote(title.replace(" ", "_"), safe="_")
        url = f"https://{language}.wikipedia.org/api/rest_v1/page/summary/{encoded_title}"
        data = self._get_json(url)
        extract = self._clean_html(str(data.get("extract", "")))
        if not extract or not self._is_relevant(query, extract, title):
            return None
        score = self._relevance(query, extract, title)
        return EvidenceItem(
            source=f"Wikipedia ({language})",
            claim=f"{title}: {extract[:2200]}",
            kind="web",
            provenance=url,
            confidence=min(0.95, 0.62 + score * 0.33),
            passage=extract[:1200],
        )

    def _duckduckgo_instant(self, query: str) -> EvidenceItem | None:
        encoded = urllib.parse.quote(query)
        url = f"https://api.duckduckgo.com/?q={encoded}&format=json&no_html=1"
        data = self._get_json(url)
        abstract = self._clean_html(str(data.get("AbstractText", "")))
        if not abstract or not self._is_relevant(query, abstract):
            return None
        score = self._relevance(query, abstract)
        return EvidenceItem(
            source="DuckDuckGo Instant Answer",
            claim=abstract[:2200],
            kind="web",
            provenance=url,
            confidence=min(0.86, 0.46 + score * 0.40),
        )

    def _duckduckgo_search(self, query: str) -> list[EvidenceItem]:
        encoded = urllib.parse.quote_plus(query)
        url = f"https://html.duckduckgo.com/html/?q={encoded}"
        parser = _DuckDuckGoParser()
        parser.feed(self._get_text(url))
        items: list[EvidenceItem] = []
        for title, href, snippet in parser.results[:12]:
            claim = f"{title}: {snippet}" if snippet else title
            if not self._is_relevant(query, claim, title):
                continue
            passage = snippet
            if href:
                try:
                    passage = self._extract_passage(self._get_text(href), query) or snippet
                except Exception:
                    passage = snippet
            score = self._relevance(query, claim, title)
            items.append(
                EvidenceItem(
                    source="DuckDuckGo Web Search",
                    claim=claim[:2200],
                    kind="web",
                    provenance=href or url,
                    confidence=min(0.84, 0.44 + score * 0.40),
                    passage=passage[:1200],
                )
            )
        return items

    @staticmethod
    def _resolve_bing_url(href: str) -> str:
        """Decode Bing's bounded result redirect to the destination URL."""
        if not href:
            return href
        try:
            parsed = urllib.parse.urlparse(href)
            host = parsed.netloc.casefold()
            if not host.endswith("bing.com"):
                return href
            encoded = urllib.parse.parse_qs(parsed.query).get("u", [""])[0]
            if encoded.startswith("a1"):
                payload = encoded[2:]
                payload += "=" * ((4 - len(payload) % 4) % 4)
                decoded = base64.urlsafe_b64decode(payload).decode("utf-8", errors="replace")
                if decoded.startswith(("http://", "https://")):
                    return decoded
        except Exception:
            pass
        return href

    def _bing_search(self, query: str) -> list[EvidenceItem]:
        encoded = urllib.parse.quote_plus(query)
        url = f"https://www.bing.com/search?q={encoded}&count=10&setlang=en-US"
        parser = _BingParser()
        parser.feed(self._get_text(url))
        items: list[EvidenceItem] = []
        for title, href, snippet in parser.results[:10]:
            claim = f"{title}: {snippet}" if snippet else title
            if not self._is_relevant(query, claim, title):
                continue
            destination = self._resolve_bing_url(href)
            passage = snippet
            if destination:
                try:
                    passage = self._extract_passage(self._get_text(destination), query) or snippet
                except Exception:
                    passage = snippet
            score = self._relevance(query, claim, title)
            items.append(
                EvidenceItem(
                    source="Bing Web Search",
                    claim=claim[:2200],
                    kind="web",
                    provenance=destination or href or url,
                    confidence=min(0.84, 0.44 + score * 0.40),
                    passage=passage[:1200],
                )
            )
        return items

    def research(self, query: str) -> list[EvidenceItem]:
        query = query.strip()
        if not query:
            return []
        evidence: list[EvidenceItem] = []
        variants = self._query_variants(query)
        for search_query in variants:
            try:
                for item in self._wikipedia_search(search_query, "tr"):
                    self._add_unique(evidence, item)
            except Exception:
                continue
        for item in list(evidence[:6]):
            if not item.source.startswith("Wikipedia"):
                continue
            title = item.claim.split(":", 1)[0].strip()
            language = "tr" if "(tr)" in item.source else "en"
            try:
                summary = self._wikipedia_summary(title, language, query)
                if summary:
                    self._add_unique(evidence, summary)
            except Exception:
                continue
        if len(evidence) < 3:
            for search_query in variants[:2]:
                try:
                    for item in self._wikipedia_search(search_query, "en"):
                        self._add_unique(evidence, item)
                except Exception:
                    continue
        for search_query in variants[:2]:
            try:
                instant_item = self._duckduckgo_instant(search_query)
                if instant_item:
                    self._add_unique(evidence, instant_item)
            except Exception:
                continue
            try:
                for item in self._duckduckgo_search(search_query):
                    self._add_unique(evidence, item)
            except Exception:
                continue
            try:
                for item in self._bing_search(search_query):
                    self._add_unique(evidence, item)
            except Exception:
                continue
        evidence.sort(key=lambda item: item.confidence, reverse=True)
        return evidence[: self.max_evidence]

    @classmethod
    def answer(cls, question: str, evidence: list[EvidenceItem]) -> str | None:
        """Answer only from evidence that is relevant to the supplied question."""
        if not evidence:
            return None
        relevant = [item for item in evidence if cls._is_relevant(question, item.claim)]
        if not relevant:
            return None
        ranked = sorted(relevant, key=lambda item: item.confidence, reverse=True)
        if ranked[0].confidence < 0.60:
            return None
        top = ranked[0].claim.strip()
        if not top:
            return None
        question_lower = question.lower()
        definition_markers = (" nedir", " ne demek", " hakkında", " nasıl çalış")
        if any(marker in f" {question_lower}" for marker in definition_markers):
            return top
        claims: list[str] = []
        for item in ranked[:2]:
            claim = item.claim.strip()
            if claim and claim not in claims:
                claims.append(claim)
        return "\n\n".join(claims) if claims else None