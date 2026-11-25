"""Fractal episodic memory backed by SQLite."""

from __future__ import annotations

import hashlib
import json
import re
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any, cast

from anne.core.cognitive_state import Consciousness, EthicScore, Hypothesis
from anne.memory.persistence import connect_memory
from anne.safety.policy import redact_sensitive


class FractalMemory:
    """Persistent memory with additive multi-scale coordinates.

    Existing databases are migrated without destructive schema changes.
    """

    def __init__(self, db_path: str = "anne.db") -> None:
        self.conn = connect_memory(db_path)
        self.conn.execute("PRAGMA foreign_keys = ON")
        self._init_tables()

    def _ensure_columns(self, table: str, columns: dict[str, str]) -> None:
        existing = {row[1] for row in self.conn.execute(f"PRAGMA table_info({table})")}
        for name, definition in columns.items():
            if name not in existing:
                self.conn.execute(f"ALTER TABLE {table} ADD COLUMN {name} {definition}")

    def _init_tables(self) -> None:
        cur = self.conn.cursor()
        cur.execute("""CREATE TABLE IF NOT EXISTS hypotheses (
            id TEXT PRIMARY KEY, topic TEXT, claim TEXT, probability REAL,
            iteration INTEGER, tested INTEGER, result TEXT, confidence_delta REAL,
            source TEXT, created_at TEXT)""")
        cur.execute("""CREATE TABLE IF NOT EXISTS decisions (
            id TEXT PRIMARY KEY, hypothesis_id TEXT, goodness REAL, equality REAL,
            harm REAL, total REAL, verdict TEXT, reasoning TEXT, consciousnesses TEXT,
            cognitive_stage TEXT, created_at TEXT)""")
        cur.execute("""CREATE TABLE IF NOT EXISTS dream_patterns (
            id TEXT PRIMARY KEY, pattern TEXT UNIQUE, frequency INTEGER DEFAULT 1,
            avg_score REAL DEFAULT 0.0, last_verdict TEXT, last_seen TEXT)""")
        cur.execute("""CREATE TABLE IF NOT EXISTS learned_rules (
            id TEXT PRIMARY KEY, rule TEXT, confidence REAL,
            support_count INTEGER DEFAULT 1, created_at TEXT)""")
        cur.execute("""CREATE TABLE IF NOT EXISTS empathy_map (
            id TEXT PRIMARY KEY, consciousness_a TEXT, consciousness_b TEXT,
            relation_strength REAL DEFAULT 0.5, conflict_count INTEGER DEFAULT 0,
            resolution_count INTEGER DEFAULT 0, updated_at TEXT)""")
        cur.execute("""CREATE TABLE IF NOT EXISTS failure_traces (
            id TEXT PRIMARY KEY, cycle_id TEXT, stage TEXT, raw_input TEXT,
            reason TEXT, meta_tag TEXT, hypothesis_id TEXT, ethic_total REAL,
            created_at TEXT)""")
        cur.execute("""CREATE TABLE IF NOT EXISTS memory_relations (
            id TEXT PRIMARY KEY, source_decision_id TEXT NOT NULL,
            target_decision_id TEXT NOT NULL, relation TEXT NOT NULL,
            reason TEXT NOT NULL, task_mode TEXT NOT NULL DEFAULT 'general',
            created_at TEXT NOT NULL,
            UNIQUE(source_decision_id,target_decision_id,relation))""")
        cur.execute("""CREATE TABLE IF NOT EXISTS scale_events (
            cycle_id TEXT PRIMARY KEY, parent_cycle_id TEXT, depth INTEGER NOT NULL DEFAULT 0,
            scale_role TEXT NOT NULL, task_mode TEXT NOT NULL DEFAULT 'general',
            question TEXT NOT NULL, selected_claim TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL DEFAULT 'started', stage_reached TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL)""")
        cur.execute("""CREATE TABLE IF NOT EXISTS experience_observations (
            source_cycle_id TEXT PRIMARY KEY,
            outcome TEXT NOT NULL,
            failure_class TEXT NOT NULL,
            strategy TEXT NOT NULL,
            lesson TEXT NOT NULL,
            safe_to_reuse INTEGER NOT NULL DEFAULT 0,
            factual_status TEXT NOT NULL,
            context_key TEXT NOT NULL DEFAULT '',
            context_conditions TEXT NOT NULL DEFAULT '[]',
            parent_cycle_id TEXT,
            lineage TEXT NOT NULL DEFAULT '[]',
            language_corroboration_status TEXT NOT NULL DEFAULT '',
            language_corroboration_providers TEXT NOT NULL DEFAULT '[]',
            created_at TEXT NOT NULL)""")
        self._ensure_columns(
            "experience_observations",
            {
                "language_corroboration_status": "TEXT NOT NULL DEFAULT ''",
                "language_corroboration_providers": "TEXT NOT NULL DEFAULT '[]'",
            },
        )
        self._ensure_columns(
            "hypotheses",
            {
                "depth": "INTEGER NOT NULL DEFAULT 0",
                "parent_cycle_id": "TEXT",
                "task_mode": "TEXT NOT NULL DEFAULT 'general'",
            },
        )
        self._ensure_columns(
            "decisions",
            {
                "depth": "INTEGER NOT NULL DEFAULT 0",
                "parent_cycle_id": "TEXT",
                "task_mode": "TEXT NOT NULL DEFAULT 'general'",
            },
        )
        self._ensure_columns(
            "failure_traces",
            {
                "depth": "INTEGER NOT NULL DEFAULT 0",
                "parent_cycle_id": "TEXT",
                "task_mode": "TEXT NOT NULL DEFAULT 'general'",
                "scale_role": "TEXT NOT NULL DEFAULT 'frame'",
                "learning_failure_class": "TEXT NOT NULL DEFAULT ''",
                "learning_strategy": "TEXT NOT NULL DEFAULT ''",
                "learning_lesson": "TEXT NOT NULL DEFAULT ''",
                "learning_confidence": "REAL NOT NULL DEFAULT 0.0",
                "learning_safe_to_reuse": "INTEGER NOT NULL DEFAULT 0",
            },
        )
        self.conn.commit()

    def get_memory_links(
        self, decision_id: str | None = None, limit: int = 64
    ) -> list[dict[str, Any]]:
        """Return explicit links between historical decision records."""
        query = (
            "SELECT id,source_decision_id,target_decision_id,relation,reason,"
            "task_mode,created_at FROM memory_relations"
        )
        params: tuple[Any, ...] = ()
        if decision_id is not None:
            query += " WHERE source_decision_id=? OR target_decision_id=?"
            params = (decision_id, decision_id)
        rows = self.conn.execute(
            query + " ORDER BY created_at DESC LIMIT ?", (*params, limit)
        ).fetchall()
        return [
            {
                "id": row[0],
                "source_decision_id": row[1],
                "target_decision_id": row[2],
                "relation": row[3],
                "reason": row[4],
                "task_mode": row[5],
                "created_at": row[6],
            }
            for row in rows
        ]

    @staticmethod
    def _normalize_token(token: str) -> str:
        """Normalize common Turkish inflections for lightweight memory recall."""
        token = token.casefold().strip(".,!?;:()[]{}\"'")
        if not token:
            return token
        suffixes = (
            "larından",
            "lerinden",
            "larına",
            "lerine",
            "ların",
            "lerin",
            "lardan",
            "lerden",
            "lara",
            "lere",
            "dan",
            "den",
            "tan",
            "ten",
            "dır",
            "dir",
            "dur",
            "dür",
            "tır",
            "tir",
            "tur",
            "tür",
            "ın",
            "in",
            "un",
            "ün",
            "ım",
            "im",
            "um",
            "üm",
            "ı",
            "i",
            "u",
            "ü",
        )
        for suffix in suffixes:
            if token.endswith(suffix) and len(token) - len(suffix) >= 3:
                return token[: -len(suffix)]
        return token

    @classmethod
    def _normalized_terms(cls, text: str) -> list[str]:
        raw_terms = re.findall(r"[\wçğıöşüÇĞİÖŞÜ]+", text.casefold(), flags=re.UNICODE)
        return [term for term in (cls._normalize_token(t) for t in raw_terms) if term]

    @staticmethod
    def _recall_variants(term: str) -> tuple[str, ...]:
        """Return conservative variants for Turkish consonant alternation.

        Turkish suffixation can soften final k→ğ (e.g. kaynak→kaynağı).
        Recall needs the reverse candidate as well, but this remains a bounded
        lexical fallback rather than a general morphological analyzer.
        """
        variants = [term]
        final_map = {"ğ": "k", "b": "p", "c": "ç", "d": "t"}
        if term and term[-1] in final_map and len(term) >= 3:
            variants.append(term[:-1] + final_map[term[-1]])
        return tuple(dict.fromkeys(variants))

    def save_hypothesis(
        self,
        h: Hypothesis,
        *,
        depth: int = 0,
        parent_cycle_id: str | None = None,
        task_mode: str = "general",
    ) -> None:
        self.conn.execute(
            """INSERT OR REPLACE INTO hypotheses
            (id,topic,claim,probability,iteration,tested,result,confidence_delta,source,created_at,
             depth,parent_cycle_id,task_mode) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                h.id,
                h.topic,
                h.claim,
                h.probability,
                h.iteration,
                int(h.tested),
                h.result,
                h.confidence_delta,
                h.source,
                datetime.now().isoformat(),
                depth,
                parent_cycle_id,
                task_mode,
            ),
        )
        self.conn.commit()

    def save_decision(
        self,
        decision_id: str,
        hyp_id: str,
        score: EthicScore,
        consciousnesses: list[Consciousness],
        stage: str = "YAP",
        *,
        depth: int = 0,
        parent_cycle_id: str | None = None,
        task_mode: str = "general",
    ) -> None:
        self.conn.execute(
            """INSERT OR REPLACE INTO decisions
            (id,hypothesis_id,goodness,equality,harm,total,verdict,reasoning,consciousnesses,
             cognitive_stage,created_at,depth,parent_cycle_id,task_mode)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                decision_id,
                hyp_id,
                score.goodness,
                score.equality,
                score.harm,
                score.total,
                score.verdict,
                score.reasoning,
                json.dumps([c.id for c in consciousnesses]),
                stage,
                datetime.now().isoformat(),
                depth,
                parent_cycle_id,
                task_mode,
            ),
        )
        self.conn.commit()

    def save_memory_link(
        self,
        source_decision_id: str,
        target_decision_id: str,
        task_mode: str,
        created_at: str,
    ) -> None:
        """Persist a non-destructive link between historical decisions."""
        statement = (
            "INSERT " + "OR IGNORE INTO memory_relations "
            "(id,source_decision_id,target_decision_id,relation,reason,task_mode,created_at) "
            "VALUES (?,?,?,?,?,?,?)"
        )
        self.conn.execute(
            statement,
            (
                f"rel_{uuid.uuid4().hex[:12]}",
                source_decision_id,
                target_decision_id,
                "supersedes",
                "newer compatible decision",
                task_mode,
                created_at,
            ),
        )

    def save_dream_pattern(self, pattern: str, score: float, verdict: str) -> None:
        cur = self.conn.cursor()
        existing = cur.execute(
            "SELECT id,frequency,avg_score FROM dream_patterns WHERE pattern=?",
            (pattern,),
        ).fetchone()
        if existing:
            nf = existing[1] + 1
            na = (existing[2] * existing[1] + score) / nf
            cur.execute(
                "UPDATE dream_patterns SET frequency=?,avg_score=?,last_verdict=?,last_seen=? "
                "WHERE id=?",
                (nf, round(na, 3), verdict, datetime.now().isoformat(), existing[0]),
            )
        else:
            cur.execute(
                "INSERT INTO dream_patterns VALUES (?,?,?,?,?,?)",
                (
                    f"dp_{uuid.uuid4().hex[:12]}",
                    pattern,
                    1,
                    score,
                    verdict,
                    datetime.now().isoformat(),
                ),
            )
        self.conn.commit()

    def save_learned_rule(self, rule: str, confidence: float) -> None:
        cur = self.conn.cursor()
        confidence = max(0.0, min(1.0, confidence))
        existing = cur.execute(
            "SELECT id,support_count,confidence FROM learned_rules WHERE rule=?",
            (rule,),
        ).fetchone()
        if existing:
            average = (existing[2] * existing[1] + confidence) / (existing[1] + 1)
            cur.execute(
                "UPDATE learned_rules SET confidence=?,support_count=? WHERE id=?",
                (average, existing[1] + 1, existing[0]),
            )
        else:
            cur.execute(
                "INSERT INTO learned_rules VALUES (?,?,?,?,?)",
                (f"rule_{uuid.uuid4().hex[:12]}", rule, confidence, 1, datetime.now().isoformat()),
            )
        self.conn.commit()

    def update_empathy(
        self,
        id_a: str,
        id_b: str,
        conflict: bool = False,
        resolved: bool = False,
    ) -> None:
        key = f"{min(id_a, id_b)}_{max(id_a, id_b)}"
        cur = self.conn.cursor()
        existing = cur.execute(
            "SELECT id,relation_strength,conflict_count,resolution_count "
            "FROM empathy_map WHERE id=?",
            (key,),
        ).fetchone()
        if existing:
            s = min(1.0, existing[1] + (0.05 if resolved else -0.02))
            cur.execute(
                "UPDATE empathy_map SET relation_strength=?,conflict_count=?,resolution_count=?, "
                "updated_at=? WHERE id=?",
                (
                    round(s, 3),
                    existing[2] + (1 if conflict else 0),
                    existing[3] + (1 if resolved else 0),
                    datetime.now().isoformat(),
                    key,
                ),
            )
        else:
            cur.execute(
                "INSERT INTO empathy_map VALUES (?,?,?,?,?,?,?)",
                (
                    key,
                    id_a,
                    id_b,
                    0.5,
                    1 if conflict else 0,
                    1 if resolved else 0,
                    datetime.now().isoformat(),
                ),
            )
        self.conn.commit()

    def save_experience_observation(
        self,
        *,
        source_cycle_id: str,
        outcome: str,
        failure_class: str,
        strategy: str,
        lesson: str,
        safe_to_reuse: bool,
        factual_status: str,
        context_key: str = "",
        context_conditions: tuple[tuple[str, str], ...] = (),
        parent_cycle_id: str | None = None,
        lineage: tuple[str, ...] = (),
        language_corroboration_status: str = "",
        language_corroboration_providers: tuple[str, ...] = (),
    ) -> None:
        """Persist bounded learning evidence as an observation, never as authority."""
        self.conn.execute(
            """INSERT OR REPLACE INTO experience_observations
            (source_cycle_id,outcome,failure_class,strategy,lesson,safe_to_reuse,
             factual_status,context_key,context_conditions,parent_cycle_id,lineage,language_corroboration_status,language_corroboration_providers,created_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                source_cycle_id,
                outcome,
                failure_class,
                strategy,
                lesson,
                int(safe_to_reuse),
                factual_status,
                context_key,
                json.dumps(list(context_conditions)),
                parent_cycle_id,
                json.dumps(list(lineage)),
                language_corroboration_status,
                json.dumps(list(language_corroboration_providers)),
                datetime.now().isoformat(),
            ),
        )
        self.conn.commit()

    def get_experience_observations(
        self,
        *,
        context_key: str,
        context_conditions: tuple[tuple[str, str], ...],
        limit: int = 64,
    ) -> list[dict[str, Any]]:
        """Return only exact-context observations; no semantic recall is used."""
        rows = (
            self.conn.cursor()
            .execute(
                """SELECT source_cycle_id,outcome,failure_class,strategy,lesson,safe_to_reuse,
            factual_status,context_key,context_conditions,parent_cycle_id,lineage,language_corroboration_status,language_corroboration_providers
            FROM experience_observations
            WHERE context_key=? AND context_conditions=?
            ORDER BY created_at DESC, rowid DESC LIMIT ?""",
                (context_key, json.dumps(list(context_conditions)), limit),
            )
            .fetchall()
        )
        return [
            {
                "source_cycle_id": row[0],
                "outcome": row[1],
                "failure_class": row[2],
                "strategy": row[3],
                "lesson": row[4],
                "safe_to_reuse": bool(row[5]),
                "factual_status": row[6],
                "context_key": row[7],
                "context_conditions": tuple(tuple(item) for item in json.loads(row[8])),
                "parent_cycle_id": row[9],
                "lineage": tuple(json.loads(row[10])),
                "language_corroboration_status": row[11],
                "language_corroboration_providers": tuple(json.loads(row[12])),
            }
            for row in rows
        ]

    def get_similar_decisions(self, topic: str, limit: int = 3) -> list[tuple[Any, ...]]:
        cur = self.conn.cursor()
        results: list[tuple[Any, ...]] = []
        for term in self._normalized_terms(topic):
            for variant in self._recall_variants(term):
                rows = cur.execute(
                    """SELECT d.verdict,d.total,d.reasoning,h.topic
                    FROM decisions d JOIN hypotheses h ON d.hypothesis_id=h.id
                    WHERE h.topic LIKE ? ORDER BY d.created_at DESC LIMIT ?""",
                    (f"%{variant}%", limit),
                ).fetchall()
                results.extend(rows)
        deduped: list[tuple[Any, ...]] = []
        seen: set[tuple[Any, ...]] = set()
        for row in results:
            if row not in seen:
                seen.add(row)
                deduped.append(row)
        return deduped[:limit]

    def get_weighted_decision_candidates(
        self,
        topic: str,
        *,
        task_mode: str = "general",
        limit: int = 12,
    ) -> list[tuple[Any, ...]]:
        """Return inspectable decision history for bounded memory weighting."""
        cur = self.conn.cursor()
        terms = self._normalized_terms(topic)
        if not terms:
            return []
        rows: list[tuple[Any, ...]] = []
        for term in terms:
            for variant in self._recall_variants(term):
                rows.extend(
                    cur.execute(
                        """SELECT d.verdict,d.total,d.reasoning,h.topic,d.created_at,d.task_mode
                        FROM decisions d JOIN hypotheses h ON d.hypothesis_id=h.id
                        WHERE h.topic LIKE ? AND d.task_mode=?
                        ORDER BY d.created_at DESC LIMIT ?""",
                        (f"%{variant}%", task_mode, limit),
                    ).fetchall()
                )
        deduped: list[tuple[Any, ...]] = []
        seen: set[tuple[Any, ...]] = set()
        for row in rows:
            if row not in seen:
                seen.add(row)
                deduped.append(row)
        return deduped[:limit]

    def get_top_patterns(self, limit: int = 5) -> list[tuple[Any, ...]]:
        rows = (
            self.conn.cursor()
            .execute(
                "SELECT pattern,frequency,avg_score,last_verdict FROM dream_patterns "
                "ORDER BY frequency DESC LIMIT ?",
                (limit,),
            )
            .fetchall()
        )
        return cast(list[tuple[Any, ...]], rows)

    def get_strong_rules(self, limit: int = 5) -> list[tuple[Any, ...]]:
        rows = (
            self.conn.cursor()
            .execute(
                "SELECT rule,confidence,support_count FROM learned_rules "
                "WHERE confidence > 0.6 ORDER BY confidence DESC LIMIT ?",
                (limit,),
            )
            .fetchall()
        )
        return cast(list[tuple[Any, ...]], rows)

    def get_empathy_strength(self, id_a: str, id_b: str) -> float:
        key = f"{min(id_a, id_b)}_{max(id_a, id_b)}"
        row = (
            self.conn.cursor()
            .execute("SELECT relation_strength FROM empathy_map WHERE id=?", (key,))
            .fetchone()
        )
        return float(row[0]) if row else 0.5

    def save_failure_trace(
        self,
        cycle_id: str,
        stage: str,
        raw_input: str,
        reason: str,
        meta_tag: str = "",
        hypothesis_id: str = "",
        ethic_total: float = 0.0,
        *,
        depth: int = 0,
        parent_cycle_id: str | None = None,
        task_mode: str = "general",
        scale_role: str = "frame",
        learning_failure_class: str = "",
        learning_strategy: str = "",
        learning_lesson: str = "",
        learning_confidence: float = 0.0,
        learning_safe_to_reuse: bool = False,
    ) -> str:
        """Persist a failure plus its bounded, non-authoritative learning signal."""
        trace_id = f"ft_{uuid.uuid4().hex}"
        confidence = max(0.0, min(1.0, float(learning_confidence)))
        self.conn.execute(
            """INSERT INTO failure_traces
            (id,cycle_id,stage,raw_input,reason,meta_tag,hypothesis_id,ethic_total,created_at,
             depth,parent_cycle_id,task_mode,scale_role,learning_failure_class,
             learning_strategy,learning_lesson,learning_confidence,learning_safe_to_reuse)
             VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                trace_id,
                cycle_id,
                stage,
                raw_input,
                reason,
                meta_tag,
                hypothesis_id,
                ethic_total,
                datetime.now().isoformat(),
                depth,
                parent_cycle_id,
                task_mode,
                scale_role,
                learning_failure_class,
                learning_strategy,
                learning_lesson,
                confidence,
                int(learning_safe_to_reuse),
            ),
        )
        self.conn.commit()
        return trace_id

    def get_recent_failures(self, limit: int = 5) -> list[tuple[Any, ...]]:
        rows = (
            self.conn.cursor()
            .execute(
                """SELECT id,cycle_id,stage,reason,meta_tag,ethic_total,created_at,
            learning_failure_class,learning_strategy,learning_lesson,
            learning_confidence,learning_safe_to_reuse
            FROM failure_traces ORDER BY created_at DESC,rowid DESC LIMIT ?""",
                (limit,),
            )
            .fetchall()
        )
        return cast(list[tuple[Any, ...]], rows)

    def get_failures_at_depth(self, depth: int, limit: int = 20) -> list[tuple[Any, ...]]:
        rows = (
            self.conn.cursor()
            .execute(
                (
                    "SELECT id,cycle_id,parent_cycle_id,depth,task_mode,scale_role,stage,reason,"
                    "created_at FROM failure_traces WHERE depth=? ORDER BY created_at DESC,"
                    "rowid DESC LIMIT ?"
                ),
                (depth, limit),
            )
            .fetchall()
        )
        return cast(list[tuple[Any, ...]], rows)

    def save_scale_event(
        self,
        *,
        cycle_id: str,
        parent_cycle_id: str | None,
        depth: int,
        scale_role: str,
        task_mode: str,
        question: str,
        selected_claim: str = "",
        status: str = "started",
        stage_reached: str = "",
    ) -> str:
        self.conn.execute(
            """INSERT OR REPLACE INTO scale_events
            (cycle_id,parent_cycle_id,depth,scale_role,task_mode,question,selected_claim,status,stage_reached,created_at)
            VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (
                cycle_id,
                parent_cycle_id,
                depth,
                scale_role,
                task_mode,
                question,
                selected_claim,
                status,
                stage_reached,
                datetime.now().isoformat(),
            ),
        )
        self.conn.commit()
        return cycle_id

    def get_scale_events(
        self,
        cycle_id: str | None = None,
        parent_cycle_id: str | None = None,
        limit: int = 50,
    ) -> list[tuple[Any, ...]]:
        clauses: list[str] = []
        params: list[Any] = []
        if cycle_id is not None:
            clauses.append("cycle_id=?")
            params.append(cycle_id)
        if parent_cycle_id is not None:
            clauses.append("parent_cycle_id=?")
            params.append(parent_cycle_id)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        params.append(limit)
        rows = (
            self.conn.cursor()
            .execute(
                f"""SELECT cycle_id,parent_cycle_id,depth,scale_role,task_mode,
            question,selected_claim,status,stage_reached,created_at FROM scale_events {where}
            ORDER BY depth ASC,created_at ASC LIMIT ?""",
                params,
            )
            .fetchall()
        )
        return cast(list[tuple[Any, ...]], rows)


# --- FHM v2 deterministic, versioned memory engine -------------------------
from anne.memory.schema import (  # noqa: E402
    PROTOCOL,
    PROTOCOL_VERSION,
    SCHEMA_SQL,
    canonical_json,
    validate_envelope,
)


@dataclass(frozen=True)
class FractalQueryResult:
    records: tuple[dict[str, Any], ...]
    selected_tier: str | None
    conflicts: tuple[dict[str, Any], ...]
    freshness: bool
    confidence: float
    uncertainty: float


SOURCE_AUTHORITY = {
    "PRIMARY_OFFICIAL": 1.00,
    "PEER_REVIEWED_OR_SPEC": 0.90,
    "VERIFIED_INTERNAL": 0.85,
    "SECONDARY_WEB": 0.60,
    "UNVERIFIED_RAW": 0.30,
}
DOMAIN_TTL_DAYS = {
    "market_pricing": 7,
    "regulatory_tax": 30,
    "operations_project": 90,
    "technical_engineering": 180,
    "theoretical_axiom": 365,
}


_PII_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"\bTR\d{24}\b", re.IGNORECASE), "[REDACTED:IBAN]"),
    (re.compile(r"\b\d{11}\b"), "[REDACTED:TCKN]"),
    (re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE), "[REDACTED:EMAIL]"),
    (re.compile(r"(?<!\d)(?:\+?90|0)\s?5\d{2}\s?\d{3}\s?\d{2}\s?\d{2}(?!\d)"), "[REDACTED:PHONE]"),
    (re.compile(r"\bAIza[\w-]{20,}\b"), "[REDACTED:API_KEY]"),
)


def sanitize_l3_input(value: Any) -> Any:
    """Apply existing secret redaction plus deterministic PII masking."""
    if isinstance(value, str):
        result = redact_sensitive(value)
        for pattern, replacement in _PII_PATTERNS:
            result = pattern.sub(replacement, result)
        return result
    if isinstance(value, dict):
        return {sanitize_l3_input(key): sanitize_l3_input(item) for key, item in value.items()}
    if isinstance(value, list):
        return [sanitize_l3_input(item) for item in value]
    if isinstance(value, tuple):
        return tuple(sanitize_l3_input(item) for item in value)
    return value


class FractalMemoryEngine:
    """Production-oriented L1/L2/L3 memory with deterministic promotion rules."""

    auto_seal = False
    human_approval_required = True

    def __init__(self, db_path: str = ":memory:") -> None:
        self.conn = connect_memory(db_path)
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.conn.executescript(SCHEMA_SQL)
        self.conn.commit()

    @staticmethod
    def _now() -> str:
        return datetime.now(UTC).isoformat().replace("+00:00", "Z")

    @staticmethod
    def _hash_envelope(envelope: dict[str, Any]) -> str:
        canonical_content = {
            "protocol": envelope["protocol"],
            "protocol_version": envelope["protocol_version"],
            "memory_tier": envelope["memory_tier"],
            "domain": envelope["domain"],
            "key": envelope["key"],
            "payload": envelope["payload"],
        }
        return hashlib.sha256(canonical_json(canonical_content).encode("utf-8")).hexdigest()

    @staticmethod
    def _authority(source_type: str) -> float:
        return SOURCE_AUTHORITY.get(source_type, SOURCE_AUTHORITY["UNVERIFIED_RAW"])

    @classmethod
    def _freshness_valid(cls, domain: str, retrieved_at: str) -> bool:
        try:
            parsed = datetime.fromisoformat(retrieved_at.replace("Z", "+00:00"))
        except ValueError:
            return False
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=UTC)
        ttl = DOMAIN_TTL_DAYS.get(domain, 60)
        return datetime.now(UTC) - parsed <= timedelta(days=ttl)

    def _event(
        self,
        record_id: str | None,
        event_type: str,
        actor: str,
        previous: str | None,
        new: str | None,
        payload: dict[str, Any],
    ) -> None:
        self.conn.execute(
            "INSERT INTO memory_events VALUES (?,?,?,?,?,?,?,?)",
            (
                f"evt_{uuid.uuid4().hex}",
                record_id,
                event_type,
                actor,
                previous,
                new,
                canonical_json(payload),
                self._now(),
            ),
        )

    def _row(self, record_id: str) -> dict[str, Any]:
        row = self.conn.execute(
            "SELECT record_id,protocol,protocol_version,memory_tier,domain,record_key,status,"
            "payload_json,filter_json,lifecycle_json,content_hash,created_at,updated_at,supersedes_record_id "  # noqa: E501
            "FROM memory_records WHERE record_id=?",
            (record_id,),
        ).fetchone()
        if row is None:
            raise KeyError(record_id)
        return {
            "record_id": row[0],
            "protocol": row[1],
            "protocol_version": row[2],
            "memory_tier": row[3],
            "domain": row[4],
            "key": row[5],
            "status": row[6],
            "payload": json.loads(row[7]),
            "anne_ai_filter": json.loads(row[8]),
            "lifecycle": json.loads(row[9]),
            "content_hash": row[10],
            "created_at": row[11],
            "updated_at": row[12],
            "supersedes": row[13],
        }

    def ingest_l3(
        self,
        domain: str,
        key: str,
        payload: dict[str, Any],
        evidence: list[dict[str, Any]] | None = None,
        *,
        retrieved_at: str | None = None,
    ) -> str:
        if not domain.strip() or not key.strip():
            raise ValueError("domain and key are required")
        if not isinstance(payload, dict) or len(canonical_json(payload)) > 1_000_000:
            raise ValueError("payload must be an object smaller than 1 MB")
        now = retrieved_at or self._now()
        clean_payload = sanitize_l3_input(payload)
        clean_evidence = [sanitize_l3_input(item) for item in (evidence or [])]
        record_id = f"mem_{uuid.uuid4().hex}"
        envelope: dict[str, Any] = {
            "protocol": PROTOCOL,
            "protocol_version": PROTOCOL_VERSION,
            "record_id": record_id,
            "memory_tier": "L3",
            "domain": domain,
            "key": key,
            "payload": clean_payload,
            "evidence": clean_evidence,
            "anne_ai_filter": {
                "truth_confidence": 0.0,
                "source_independence": 0.0,
                "freshness_valid": True,
                "provenance_complete": bool(clean_evidence),
                "safety_policy": "PASS",
            },
            "lifecycle": {
                "status": "CANDIDATE",
                "created_at": now,
                "updated_at": now,
                "supersedes": None,
            },
        }
        validate_envelope(envelope)
        content_hash = self._hash_envelope(envelope)
        existing = self.conn.execute(
            "SELECT record_id FROM memory_records "
            "WHERE domain=? AND record_key=? AND content_hash=? "
            "AND status NOT IN ('ARCHIVED','REVOKED') LIMIT 1",
            (domain, key, content_hash),
        ).fetchone()
        if existing is not None:
            return str(existing[0])
        with self.conn:
            self.conn.execute(
                "INSERT INTO memory_records VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    record_id,
                    PROTOCOL,
                    PROTOCOL_VERSION,
                    "L3",
                    domain,
                    key,
                    "CANDIDATE",
                    canonical_json(clean_payload),
                    canonical_json(envelope["anne_ai_filter"]),
                    canonical_json(envelope["lifecycle"]),
                    content_hash,
                    now,
                    now,
                    None,
                ),
            )
            for item in clean_evidence:
                self._insert_evidence(record_id, item, now)
            self._detect_conflicts(record_id, domain, key)
            self._event(record_id, "INGEST_L3", "SYSTEM", None, "CANDIDATE", {})
        return record_id

    def _insert_evidence(self, record_id: str, item: dict[str, Any], fallback_time: str) -> None:
        required = ("source_id", "source_type", "independence_group", "evidence_kind", "provenance")
        if any(not str(item.get(field, "")).strip() for field in required):
            raise ValueError(
                "evidence requires source, type, independence group, kind and provenance"
            )
        self.conn.execute(
            "INSERT INTO memory_evidence VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                f"ev_{uuid.uuid4().hex}",
                record_id,
                item["source_id"],
                item["source_type"],
                item["independence_group"],
                item.get("observed_at"),
                item.get("retrieved_at", fallback_time),
                item.get("jurisdiction", ""),
                item["evidence_kind"],
                max(0.0, min(1.0, float(item.get("confidence", 0.0)))),
                item["provenance"],
                self._authority(item["source_type"]),
            ),
        )

    def _detect_conflicts(self, record_id: str, domain: str, key: str) -> None:
        current = self.conn.execute(
            "SELECT record_id,payload_json FROM memory_records WHERE domain=? AND record_key=? "
            "AND record_id<>? AND status NOT IN ('ARCHIVED','REVOKED')",
            (domain, key, record_id),
        ).fetchall()
        payload = self.conn.execute(
            "SELECT payload_json FROM memory_records WHERE record_id=?", (record_id,)
        ).fetchone()[0]
        for other_id, other_payload in current:
            if other_payload == payload:
                continue
            pair = tuple(sorted((record_id, other_id)))
            exists = self.conn.execute(
                "SELECT 1 FROM memory_conflicts WHERE record_a=? AND record_b=? AND status='OPEN'",
                pair,
            ).fetchone()
            if not exists:
                self.conn.execute(
                    "INSERT INTO memory_conflicts VALUES (?,?,?,?,?,?,?,?,?)",
                    (
                        f"conf_{uuid.uuid4().hex}",
                        pair[0],
                        pair[1],
                        "PAYLOAD_MISMATCH",
                        "HIGH",
                        "OPEN",
                        None,
                        self._now(),
                        None,
                    ),
                )

    def evaluate_promotion_l2(self, record_id: str) -> bool:
        record = self._row(record_id)
        if record["memory_tier"] != "L3" or record["status"] not in {"CANDIDATE", "VERIFIED"}:
            return False
        evidence = self.conn.execute(
            "SELECT independence_group,provenance,retrieved_at FROM memory_evidence WHERE record_id=?",  # noqa: E501
            (record_id,),
        ).fetchall()
        valid = (
            len(evidence) >= 3
            and len({row[0] for row in evidence}) >= 2
            and all(row[1] and self._freshness_valid(record["domain"], row[2]) for row in evidence)
        )
        conflict = self.conn.execute(
            "SELECT 1 FROM memory_conflicts c "
            "WHERE (c.record_a=? OR c.record_b=?) AND c.status='OPEN' "
            "AND NOT EXISTS (SELECT 1 FROM memory_records old "
            "WHERE (old.record_id=c.record_a OR old.record_id=c.record_b) "
            "AND old.record_id<>? AND old.memory_tier='L1' AND old.status='SEALED') LIMIT 1",
            (record_id, record_id, record_id),
        ).fetchone()
        if not valid or conflict:
            return False
        now = self._now()
        with self.conn:
            self.conn.execute(
                "UPDATE memory_records SET memory_tier='L2', status='VERIFIED', updated_at=? WHERE record_id=?",  # noqa: E501
                (now, record_id),
            )
            self._event(record_id, "PROMOTE_L2", "SYSTEM", record["status"], "VERIFIED", {})
        return True

    def propose_seal_candidate(self, record_id: str) -> bool:
        record = self._row(record_id)
        if record["memory_tier"] != "L2" or record["status"] != "VERIFIED":
            return False
        evidence = self.conn.execute(
            "SELECT confidence,source_authority,independence_group,provenance,retrieved_at "
            "FROM memory_evidence WHERE record_id=?",
            (record_id,),
        ).fetchall()
        if not evidence:
            return False
        truth = sum(row[0] for row in evidence) / len(evidence)
        independence = min(1.0, len({row[2] for row in evidence}) / 2)
        filters = {
            "truth_confidence": truth,
            "source_independence": independence,
            "freshness_valid": all(
                self._freshness_valid(record["domain"], row[4]) for row in evidence
            ),
            "provenance_complete": all(row[3] for row in evidence),
            "safety_policy": "PASS",
        }
        if not (
            truth >= 0.85
            and independence >= 0.70
            and filters["freshness_valid"]
            and filters["provenance_complete"]
            and filters["safety_policy"] == "PASS"
        ):
            return False
        now = self._now()
        with self.conn:
            self.conn.execute(
                "UPDATE memory_records SET status='SEAL_CANDIDATE', filter_json=?, updated_at=? WHERE record_id=?",  # noqa: E501
                (canonical_json(filters), now, record_id),
            )
            self._event(
                record_id, "SEAL_CANDIDATE", "SYSTEM", "VERIFIED", "SEAL_CANDIDATE", filters
            )
        return True

    def approve_seal(self, record_id: str, approver_id: str, approver_role: str) -> str:
        if not approver_id.strip() or approver_role not in {"ARCHITECT", "HUMAN_ADMIN"}:
            self._event(
                record_id,
                "SEAL_REJECTED",
                approver_id or "UNKNOWN",
                None,
                None,
                {"approver_role": approver_role},
            )
            self.conn.commit()
            raise PermissionError("only ARCHITECT or HUMAN_ADMIN may approve sealing")
        record = self._row(record_id)
        if record["status"] != "SEAL_CANDIDATE":
            raise ValueError("record must be SEAL_CANDIDATE")
        now = self._now()
        with self.conn:
            previous = self.conn.execute(
                "SELECT record_id FROM memory_records WHERE domain=? AND record_key=? AND memory_tier='L1' AND status='SEALED'",  # noqa: E501
                (record["domain"], record["key"]),
            ).fetchall()
            self.conn.execute(
                "UPDATE memory_records SET memory_tier='L1', status='SEALED', updated_at=? WHERE record_id=?",  # noqa: E501
                (now, record_id),
            )
            for (old_id,) in previous:
                self.conn.execute(
                    "UPDATE memory_records SET status='SUPERSEDED', updated_at=? WHERE record_id=?",
                    (now, old_id),
                )
                self._event(
                    old_id,
                    "SUPERSEDE",
                    approver_id,
                    "SEALED",
                    "SUPERSEDED",
                    {"superseded_by": record_id},
                )
            self._event(
                record_id,
                "SEAL_APPROVED",
                approver_id,
                "SEAL_CANDIDATE",
                "SEALED",
                {"role": approver_role},
            )
        return record_id

    def query_fractal(self, domain: str, key: str) -> FractalQueryResult:
        rows = self.conn.execute(
            "SELECT record_id FROM memory_records WHERE domain=? AND record_key=? AND status NOT IN ('ARCHIVED','REVOKED')",  # noqa: E501
            (domain, key),
        ).fetchall()
        records = tuple(self._row(row[0]) for row in rows)
        if not records:
            return FractalQueryResult((), None, (), False, 0.0, 1.0)
        priority = {"L1": 0, "L2": 1, "L3": 2}
        ordered = tuple(sorted(records, key=lambda item: priority[item["memory_tier"]]))
        selected = ordered[0]
        conflicts = tuple(
            self.conn.execute(
                "SELECT conflict_id,record_a,record_b,conflict_type,severity,status FROM memory_conflicts "  # noqa: E501
                "WHERE (record_a=? OR record_b=?) AND status='OPEN'",
                (selected["record_id"], selected["record_id"]),
            ).fetchall()
        )
        conflict_dicts = tuple(
            {
                "conflict_id": row[0],
                "record_a": row[1],
                "record_b": row[2],
                "conflict_type": row[3],
                "severity": row[4],
                "status": row[5],
            }
            for row in conflicts
        )
        confidence = float(selected["anne_ai_filter"].get("truth_confidence", 0.0))
        fresh = self._freshness_valid(domain, selected["updated_at"])
        uncertainty = max(0.0, min(1.0, 1.0 - confidence + (0.25 if conflicts else 0.0)))
        return FractalQueryResult(
            ordered, selected["memory_tier"], conflict_dicts, fresh, confidence, uncertainty
        )

    def archive_stale_l3(self, days: int = 30) -> list[str]:
        if days < 0:
            raise ValueError("days must be non-negative")
        cutoff = datetime.now(UTC) - timedelta(days=days)
        candidates = self.conn.execute(
            "SELECT record_id,created_at,status FROM memory_records WHERE memory_tier='L3' AND status IN ('CANDIDATE','STALE')"  # noqa: E501
        ).fetchall()
        archived: list[str] = []
        with self.conn:
            for record_id, created_at, status in candidates:
                parsed = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
                if parsed <= cutoff:
                    self.conn.execute(
                        "UPDATE memory_records SET status='ARCHIVED', updated_at=? WHERE record_id=?",  # noqa: E501
                        (self._now(), record_id),
                    )
                    self._event(record_id, "ARCHIVE_L3", "SYSTEM", status, "ARCHIVED", {})
                    archived.append(record_id)
        return archived

    def restore_archived(self, record_id: str) -> bool:
        record = self._row(record_id)
        if record["memory_tier"] != "L3" or record["status"] != "ARCHIVED":
            return False
        with self.conn:
            self.conn.execute(
                "UPDATE memory_records SET status='CANDIDATE', updated_at=? WHERE record_id=?",
                (self._now(), record_id),
            )
            self._event(record_id, "RESTORE_L3", "SYSTEM", "ARCHIVED", "CANDIDATE", {})
        return True


__all__ = ["FractalMemory", "FractalMemoryEngine", "FractalQueryResult", "sanitize_l3_input"]
