"""Small rendering and asset helpers for the GUI."""

from pathlib import Path
import io
import pygame
import numpy as np
from os import walk


def build_heatmap_surface(pygame, floor_map, temperature_field, tile_size: int, alpha: int = 234, font=None):
    """
    Build a heatmap surface for the whole house grid.
    """
    h, w = floor_map.height, floor_map.width
    surf = pygame.Surface((w * tile_size, h * tile_size), pygame.SRCALPHA)

    mask = (floor_map.floors.astype(bool) | floor_map.walls.astype(bool) | floor_map.doors.astype(bool))
    temps = temperature_field[mask] if mask.any() else np.array([], dtype=float)
    if temps.size == 0:
        return surf

    tmin = float(np.nanmin(temps))
    tmax = float(np.nanmax(temps))
    if abs(tmax - tmin) < 1e-6:
        tmax = tmin + 1.0

    def lerp(a, b, t):
        return a + (b - a) * t

    for r in range(h):
        for c in range(w):
            if not mask[r, c]:
                continue

            t = float(temperature_field[r, c])
            x = (t - tmin) / (tmax - tmin)
            x = max(0.0, min(1.0, x))

            # blue -> white -> red
            if x < 0.5:
                k = x / 0.5
                col = (int(lerp(30, 80, k)), int(lerp(80, 255, k)), int(lerp(255, 255, k)))
            else:
                k = (x - 0.5) / 0.5
                col = (int(lerp(255, 255, k)), int(lerp(255, 80, k)), int(lerp(255, 30, k)))

            cell_rect = (c * tile_size, r * tile_size, tile_size, tile_size)
            pygame.draw.rect(surf, (*col, int(alpha)), cell_rect)

            if font is not None:
                r0, g0, b0 = col
                luminance = 0.2126 * r0 + 0.7152 * g0 + 0.0722 * b0
                text_col = (0, 0, 0) if luminance > 150 else (255, 255, 255)
                text = f"{t:.2f}"
                text_surf = font.render(text, True, text_col)
                text_rect = text_surf.get_rect(center=(c * tile_size + tile_size // 2, r * tile_size + tile_size // 2))
                surf.blit(text_surf, text_rect)

    return surf


def import_folder(path):
    path = Path(path)
    surface_list = []
    for _, __, img_files in walk(path):
        for image in img_files:
            full_path = path / image
            image_surf = pygame.image.load(str(full_path)).convert_alpha()
            surface_list.append(image_surf)
    return surface_list


def opaque_bounds_rect(surf: pygame.Surface) -> pygame.Rect:
    mask = pygame.mask.from_surface(surf)
    rects = mask.get_bounding_rects()
    if not rects:
        return pygame.Rect(0, 0, surf.get_width(), surf.get_height())

    bounds = rects[0].copy()
    for r in rects[1:]:
        bounds.union_ip(r)
    return bounds


def figure_to_surface(fig, max_width: int | None = None, max_height: int | None = None):
    """
    Convert a matplotlib Figure into a pygame.Surface (RGBA).
    Uses High DPI + Smoothscale for crisp rendering on virtual surface.
    """
    buf = io.BytesIO()
    try:
        import matplotlib
        matplotlib.use("Agg", force=True)
        # CHANGED: High DPI (200) for source image
        fig.savefig(buf, format="png", bbox_inches='tight', transparent=False, dpi=200)
        buf.seek(0)
        
        surf = pygame.image.load(buf).convert_alpha()
    except Exception as e:
        print(f"Plot rendering failed: {e}")
        surf = pygame.Surface((200, 100))
    finally:
        buf.close()
        try:
            import matplotlib.pyplot as plt
            plt.close(fig)
        except Exception:
            pass

    if max_width and max_height:
        w, h = surf.get_size()
        scale_w = max_width / w
        scale_h = max_height / h
        scale = min(1.0, min(scale_w, scale_h))
        
        new_w = int(w * scale)
        new_h = int(h * scale)
        # CHANGED: Use smoothscale for high-quality downsampling
        surf = pygame.transform.smoothscale(surf, (new_w, new_h))

    return surf
