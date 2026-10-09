"""Minimal local desktop shell for the ANNE cognitive runtime.

The desktop layer is intentionally thin. It exposes the guarded runtime,
local media context and cooperative workload controls without adding
cognitive, safety or agency authority.
"""
from __future__ import annotations

import threading
import tkinter as tk
from tkinter import filedialog, ttk
from typing import Any

from anne.core.decision_loop import DecisionLoop
from anne.core.local_media import LocalMediaLauncher
from anne.core.media_context import MediaContext


APP_TITLE = "ANNE AI — Adaptive Neural Nexus Engine"
STAGES = (
    "FAIL_FAST",
    "DUY",
    "BAK",
    "GÖR",
    "MITOS",
    "SELECT",
    "ANLA",
    "HİSSET",
    "YAP",
)


class AnneDesktop(tk.Tk):
    """Small laptop-friendly desktop shell around ANNE's guarded runtime."""

    def __init__(self, loop: DecisionLoop | None = None) -> None:
        super().__init__()
        self.loop = loop
        self.media_launcher = LocalMediaLauncher()
        self.media_context: MediaContext | None = None
        self.title(APP_TITLE)
        self.geometry("980x780")
        self.minsize(820, 680)
        self._build_ui()

    def _build_ui(self) -> None:
        root = ttk.Frame(self, padding=18)
        root.pack(fill="both", expand=True)

        header = ttk.Frame(root)
        header.pack(fill="x")
        ttk.Label(header, text="ANNE AI", font=("Segoe UI", 24, "bold")).pack(anchor="w")
        ttk.Label(
            header,
            text="Adaptive Neural Nexus Engine · Local Runtime",
        ).pack(anchor="w", pady=(2, 10))

        status = ttk.Frame(root)
        status.pack(fill="x", pady=(0, 12))
        ttk.Label(status, text="RUNTIME: LOCAL / ADAPTIVE").pack(side="left")
        self.status_var = tk.StringVar(value="READY")
        ttk.Label(status, textvariable=self.status_var).pack(side="right")

        media = ttk.LabelFrame(root, text="Media Context", padding=10)
        media.pack(fill="x", pady=(0, 12))
        self.media_var = tk.StringVar(value="No local media selected.")
        ttk.Label(media, textvariable=self.media_var).pack(side="left", fill="x", expand=True)
        ttk.Button(media, text="OPEN MEDIA", command=self._select_media).pack(side="right")
        ttk.Button(media, text="PLAY", command=self._play_media).pack(side="right", padx=(0, 8))

        context = ttk.Frame(root)
        context.pack(fill="x", pady=(0, 12))
        ttk.Label(context, text="Scene time (HH:MM:SS)").pack(side="left")
        self.time_var = tk.StringVar(value="00:00:00")
        ttk.Entry(context, textvariable=self.time_var, width=12).pack(side="left", padx=(6, 14))
        ttk.Label(context, text="Scene label").pack(side="left")
        self.scene_var = tk.StringVar()
        ttk.Entry(context, textvariable=self.scene_var, width=24).pack(side="left", padx=6)

        ttk.Label(root, text="Input / Discussion").pack(anchor="w")
        self.input_text = tk.Text(root, height=5, wrap="word", font=("Segoe UI", 11))
        self.input_text.pack(fill="x", pady=(4, 10))
        self.input_text.insert(
            "1.0",
            "Merhaba ANNE. Kendini güvenli ve sınırlı bir bilişsel çevrim içinde test et.",
        )

        self.run_button = ttk.Button(
            root, text="RUN COGNITIVE CYCLE", command=self._start_cycle
        )
        self.run_button.pack(anchor="e", pady=(0, 14))

        ttk.Label(root, text="Cognitive Trace").pack(anchor="w")
        trace_frame = ttk.Frame(root)
        trace_frame.pack(fill="x", pady=(4, 12))
        self.stage_vars: dict[str, tk.StringVar] = {}
        for stage in STAGES:
            var = tk.StringVar(value=f"○ {stage}")
            self.stage_vars[stage] = var
            ttk.Label(trace_frame, textvariable=var, width=13).pack(side="left", padx=2)

        ttk.Label(root, text="Result").pack(anchor="w")
        self.result_text = tk.Text(
            root, height=14, wrap="word", state="disabled", font=("Consolas", 10)
        )
        self.result_text.pack(fill="both", expand=True)

    def _select_media(self) -> None:
        path = filedialog.askopenfilename(
            title="Select local media",
            filetypes=[
                ("Video", "*.mp4 *.mkv *.avi *.mov *.webm"),
                ("Audio", "*.mp3 *.wav *.flac *.m4a"),
                ("All files", "*.*"),
            ],
        )
        if not path:
            return
        self.media_context = MediaContext.from_path(
            path,
            position_seconds=self._parse_time(self.time_var.get()),
            scene_label=self.scene_var.get().strip() or None,
        )
        self.media_var.set(f"{self.media_context.title} · {self.media_context.media_path}")

    def _play_media(self) -> None:
        if self.media_context is None:
            self._show_result("Select a local media file first.")
            return
        try:
            player = self.media_launcher.open(self.media_context.media_path)
            self.status_var.set(f"MEDIA: {player}")
        except Exception as exc:  # noqa: BLE001 - surface local player errors in UI
            self._show_result(f"MEDIA ERROR\n\n{type(exc).__name__}: {exc}")
            self.status_var.set("MEDIA ERROR")

    @staticmethod
    def _parse_time(value: str) -> float:
        parts = value.strip().split(":")
        if len(parts) != 3:
            raise ValueError("scene time must use HH:MM:SS")
        hours, minutes, seconds = (int(part) for part in parts)
        if minutes > 59 or seconds > 59 or min(hours, minutes, seconds) < 0:
            raise ValueError("invalid scene time")
        return hours * 3600 + minutes * 60 + seconds

    def _start_cycle(self) -> None:
        raw_input = self.input_text.get("1.0", "end-1c").strip()
        if not raw_input:
            self._show_result("Please enter an input.")
            return

        media_context = self.media_context
        if media_context is not None:
            media_context = MediaContext(
                media_path=media_context.media_path,
                title=media_context.title,
                position_seconds=self._parse_time(self.time_var.get()),
                scene_label=self.scene_var.get().strip() or None,
                user_note=None,
            )

        self.run_button.configure(state="disabled")
        self.status_var.set("RUNNING")
        for stage in STAGES:
            self.stage_vars[stage].set(f"○ {stage}")

        threading.Thread(
            target=self._run_cycle,
            args=(raw_input, media_context),
            daemon=True,
        ).start()

    def _run_cycle(self, raw_input: str, media_context: MediaContext | None) -> None:
        try:
            loop = self.loop or DecisionLoop()
            learning_context: dict[str, Any] = {"surface": "desktop"}
            if media_context is not None:
                learning_context["media"] = {
                    "title": media_context.title,
                    "path": media_context.media_path,
                    "position_seconds": media_context.position_seconds,
                    "position": media_context.position_label,
                    "scene_label": media_context.scene_label,
                }
                raw_input = media_context.discussion_prompt(raw_input)

            result = loop.run(raw_input, learning_context=learning_context)
            self.after(0, self._render_result, result)
        except Exception as exc:  # noqa: BLE001 - surface runtime failures in UI
            self.after(0, self._render_error, exc)

    def _render_result(self, result: Any) -> None:
        trace_obj = getattr(result, "trace", None)
        trace = tuple(getattr(trace_obj, "stage_trace", ()) or ())
        for stage in STAGES:
            marker = "✓" if stage in trace else "○"
            self.stage_vars[stage].set(f"{marker} {stage}")

        output = getattr(result, "output", {}) or {}
        resource = output.get("resource_decision", {}) or {}
        verdict = getattr(result, "verdict", None) or output.get("verdict")
        action = getattr(result, "action", None) or output.get("action")
        reason = getattr(result, "reason", "") or output.get("reason") or output.get("note")

        lines = [
            f"STATUS      : {getattr(result, 'status', 'UNKNOWN')}",
            f"REASON      : {reason or '—'}",
            f"VERDICT     : {verdict or '—'}",
            f"ACTION      : {action or '—'}",
            f"ANLA SCORE  : {getattr(result, 'anla_score', '—')}",
            f"ETHIC SCORE : {getattr(result, 'ethic_total', '—')}",
            f"TRACE       : {' → '.join(trace) if trace else '—'}",
        ]
        if resource:
            optimization = resource.get("optimization", {}) or {}
            host = optimization.get("host", {}) or {}
            lines.extend(
                [
                    "",
                    "ADAPTIVE RESOURCE",
                    f"capacity    : {optimization.get('optimized_capacity', '—')}",
                    f"status      : {optimization.get('status', '—')}",
                    f"cpu_count   : {host.get('cpu_count', '—')}",
                    f"ram_free    : {host.get('memory_available_bytes', '—')}",
                    f"route       : {(resource.get('route') or {}).get('status', '—')}",
                ]
            )

        if self.media_context is not None:
            lines.extend(
                [
                    "",
                    "MEDIA CONTEXT",
                    f"title       : {self.media_context.title}",
                    f"position    : {self.media_context.position_label}",
                    f"scene       : {self.media_context.scene_label or '—'}",
                ]
            )

        self._show_result("\n".join(lines))
        self.status_var.set(str(getattr(result, "status", "DONE")))
        self.run_button.configure(state="normal")

    def _render_error(self, exc: Exception) -> None:
        self._show_result(f"RUNTIME ERROR\n\n{type(exc).__name__}: {exc}")
        self.status_var.set("ERROR")
        self.run_button.configure(state="normal")

    def _show_result(self, text: str) -> None:
        self.result_text.configure(state="normal")
        self.result_text.delete("1.0", "end")
        self.result_text.insert("1.0", text)
        self.result_text.configure(state="disabled")


def main() -> None:
    """Launch the ANNE local desktop shell."""
    app = AnneDesktop()
    app.mainloop()


if __name__ == "__main__":
    main()
