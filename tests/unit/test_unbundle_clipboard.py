"""Clipboard ingress reuses the normal unbundle parser and publication path."""

from __future__ import annotations

from types import SimpleNamespace

from ui.unbundle_frame import UnbundleFrame


def test_clipboard_text_is_parsed_and_published_without_a_file_dialog():
    manifest = object()

    class Frame:
        PARSE_PROGRESS_MIN_MB = 2.0
        parser = SimpleNamespace(parse=lambda text: manifest)
        current_manifest = None

        def __init__(self):
            self.logs = []
            self.accepted = []

        def _log(self, message):
            self.logs.append(message)

        def _accept_manifest(self, source_label):
            self.accepted.append(source_label)

        def winfo_toplevel(self):
            return self

    frame = Frame()

    UnbundleFrame.load_bundle_text(frame, "bundle payload", source_label="Clipboard")

    assert frame.current_manifest is manifest
    assert frame.accepted == ["Clipboard"]
