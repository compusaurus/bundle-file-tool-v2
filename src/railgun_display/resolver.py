"""Reusable active-display and launch-display resolution policy."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Protocol

from .models import (
    DisplayInfo,
    DisplayRect,
    DisplayTopology,
    parse_tk_geometry,
    parse_work_area,
)


class ResolutionStrategy(str, Enum):
    HYBRID_CURSOR_FIRST = "hybrid_cursor_first"
    CURSOR = "cursor"
    FOREGROUND_WINDOW = "foreground_window"
    PRIMARY = "primary"


class DisplayDriver(Protocol):
    def topology(self) -> DisplayTopology: ...
    def cursor_point(self) -> tuple[int, int] | None: ...
    def foreground_rect(self) -> DisplayRect | None: ...


@dataclass(frozen=True)
class DisplayTarget:
    display: DisplayInfo
    reason: str

    @property
    def work_area(self) -> DisplayRect:
        return self.display.work_area


def _display_for_point(
    topology: DisplayTopology, point: tuple[int, int] | None
) -> DisplayInfo | None:
    if point is None:
        return None
    contained = next(
        (display for display in topology.displays if display.bounds.contains(point)), None
    )
    if contained is not None:
        return contained
    x, y = point
    return min(
        topology.displays,
        key=lambda display: (
            max(display.bounds.left - x, 0, x - display.bounds.right) ** 2
            + max(display.bounds.top - y, 0, y - display.bounds.bottom) ** 2
        ),
        default=None,
    )


def _display_for_rect(
    topology: DisplayTopology, rect: DisplayRect | None
) -> DisplayInfo | None:
    if rect is None:
        return None
    ranked = sorted(
        topology.displays,
        key=lambda display: rect.intersection_area(display.bounds),
        reverse=True,
    )
    if not ranked or rect.intersection_area(ranked[0].bounds) == 0:
        return None
    return ranked[0]


class ActiveDisplayResolver:
    """Resolve a display without assuming that primary means active."""

    def __init__(self, driver: DisplayDriver) -> None:
        self.driver = driver

    def resolve(
        self, strategy: ResolutionStrategy = ResolutionStrategy.HYBRID_CURSOR_FIRST
    ) -> DisplayTarget | None:
        topology = self.driver.topology()
        if not topology.displays:
            return None
        if strategy in {ResolutionStrategy.HYBRID_CURSOR_FIRST, ResolutionStrategy.CURSOR}:
            display = _display_for_point(topology, self.driver.cursor_point())
            if display is not None:
                return DisplayTarget(display, "cursor")
        if strategy in {
            ResolutionStrategy.HYBRID_CURSOR_FIRST,
            ResolutionStrategy.FOREGROUND_WINDOW,
        }:
            display = _display_for_rect(topology, self.driver.foreground_rect())
            if display is not None:
                return DisplayTarget(display, "foreground-window")
        primary = topology.primary_display
        return DisplayTarget(primary, "primary-fallback") if primary is not None else None

    def resolve_application_launch(
        self,
        *,
        saved_geometry: object = "",
        saved_work_area: object = "",
    ) -> DisplayTarget | None:
        """Prefer the app's restorable display, then current user attention."""

        topology = self.driver.topology()
        geometry = parse_tk_geometry(saved_geometry)
        display = _display_for_rect(topology, geometry.rect if geometry else None)
        if display is not None:
            return DisplayTarget(display, "saved-window")
        display = _display_for_rect(topology, parse_work_area(saved_work_area))
        if display is not None:
            return DisplayTarget(display, "saved-display")
        return self.resolve(ResolutionStrategy.HYBRID_CURSOR_FIRST)


def geometry_on_display(value: object, work_area: DisplayRect) -> str:
    """Contain persisted Tk geometry on the already-resolved launch display."""

    geometry = parse_tk_geometry(value)
    if geometry is None:
        geometry = parse_tk_geometry("1000x700")
    assert geometry is not None
    current = geometry.rect
    if current is None or current.intersection_area(work_area) == 0:
        placed = work_area.centered_window(geometry.width, geometry.height)
    else:
        placed = work_area.clamp_window(current)
    return f"{placed.width}x{placed.height}{placed.left:+d}{placed.top:+d}"


def display_for_window(topology: DisplayTopology, rect: DisplayRect) -> DisplayInfo | None:
    """Use the window's largest intersection, then its nearest display."""
    return _display_for_rect(topology, rect) or _display_for_point(topology, rect.center)


def other_display(topology: DisplayTopology, rect: DisplayRect) -> DisplayInfo | None:
    """Cycle through distinct desktop work areas in stable spatial order."""
    unique = {display.work_area: display for display in topology.displays
              if display.work_area.area > 0}
    displays = sorted(unique.values(), key=lambda d: (d.bounds.left, d.bounds.top, d.identifier))
    if len(displays) < 2:
        return None
    current = display_for_window(DisplayTopology(tuple(displays)), rect)
    return displays[(displays.index(current) + 1) % len(displays)]
