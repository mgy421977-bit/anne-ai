from __future__ import annotations

import json
from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox

from anne.translation import TranslationEngine, TranslationMemory

BASE = Path(__file__).resolve().parents[1]
MEMORY = BASE / "runtime_data" / "translation_memory.json"


def build_engine() -> TranslationEngine:
    # Import is optional so the base ANNE installation remains cloud-free.
    try:
        from anne.translation.providers import GoogleCloudTranslationProvider
        provider = GoogleCloudTranslationProvider()
    except Exception:
        provider = None
    return TranslationEngine(
        TranslationMemory(MEMORY),
        learning_provider=provider,
        learning_enabled=True,
    )


class LiveTranslatorApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("ANNE — Live Semantic Translator")
        self.root.geometry("1100x760")
        self.engine = build_engine()
        self.items: list[dict[str, str]] = []
        self._build()

    def _build(self) -> None:
        frame = ttk.Frame(self.root, padding=12)
        frame.pack(fill="both", expand=True)
        ttk.Label(
            frame,
            text="ANNE • MITOS LIVE TRANSLATOR",
            font=("Segoe UI", 18, "bold"),
        ).pack(anchor="w")
        ttk.Label(
            frame,
            text="Known → offline memory | Unknown → learning provider → persistent memory",
        ).pack(anchor="w", pady=(2, 12))

        form = ttk.Frame(frame)
        form.pack(fill="x")
        ttk.Label(form, text="Speaker").grid(row=0, column=0, sticky="w")
        self.speaker = ttk.Entry(form, width=28)
        self.speaker.grid(row=1, column=0, padx=(0, 12), sticky="ew")
        ttk.Label(form, text="Meeting context").grid(row=0, column=1, sticky="w")
        self.context = ttk.Entry(form)
        self.context.grid(row=1, column=1, sticky="ew")
        form.columnconfigure(1, weight=1)

        ttk.Label(frame, text="English transcript chunk").pack(anchor="w", pady=(12, 4))
        self.source = tk.Text(frame, height=5, font=("Segoe UI", 12))
        self.source.pack(fill="x")

        buttons = ttk.Frame(frame)
        buttons.pack(fill="x", pady=8)
        ttk.Button(buttons, text="TRANSLATE", command=self.translate).pack(side="left")
        ttk.Button(buttons, text="CLEAR", command=self.clear).pack(side="left", padx=8)
        ttk.Button(buttons, text="SAVE SESSION", command=self.save).pack(side="left")

        self.output = tk.Text(frame, font=("Segoe UI", 11), state="disabled")
        self.output.pack(fill="both", expand=True)

    def translate(self) -> None:
        source = self.source.get("1.0", "end").strip()
        if not source:
            return
        try:
            result = self.engine.translate(
                source,
                speaker=self.speaker.get().strip() or "Unknown",
                context={"meeting": self.context.get().strip()},
            )
        except Exception as exc:
            messagebox.showerror("ANNE", str(exc))
            return

        item = {
            "speaker": result.speaker,
            "source": result.source,
            "direct": result.direct,
            "semantic": result.semantic,
            "mode": result.source_mode,
        }
        self.items.append(item)
        self.output.configure(state="normal")
        self.output.insert(
            "end",
            f"\n[{result.source_mode.upper()}] {result.speaker}\n"
            f"BİREBİR: {result.direct}\n"
            f"ANLAMSAL: {result.semantic}\n"
            + "─" * 90 + "\n",
        )
        self.output.see("end")
        self.output.configure(state="disabled")
        self.source.delete("1.0", "end")

    def clear(self) -> None:
        self.source.delete("1.0", "end")

    def save(self) -> None:
        path = BASE / "runtime_data" / "meeting_session.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.items, ensure_ascii=False, indent=2), encoding="utf-8")
        messagebox.showinfo("ANNE", f"Session saved:\n{path}")


if __name__ == "__main__":
    root = tk.Tk()
    LiveTranslatorApp(root)
    root.mainloop()
