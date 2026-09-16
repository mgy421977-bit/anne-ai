"""ANNE V1 first-run / self-setup.

Prepares environment, folders, SQLite memory, config template, and reports
system readiness. Does NOT alter cognitive authority, epistemic rules, or
authorization policy.
"""

from __future__ import annotations

import os
import socket
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from anne.memory.paths import resolve_memory_location


CONFIG_FILENAME = "anne_config.env"
CONFIG_EXAMPLE = "anne_config.env.example"
DEFAULT_DATA_DIR = "anne_data"
DEFAULT_DB = "anne_web.db"
DEFAULT_PORT = 8000


@dataclass
class CheckItem:
    name: str
    ok: bool
    detail: str = ""
    warning: bool = False


@dataclass
class SelfSetupReport:
    checks: list[CheckItem] = field(default_factory=list)
    ready: bool = False
    config_path: str = ""
    data_dir: str = ""
    db_path: str = ""
    memory_durable: bool = False
    memory_source: str = ""
    port: int = DEFAULT_PORT
    provider: str = ""
    messages: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "ready": self.ready,
            "provider": self.provider,
            "config_path": self.config_path,
            "data_dir": self.data_dir,
            "db_path": self.db_path,
            "memory_durable": self.memory_durable,
            "memory_source": self.memory_source,
            "port": self.port,
            "checks": [
                {
                    "name": c.name,
                    "ok": c.ok,
                    "warning": c.warning,
                    "detail": c.detail,
                }
                for c in self.checks
            ],
            "messages": list(self.messages),
        }

    def print_human(self) -> None:
        print()
        print("=" * 46)
        print("  ANNE SYSTEM CHECK")
        print("=" * 46)
        for c in self.checks:
            if c.ok and not c.warning:
                mark = "OK"
            elif c.ok and c.warning:
                mark = "WARN"
            else:
                mark = "FAIL"
            print(f"  [{mark:4}] {c.name}: {c.detail or ('ready' if c.ok else 'missing')}")
        print("-" * 46)
        if self.ready:
            print("  ANNE READY")
            print(f"  Memory: {self.db_path}")
            print(f"  Durable: {'yes' if self.memory_durable else 'NO (temporary)'}")
            print(f"  Open Chrome: http://127.0.0.1:{self.port}")
        else:
            print("  ANNE NOT READY")
            for m in self.messages:
                print(f"  -> {m}")
        print("=" * 46)
        print()


def _project_root() -> Path:
    return Path(os.getcwd()).resolve()


def _ensure_dirs(root: Path) -> tuple[Path, Path]:
    data = root / DEFAULT_DATA_DIR
    logs = data / "logs"
    data.mkdir(parents=True, exist_ok=True)
    logs.mkdir(parents=True, exist_ok=True)
    return data, logs


def _write_config_example(root: Path) -> Path:
    example = root / CONFIG_EXAMPLE
    content = (
        "# ANNE V1 local configuration\n"
        "# Copy to anne_config.env and fill in values. Never commit anne_config.env.\n\n"
        "# Language provider: openai | xai | openrouter | gemini\n"
        "ANNE_WEB_PROVIDER=openai\n\n"
        "# ChatGPT / OpenAI\n"
        "OPENAI_API_KEY=\n"
        "ANNE_OPENAI_MODEL=gpt-4o-mini\n\n"
        "# Grok / xAI\n"
        "XAI_API_KEY=\n"
        "ANNE_XAI_MODEL=grok-2-latest\n\n"
        "OPENROUTER_API_KEY=\n"
        "GEMINI_API_KEY=\n\n"
        "ANNE_MITOS_URL=\n"
        "ANNE_CHATGPT_URL=\n\n"
        "# External durable memory root (e.g. E:/ANNE)\n"
        "ANNE_MEMORY_ROOT=\n"
        "ANNE_WEB_DB=\n"
        "ANNE_WEB_MAX_QUEUE=32\n"
        "ANNE_WEB_PORT=8000\n"
    )
    if not example.exists():
        example.write_text(content, encoding="utf-8")
    return example


def _load_config_into_environ(root: Path) -> Path | None:
    path = root / CONFIG_FILENAME
    if not path.exists():
        return None
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value
    return path


