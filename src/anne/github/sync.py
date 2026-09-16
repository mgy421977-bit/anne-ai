"""Safe GitHub repository sync for ANNE V1.

The installed ANNE can keep its code connected to the public upstream repository
and fetch fast-forward updates on startup. Experience sharing is deliberately
separate: only explicitly anonymized, non-content telemetry is exported, and
no GitHub write is attempted from the client because a public repository cannot
accept anonymous writes safely.
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

DEFAULT_REPOSITORY = "https://github.com/mgy421977-bit/anne-ai.git"
DEFAULT_BRANCH = "main"


def _run_git(cwd: Path, *args: str, timeout: int = 30) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args], cwd=cwd, capture_output=True, text=True, timeout=timeout, check=False
    )


def ensure_repository_connection(root: Path) -> dict[str, Any]:
    """Connect the installation to upstream and safely fast-forward main when possible."""
    repo_url = (os.getenv("ANNE_GITHUB_REPOSITORY") or DEFAULT_REPOSITORY).strip()
    branch = (os.getenv("ANNE_GITHUB_BRANCH") or DEFAULT_BRANCH).strip()
    result: dict[str, Any] = {"repository": repo_url, "branch": branch, "updated": False}
    if not (root / ".git").is_dir():
        result["status"] = "not_git_installation"
        return result
    try:
        remote = _run_git(root, "remote", "get-url", "origin")
        if remote.returncode != 0:
            add = _run_git(root, "remote", "add", "origin", repo_url)
            if add.returncode != 0:
                result["status"] = "remote_setup_failed"
                result["detail"] = add.stderr.strip()
                return result
        elif remote.stdout.strip() != repo_url:
            set_url = _run_git(root, "remote", "set-url", "origin", repo_url)
            if set_url.returncode != 0:
                result["status"] = "remote_update_failed"
                result["detail"] = set_url.stderr.strip()
                return result
        fetch = _run_git(root, "fetch", "--prune", "origin", branch, timeout=60)
        if fetch.returncode != 0:
            result["status"] = "fetch_failed"
            result["detail"] = fetch.stderr.strip()
            return result
        current = _run_git(root, "branch", "--show-current")
        current_branch = current.stdout.strip()
        result["current_branch"] = current_branch
        if current_branch != branch:
            result["status"] = "update_available_not_applied"
            result["detail"] = f"installation branch is {current_branch or 'detached'}, expected {branch}"
            return result
        pull = _run_git(root, "pull", "--ff-only", "origin", branch, timeout=60)
        result["updated"] = pull.returncode == 0 and "Already up to date" not in pull.stdout
        result["status"] = "updated" if result["updated"] else "up_to_date"
        if pull.returncode != 0:
            result["status"] = "update_not_applied"
            result["detail"] = pull.stderr.strip()
        return result
    except (OSError, subprocess.SubprocessError) as exc:
        result["status"] = "git_unavailable"
        result["detail"] = str(exc)
        return result


def anonymize_experience(experience: dict[str, Any], *, version: str) -> dict[str, Any]:
    """Convert an experience into non-content telemetry.

    User text, answers, evidence, identifiers, and memory contents are excluded.
    """
    status = str(experience.get("comparison_status") or "UNKNOWN").upper()
    confidence = experience.get("confidence")
    try:
        confidence_bucket = round(float(confidence), 1) if confidence is not None else None
    except (TypeError, ValueError):
        confidence_bucket = None
    return {
        "schema": "anne-experience-v1",
        "version": version,
        "timestamp": datetime.now(UTC).date().isoformat(),
        "comparison_status": status,
        "research_used": bool(experience.get("research_used", False)),
        "previous_answer_used": bool(experience.get("previous_answer_used", False)),
        "previous_answer_changed": bool(experience.get("previous_answer_changed", False)),
        "uncertainty_detected": bool(experience.get("uncertainty_detected", False)),
        "anne_evaluation_formed": bool(experience.get("anne_evaluation_formed", False)),
        "confidence_bucket": confidence_bucket,
    }


def queue_anonymized_experience(root: Path, experience: dict[str, Any], *, version: str) -> Path:
    """Append sanitized experience telemetry to an outbox for a future intake service."""
    outbox = root / "experiences" / "anonymous_outbox.jsonl"
    outbox.parent.mkdir(parents=True, exist_ok=True)
    payload = anonymize_experience(experience, version=version)
    with outbox.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n")
    return outbox


def installation_fingerprint(installation_id: str) -> str:
    """Return a one-way, non-reversible-ish contribution grouping identifier."""
    return hashlib.sha256(installation_id.encode("utf-8")).hexdigest()[:16]
