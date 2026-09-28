"""Reusable display-selection and safe-placement primitives."""

from .models import (
    DisplayInfo,
    DisplayRect,
    DisplayTopology,
    WindowGeometry,
    parse_tk_geometry,
    parse_work_area,
)
from .resolver import (
    ActiveDisplayResolver,
    DisplayDriver,
    DisplayTarget,
    ResolutionStrategy,
    geometry_on_display,
    display_for_window,
    other_display,
)
from .windows import (
    Win32DisplayDriver,
    create_display_driver,
    place_process_tree_windows,
    place_process_windows,
    process_tree_ids,
)

__all__ = [
    "ActiveDisplayResolver",
    "DisplayDriver",
    "DisplayInfo",
    "DisplayRect",
    "DisplayTarget",
    "DisplayTopology",
    "ResolutionStrategy",
    "Win32DisplayDriver",
    "WindowGeometry",
    "create_display_driver",
    "geometry_on_display",
    "display_for_window",
    "other_display",
    "parse_tk_geometry",
    "parse_work_area",
    "place_process_tree_windows",
    "place_process_windows",
    "process_tree_ids",
]
