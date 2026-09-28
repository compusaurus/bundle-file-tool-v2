"""Framework-neutral display geometry models with signed coordinates."""

from __future__ import annotations

import re
from dataclasses import dataclass


_TK_GEOMETRY = re.compile(
    r"^(?P<width>\d+)x(?P<height>\d+)"
    r"(?:(?P<x>[+-]\d+)(?P<y>[+-]\d+))?$"
)


@dataclass(frozen=True)
class DisplayRect:
    """A rectangle in virtual-desktop coordinates."""

    left: int
    top: int
    right: int
    bottom: int

    @property
    def width(self) -> int:
        return max(0, self.right - self.left)

    @property
    def height(self) -> int:
        return max(0, self.bottom - self.top)

    @property
    def area(self) -> int:
        return self.width * self.height

    @property
    def center(self) -> tuple[int, int]:
        return self.left + self.width // 2, self.top + self.height // 2

    def contains(self, point: tuple[int, int]) -> bool:
        x, y = point
        return self.left <= x < self.right and self.top <= y < self.bottom

    def intersection_area(self, other: "DisplayRect") -> int:
        width = max(0, min(self.right, other.right) - max(self.left, other.left))
        height = max(0, min(self.bottom, other.bottom) - max(self.top, other.top))
        return width * height

    def centered_window(self, width: int, height: int) -> "DisplayRect":
        width = min(max(1, int(width)), max(1, self.width))
        height = min(max(1, int(height)), max(1, self.height))
        x = self.left + (self.width - width) // 2
        y = self.top + (self.height - height) // 2
        return DisplayRect(x, y, x + width, y + height)

    def clamp_window(self, window: "DisplayRect") -> "DisplayRect":
        width = min(max(1, window.width), max(1, self.width))
        height = min(max(1, window.height), max(1, self.height))
        max_x = max(self.left, self.right - width)
        max_y = max(self.top, self.bottom - height)
        x = min(max(window.left, self.left), max_x)
        y = min(max(window.top, self.top), max_y)
        return DisplayRect(x, y, x + width, y + height)

    def as_csv(self) -> str:
        return f"{self.left},{self.top},{self.right},{self.bottom}"


@dataclass(frozen=True)
class DisplayInfo:
    """One connected display and its taskbar/dock-safe work area."""

    identifier: str
    bounds: DisplayRect
    work_area: DisplayRect
    primary: bool = False


@dataclass(frozen=True)
class DisplayTopology:
    """A stable snapshot of the connected display set."""

    displays: tuple[DisplayInfo, ...]

    @property
    def primary_display(self) -> DisplayInfo | None:
        return next((display for display in self.displays if display.primary), None) or (
            self.displays[0] if self.displays else None
        )


@dataclass(frozen=True)
class WindowGeometry:
    width: int
    height: int
    x: int | None = None
    y: int | None = None

    @property
    def positioned(self) -> bool:
        return self.x is not None and self.y is not None

    @property
    def rect(self) -> DisplayRect | None:
        if not self.positioned:
            return None
        assert self.x is not None and self.y is not None
        return DisplayRect(self.x, self.y, self.x + self.width, self.y + self.height)


def parse_tk_geometry(value: object) -> WindowGeometry | None:
    """Parse ``WIDTHxHEIGHT±X±Y`` without rejecting negative coordinates."""

    match = _TK_GEOMETRY.fullmatch(str(value or "").strip())
    if match is None:
        return None
    width = int(match.group("width"))
    height = int(match.group("height"))
    if width < 1 or height < 1:
        return None
    x = int(match.group("x")) if match.group("x") is not None else None
    y = int(match.group("y")) if match.group("y") is not None else None
    return WindowGeometry(width, height, x, y)


def parse_work_area(value: object) -> DisplayRect | None:
    """Parse the persisted ``left,top,right,bottom`` work-area contract."""

    try:
        parts = tuple(int(part.strip()) for part in str(value or "").split(","))
    except ValueError:
        return None
    if len(parts) != 4:
        return None
    rect = DisplayRect(*parts)
    return rect if rect.width > 0 and rect.height > 0 else None

