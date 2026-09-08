"""Zoom RTMS -> ANNE translation bridge.

Zoom RTMS supplies transcript packets continuously and includes participant
identity (`userName`) with each transcript callback. ANNE therefore does not
need to infer who is speaking from the voice.

Requires the optional `rtms` package and a configured Zoom RTMS application.
"""
from __future__ import annotations

import os
import signal
import sys

from anne.translation import TranslationEngine, TranslationMemory
from anne.translation.providers import GoogleCloudTranslationProvider


MEMORY_PATH = os.getenv("ANNE_TRANSLATION_MEMORY", "runtime_data/translation_memory.json")


def main() -> None:
    import rtms

    memory = TranslationMemory(MEMORY_PATH)
    provider = GoogleCloudTranslationProvider()
    engine = TranslationEngine(memory, learning_provider=provider, learning_enabled=True)

    client = rtms.Client()

    @client.on_webhook_event()
    def on_webhook(payload):
        if payload.get("event") != "meeting.rtms_started":
            return
        data = payload.get("payload", {})
        client.join(
            meeting_uuid=data.get("meeting_uuid"),
            rtms_stream_id=data.get("rtms_stream_id"),
            server_urls=data.get("server_urls"),
            signature=data.get("signature"),
        )

    @client.onTranscriptData
    def on_transcript(data, size, timestamp, metadata):
        text = data.decode("utf-8") if isinstance(data, bytes) else str(data)
        speaker = getattr(metadata, "userName", None) or "Unknown"
        result = engine.translate(
            text,
            speaker=speaker,
            context={"source": "zoom_rtms", "timestamp": timestamp},
        )
        print(f"[{speaker}] {result.direct}")
        print(f"    semantic: {result.semantic}")

    def shutdown(_sig, _frame):
        client.leave()
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    while True:
        client._process_join_queue()
        client._poll_if_needed()


if __name__ == "__main__":
    main()
