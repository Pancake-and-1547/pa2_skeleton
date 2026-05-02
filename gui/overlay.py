"""Overlay theme, fonts, and common drawing helpers."""

import pygame

from .paths import asset_path


PANEL_BG = (18, 26, 34, 232)
PANEL_BG_ALT = (29, 40, 52, 232)
PANEL_EDGE = (126, 180, 191)
PANEL_EDGE_SOFT = (64, 92, 110)
PANEL_EDGE_OUTER = (194, 218, 224, 218)
TEXT_PRIMARY = (238, 244, 247)
TEXT_MUTED = (181, 194, 201)
CONTENT_BG = (10, 15, 21, 220)
BTN_BG = (36, 54, 68, 235)
BTN_BG_HOVER = (51, 76, 94, 235)
BTN_BG_ACTIVE = (56, 114, 120, 245)
BTN_BG_PRIMARY = (201, 133, 45, 245)
BTN_BG_PRIMARY_HOVER = (222, 152, 60, 245)
BTN_BG_DANGER = (140, 67, 67, 245)
BTN_BG_DANGER_HOVER = (165, 79, 79, 245)


class SmoothFont:
    """Render text at higher resolution then smoothscale down."""

    def __init__(self, name, size, scale_factor=3):
        self.scale = scale_factor
        self.font = pygame.font.Font(str(name) if name else None, int(size * scale_factor))

    def render(self, text, antialias, color, background=None):
        big_surf = self.font.render(str(text), True, color, background)
        target_w = int(big_surf.get_width() / self.scale)
        target_h = int(big_surf.get_height() / self.scale)
        if target_w <= 0 or target_h <= 0:
            return big_surf
        return pygame.transform.smoothscale(big_surf, (target_w, target_h))

    def get_height(self):
        return int(self.font.get_height() / self.scale)

    def size(self, text):
        w, h = self.font.size(str(text))
        return (int(w / self.scale), int(h / self.scale))


class Overlay:
    """Rendering helper / UI context."""

    def __init__(self):
        self.font_board = SmoothFont(None, 22)
        self.font_step = SmoothFont(None, 24)
        self.font_heatmap = SmoothFont(None, 24)
        self.font_panel_title = SmoothFont(None, 34)
        self.font_panel_value = SmoothFont(None, 28)
        self.font_panel_hint = SmoothFont(None, 22)
        self.font_btn = SmoothFont(None, 22)
        self.font_right = SmoothFont(None, 23)
        self.colors = {
            "text": TEXT_PRIMARY,
            "muted": TEXT_MUTED,
            "panel_bg": PANEL_BG,
            "panel_edge": PANEL_EDGE,
            "content_bg": CONTENT_BG,
        }

    def draw_text(self, surface, text, pos, color=TEXT_PRIMARY, font=None, anchor="topleft"):
        if font is None:
            font = self.font_board
        surf = font.render(str(text), True, color)
        rect = surf.get_rect(**{anchor: pos})
        surface.blit(surf, rect)
        return rect

    def wrap_lines(self, text: str, font, max_width: int):
        lines: list[str] = []
        for raw in str(text).splitlines() or [""]:
            if font.size(raw)[0] <= max_width:
                lines.append(raw)
                continue
            cur = ""
            for word in raw.split(" "):
                candidate = f"{cur} {word}".strip()
                if font.size(candidate)[0] > max_width and cur:
                    lines.append(cur)
                    cur = word
                else:
                    cur = candidate
            if cur:
                lines.append(cur)
        return lines

    def format_step_label(self, step_minutes: int) -> str:
        if step_minutes % 1440 == 0 and step_minutes > 0:
            return f"{step_minutes // 1440} day"
        if step_minutes % 60 == 0 and step_minutes > 0:
            return f"{step_minutes // 60} hour"
        return f"{step_minutes} min"

    def power_mode_text(self, signed_power: int) -> str:
        p = int(max(-5, min(5, signed_power)))
        if p == 0:
            return "Mode: OFF"
        if p < 0:
            return f"Mode: HEAT  Level: {abs(p)}"
        return f"Mode: COOL  Level: {p}"

    def draw_panel_bg(self, surface, rect: pygame.Rect, *, title: str | None = None, title_font=None):
        shadow = rect.move(4, 5)
        shadow_surf = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
        pygame.draw.rect(shadow_surf, (0, 0, 0, 34), shadow_surf.get_rect(), border_radius=16)
        surface.blit(shadow_surf, shadow.topleft)

        panel = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
        pygame.draw.rect(panel, PANEL_BG, panel.get_rect(), border_radius=16)

        if title:
            header_rect = pygame.Rect(0, 0, rect.width, min(68, rect.height))
            pygame.draw.rect(
                panel,
                PANEL_BG_ALT,
                header_rect,
                border_top_left_radius=16,
                border_top_right_radius=16,
            )
            divider_y = min(header_rect.bottom - 1, rect.height - 12)
            pygame.draw.line(panel, PANEL_EDGE, (18, divider_y), (rect.width - 18, divider_y), 2)

        pygame.draw.rect(panel, PANEL_EDGE_OUTER, panel.get_rect(), width=3, border_radius=16)
        inner_rect = panel.get_rect().inflate(-6, -6)
        pygame.draw.rect(panel, PANEL_EDGE_SOFT, inner_rect, width=1, border_radius=13)

        surface.blit(panel, rect.topleft)

        if title:
            font = title_font if title_font else self.font_panel_title
            self.draw_text(surface, title, (rect.centerx, rect.top + 18), font=font, anchor="midtop")

    def draw_content_box(self, surface, rect: pygame.Rect, *, border: bool = True):
        pygame.draw.rect(surface, CONTENT_BG, rect, border_radius=10)
        if border:
            pygame.draw.rect(surface, PANEL_EDGE_OUTER, rect, 2, border_radius=10)

    def draw_button(
        self,
        surface,
        rect: pygame.Rect,
        label: str,
        *,
        mouse_pos,
        active: bool = False,
        variant: str = "default",
        disabled: bool = False,
    ):
        hover = rect.collidepoint(mouse_pos)
        if disabled:
            bg = (52, 58, 65, 180)
            border = (88, 96, 105)
            text_color = (142, 150, 160)
        else:
            if variant == "primary":
                bg = BTN_BG_PRIMARY_HOVER if hover else BTN_BG_PRIMARY
            elif variant == "danger":
                bg = BTN_BG_DANGER_HOVER if hover else BTN_BG_DANGER
            elif active:
                bg = BTN_BG_HOVER if hover else BTN_BG_ACTIVE
            else:
                bg = BTN_BG_HOVER if hover else BTN_BG
            border = PANEL_EDGE if active else PANEL_EDGE_SOFT
            text_color = TEXT_PRIMARY

        pygame.draw.rect(surface, bg, rect, border_radius=8)
        pygame.draw.rect(surface, border, rect, 2, border_radius=8)
        self.draw_text(surface, label, rect.center, font=self.font_btn, anchor="center", color=text_color)

    def draw(self, surface: pygame.Surface, *, panels, mouse_pos, state) -> None:
        panels.draw(surface, mouse_pos, ui=self)