def _port_available(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind(("127.0.0.1", port))
            return True
        except OSError:
            return False


def _check_packages() -> tuple[bool, str]:
    missing: list[str] = []
    for mod in ("fastapi", "uvicorn", "pydantic"):
        try:
            __import__(mod)
        except ImportError:
            missing.append(mod)
    if missing:
        return False, f"missing packages: {', '.join(missing)} (pip install -e '.[api]')"
    return True, "fastapi/uvicorn available"


def _init_memory(db_path: Path) -> tuple[bool, str]:
    try:
        from anne.memory.local_memory import LocalMemory

        mem = LocalMemory(db_path)
        _ = mem.context(limit=1)
        _ = mem.recent_experiences(limit=1)
        return True, str(db_path)
    except Exception as exc:  # noqa: BLE001
        return False, f"memory init failed: {exc}"


def _provider_status() -> tuple[str, bool, str, bool]:
    name = (os.getenv("ANNE_WEB_PROVIDER") or "").strip().lower()
    if not name:
        return "none", False, "ANNE_WEB_PROVIDER not set (openai|xai|openrouter|gemini)", False

    key_map = {
        "openai": ("OPENAI_API_KEY", "CHATGPT_API_KEY"),
        "chatgpt": ("OPENAI_API_KEY", "CHATGPT_API_KEY"),
        "xai": ("XAI_API_KEY", "GROK_API_KEY"),
        "grok": ("XAI_API_KEY", "GROK_API_KEY"),
        "openrouter": ("OPENROUTER_API_KEY",),
        "gemini": ("GEMINI_API_KEY",),
    }
    if name == "chatgpt":
        name = "openai"
    if name == "grok":
        name = "xai"

    keys = key_map.get(name)
    if keys is None:
        return name, False, f"unsupported provider '{name}'", False
    if any(os.getenv(k, "").strip() for k in keys):
        return name, True, f"{name} key present (value hidden)", False
    return name, False, f"{name} API key missing", False


def run_self_setup(*, root: Path | None = None, port: int | None = None) -> SelfSetupReport:
    root = root or _project_root()
    report = SelfSetupReport()
    report.port = port or int(os.getenv("ANNE_WEB_PORT", str(DEFAULT_PORT)))

    py_ok = sys.version_info >= (3, 12)
    report.checks.append(
        CheckItem("Python Runtime", py_ok, f"{sys.version.split()[0]} (need 3.12+)")
    )
    if not py_ok:
        report.messages.append("Install Python 3.12+ and re-run START_ANNE.bat")

    pkg_ok, pkg_detail = _check_packages()
    report.checks.append(CheckItem("API Packages", pkg_ok, pkg_detail))
    if not pkg_ok:
        report.messages.append(pkg_detail)

    example = _write_config_example(root)
    loaded = _load_config_into_environ(root)
    report.config_path = str(root / CONFIG_FILENAME)
    if loaded is None:
        report.checks.append(
            CheckItem(
                "Configuration",
                False,
                f"create {CONFIG_FILENAME} from {example.name} and set API keys",
            )
        )
        report.messages.append(
            f"Copy {CONFIG_EXAMPLE} to {CONFIG_FILENAME}, set ANNE_WEB_PROVIDER and API key"
        )
    else:
        report.checks.append(CheckItem("Configuration", True, str(loaded.name)))

    location = resolve_memory_location(project_fallback=root / DEFAULT_DATA_DIR)
    report.data_dir = str(location.root)
    report.db_path = str(location.db_path)
    report.memory_durable = location.durable
    report.memory_source = location.source
    if location.exists_prior:
        report.checks.append(
            CheckItem("ANNE Memory Root", True, f"Existing ANNE Memory Found: {location.root}")
        )
    elif location.durable:
        report.checks.append(
            CheckItem("ANNE Memory Root", True, f"new durable root prepared: {location.root}")
        )
    else:
        report.checks.append(
            CheckItem(
                "ANNE Memory Root",
                True,
                location.message or "Kalıcı ANNE Memory bulunamadı.",
                warning=True,
            )
        )
        report.messages.append(location.message)

    db_env = (os.getenv("ANNE_WEB_DB") or "").strip()
    if db_env:
        db_path = Path(db_env)
        if not db_path.is_absolute():
            db_path = root / db_path
    else:
        db_path = location.db_path
    db_path.parent.mkdir(parents=True, exist_ok=True)
    report.db_path = str(db_path)
    os.environ["ANNE_WEB_DB"] = str(db_path)

    mem_ok, mem_detail = _init_memory(db_path)
    report.checks.append(CheckItem("Memory", mem_ok, mem_detail))
    report.checks.append(
        CheckItem("Experience Store", mem_ok, "experiences table ready" if mem_ok else mem_detail)
    )
    report.checks.append(CheckItem("Logs", True, str(location.root / "logs")))
    if location.durable and mem_ok:
        report.checks.append(
            CheckItem("Memory Durability", True, "persistent external/local ANNE root")
        )
    else:
        report.checks.append(
            CheckItem(
                "Memory Durability",
                True,
                "temporary — not durable across machines until ANNE_MEMORY_ROOT is set",
                warning=True,
            )
        )

    try:
        from anne.core.conversation import CognitiveConversation, EpistemicPolicy  # noqa: F401

        report.checks.append(CheckItem("Cognitive Runtime", True, "CognitiveConversation loaded"))
    except Exception as exc:  # noqa: BLE001
        report.checks.append(CheckItem("Cognitive Runtime", False, str(exc)))
        report.messages.append(f"Cognitive runtime import failed: {exc}")

    pname, p_ok, p_detail, p_warn = _provider_status()
    report.provider = pname
    report.checks.append(CheckItem("Language Interface", p_ok, p_detail, warning=p_warn))
    if not p_ok:
        report.messages.append(p_detail)

    research_set = bool(
        os.getenv("ANNE_MITOS_URL", "").strip() or os.getenv("ANNE_CHATGPT_URL", "").strip()
    )
    report.checks.append(
        CheckItem(
            "Research Interface",
            True,
            "configured" if research_set else "optional adapters not set (ANNE may skip external research)",
            warning=not research_set,
        )
    )

    port_free = _port_available(report.port)
    report.checks.append(
        CheckItem(
            "Web Port",
            True,
            f"127.0.0.1:{report.port} {'available' if port_free else 'in use (server may already be running)'}",
            warning=not port_free,
        )
    )
    report.checks.append(CheckItem("Web Interface", True, "uvicorn anne.api.web_tinker:app"))
    report.checks.append(
        CheckItem(
            "Chrome Bridge",
            True,
            f"http://127.0.0.1:{report.port}",
            warning=not p_ok,
        )
    )

    critical_ok = all(
        c.ok
        for c in report.checks
        if c.name
        in {
            "Python Runtime",
            "API Packages",
            "Configuration",
            "Memory",
            "Cognitive Runtime",
            "Language Interface",
        }
    )
    report.ready = critical_ok
    return report


def main() -> int:
    report = run_self_setup()
    report.print_human()
    return 0 if report.ready else 1


if __name__ == "__main__":
    raise SystemExit(main())
