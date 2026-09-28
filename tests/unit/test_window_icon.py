"""Native BFT branding must replace Tk's default feather icon."""

from __future__ import annotations

import hashlib

from ui import window_icon


class _Window:
    def __init__(self) -> None:
        self.calls: list[tuple[bool, object]] = []

    def iconphoto(self, default: bool, image: object) -> None:
        self.calls.append((default, image))


def test_packaged_window_icon_has_the_approved_bft_identity() -> None:
    assert window_icon.WINDOW_ICON_PATH.is_file()
    assert hashlib.sha256(window_icon.WINDOW_ICON_PATH.read_bytes()).hexdigest() == (
        "9a5039c6b1f3d8fc6661121b6695e90ca91120576b9d17fe03f09ffd058f7665"
    )


def test_window_icon_is_applied_as_the_default_and_retained(monkeypatch) -> None:
    icon = object()
    monkeypatch.setattr(window_icon.tk, "PhotoImage", lambda **_kwargs: icon)
    window = _Window()

    assert window_icon.apply_window_icon(window) is True
    assert window.calls == [(True, icon)]
    assert window._bft_window_icon is icon


def test_window_icon_failure_never_blocks_the_application(monkeypatch) -> None:
    def fail(**_kwargs):
        raise window_icon.tk.TclError("bad image")

    monkeypatch.setattr(window_icon.tk, "PhotoImage", fail)

    assert window_icon.apply_window_icon(_Window()) is False
