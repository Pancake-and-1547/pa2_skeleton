"""Viewport and house-grid coordinate helpers."""

from dataclasses import dataclass
from typing import Iterable, Optional, Tuple

import pygame


# ----------------------------
# Viewport mapping (window <-> virtual)
# ----------------------------

@dataclass(frozen=True)
class ViewportTransform:
    """Precomputed mapping information from window space to virtual space.

    Attributes:
        scale: Uniform scale factor applied to virtual -> window.
        dst_size: The scaled virtual surface size (width, height) that fits the window.
        offset: Top-left offset (x, y) of the scaled surface inside the window (letterbox).
    """
    scale: float
    dst_size: tuple[int, int]
    offset: tuple[float, float]


@dataclass
class VirtualViewport:
    """
    Virtual resolution scaling + letterboxing helper.

    Responsibilities:
    - Compute transform from window size -> virtual surface.
    - Map input events into virtual coordinates.
    """
    virtual_w: int
    virtual_h: int

    def compute(self, window_w: int, window_h: int) -> ViewportTransform:
        """Compute the letterbox+scale transform for the current window size."""
        target_aspect = self.virtual_w / self.virtual_h
        window_aspect = window_w / window_h if window_h != 0 else target_aspect

        if window_aspect > target_aspect:
            # Fit by height
            scale = window_h / self.virtual_h
            dst_w = int(scale * self.virtual_w)
            dst_h = int(window_h)
            offset_x = (window_w - dst_w) / 2
            offset_y = 0.0
        else:
            # Fit by width
            scale = window_w / self.virtual_w
            dst_w = int(window_w)
            dst_h = int(scale * self.virtual_h)
            offset_x = 0.0
            offset_y = (window_h - dst_h) / 2

        return ViewportTransform(float(scale), (dst_w, dst_h), (float(offset_x), float(offset_y)))

    def map_point_to_virtual(self, x: float, y: float, *, transform: ViewportTransform) -> tuple[int, int]:
        """Map a window-space point into integer virtual coordinates."""
        ox, oy = transform.offset
        s = transform.scale if transform.scale != 0.0 else 1.0
        vx = (x - ox) / s
        vy = (y - oy) / s
        return (int(vx), int(vy))

    def map_event(self, e: pygame.event.Event, *, transform: ViewportTransform) -> pygame.event.Event:
        """Map a pygame mouse event into virtual coordinates.

        Notes:
        - MOUSEWHEEL does not contain a position and is returned unchanged.
        - Returned events are new pygame Event objects with `pos` in virtual coords.
        """
        # NOTE: MOUSEWHEEL has no pos; do not attempt coordinate remap.
        if e.type in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP):
            mx, my = self.map_point_to_virtual(e.pos[0], e.pos[1], transform=transform)
            return pygame.event.Event(e.type, button=e.button, pos=(mx, my), touch=False)

        if e.type == pygame.MOUSEMOTION:
            mx, my = self.map_point_to_virtual(e.pos[0], e.pos[1], transform=transform)
            s = transform.scale if transform.scale != 0.0 else 1.0
            rel_x = e.rel[0] / s
            rel_y = e.rel[1] / s
            return pygame.event.Event(e.type, pos=(mx, my), rel=(rel_x, rel_y), buttons=e.buttons, touch=False)

        return e

    def map_events(self, events: Iterable[pygame.event.Event], *, transform: ViewportTransform) -> list[pygame.event.Event]:
        """Vectorized version of map_event for an event batch."""
        return [self.map_event(e, transform=transform) for e in events]


def mouse_pos_from_events(
    events: Iterable[pygame.event.Event],
    *,
    fallback: Optional[tuple[int, int]] = None,
) -> tuple[int, int]:
    """
    Extract last-known mouse pos from already-mapped (virtual) events.

        Collaboration notes:
        - Level uses this to keep a stable mouse position even if some frames have no
            mouse motion events.
    """
    last = fallback if fallback is not None else (0, 0)
    for e in events:
        if hasattr(e, "pos"):
            try:
                last = (int(e.pos[0]), int(e.pos[1]))
            except Exception:
                pass
    return last


# ----------------------------
# House grid coordinate system (house cell <-> world pixels)
# ----------------------------

@dataclass(frozen=True)
class HouseGridCoord:
    """
    Coordinate helper for the house grid.

    world pixels:
      - the same coordinate space as sprite rects (topleft positions)
    house cells:
      - (r, c) indices into floor_map grids
    """
    house_offset_r: int
    house_offset_c: int
    map_height: int
    map_width: int
    tile_size: int

    def house_origin_world(self) -> tuple[int, int]:
        """World top-left pixel of the house grid (cell 0,0)."""
        return (self.house_offset_c * self.tile_size, self.house_offset_r * self.tile_size)

    def world_to_house_cell(self, world_pos: tuple[float, float]) -> Optional[tuple[int, int]]:
        """Convert world coordinates -> house grid cell (r, c).

        Returns None when the position is outside the house bounds.
        """
        wx, wy = world_pos
        c = int(wx // self.tile_size) - self.house_offset_c
        r = int(wy // self.tile_size) - self.house_offset_r
        if 0 <= r < self.map_height and 0 <= c < self.map_width:
            return (r, c)
        return None

    def house_cell_to_world_topleft(self, r: int, c: int) -> tuple[int, int]:
        """Convert house grid cell (r, c) -> world top-left pixel coordinates."""
        x = (self.house_offset_c + int(c)) * self.tile_size
        y = (self.house_offset_r + int(r)) * self.tile_size
        return (x, y)


def find_sprite_at_house_cell(sprite_group: pygame.sprite.Group, coord: HouseGridCoord, r: int, c: int):
    """
    Generic sprite lookup by rect.topleft matching the house cell topleft.

    Dependencies and collaboration:
    - Assumes sprites are aligned to cell toplefts (UIMapManager enforces this).
    - Used by InteractionManager to locate AC/Door sprites at the selected cell.
    """
    wx, wy = coord.house_cell_to_world_topleft(int(r), int(c))
    for spr in sprite_group:
        if getattr(spr, "rect", None) is not None and spr.rect.topleft == (wx, wy):
            return spr
    return None
