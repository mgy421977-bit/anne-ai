#!/usr/bin/env python3
"""ANNE Cognitive Loop micro-simulation.

Simulates the proposed non-token-centric internal loop:
Perception -> Sense -> Concept -> Inspect -> Relation -> Memory -> Understand
-> Reason -> Affect -> Decide -> Act -> Learn.

The experiment is deliberately symbolic/state-based. Tokens are not used as
an internal state representation. The benchmark measures reuse after learning,
not LLM quality or energy consumption.

  python benchmarks/scripts/run_cognitive_loop.py
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RESULTS = ROOT / "benchmarks" / "results"


@dataclass
class CognitiveMemory:
    concepts: dict[str, dict] = field(default_factory=dict)
    relations: list[tuple[str, str, str]] = field(default_factory=list)
    experiences: list[dict] = field(default_factory=list)

    def learn(self, concept: str, attributes: dict, relations: list[tuple[str, str, str]]) -> None:
        self.concepts[concept] = dict(attributes)
        for relation in relations:
            if relation not in self.relations:
                self.relations.append(relation)

    def recall(self, concept: str) -> dict | None:
        return self.concepts.get(concept)


class CognitiveLoop:
    def __init__(self) -> None:
        self.memory = CognitiveMemory()

    def run(self, observation: dict) -> dict:
        trace = []
        trace.append("ALGILA")
        sensed = dict(observation)
        trace.append("DUY")

        concept = sensed["concept"]
        trace.append("KAVRAM")
        recalled = self.memory.recall(concept)
        trace.append("BAK")

        relations = sensed.get("relations", [])
        trace.append("İLİŞKİ")
        trace.append("BELLEK")
        reused = recalled is not None

        if recalled is None:
            knowledge = dict(sensed.get("attributes", {}))
            reason = f"new:{concept}"
        else:
            knowledge = dict(recalled)
            reason = f"reused:{concept}"

        trace.append("ANLA")
        trace.append("MUHAKEME")
        affect = "consistent" if reused else "uncertain"
        trace.append("HİSSET")
        decision = "ACT_WITH_KNOWN_STRUCTURE" if reused else "LEARN_THEN_ACT"
        trace.append("KARAR")
        action = "reuse" if reused else "learn"
        trace.append("YAP")

        if not reused:
            self.memory.learn(concept, knowledge, relations)
        self.memory.experiences.append({"concept": concept, "reused": reused, "decision": decision})
        trace.append("ÖĞREN")

        return {
            "concept": concept,
            "reused_memory": reused,
            "decision": decision,
            "action": action,
            "affective_state": affect,
            "reasoning": reason,
            "trace": trace,
            "internal_token_count": 0,
        }


def main() -> int:
    loop = CognitiveLoop()
    observation = {
        "concept": "solar_storage",
        "attributes": {"storage": "battery", "purpose": "store_energy"},
        "relations": [("solar_storage", "stores", "energy")],
    }

    first = loop.run(observation)
    second = loop.run({"concept": "solar_storage", "relations": observation["relations"]})

    payload = {
        "experiment": "ANNE Cognitive Loop Micro-Simulation",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "architecture": ["ALGILA", "DUY", "KAVRAM", "BAK", "İLİŞKİ", "BELLEK", "ANLA", "MUHAKEME", "HİSSET", "KARAR", "YAP", "ÖĞREN"],
        "claim_scope": "symbolic cognitive organization; not an LLM or energy benchmark",
        "first_cycle": first,
        "second_cycle": second,
        "reuse_gain": second["reused_memory"] and not first["reused_memory"],
        "internal_token_count": 0,
    }

    RESULTS.mkdir(parents=True, exist_ok=True)
    out = RESULTS / f"{datetime.now(timezone.utc).strftime('%Y-%m-%d')}_cognitive_loop.json"
    out.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"first_reused": first["reused_memory"], "second_reused": second["reused_memory"], "reuse_gain": payload["reuse_gain"], "internal_token_count": 0}, ensure_ascii=False, indent=2))
    print(f"Wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
