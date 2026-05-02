"""Minimal interface shared by all GUI panels."""

class BasePanel:
    """
    Base class for UI panels.

    `wants_text_input`:
    - True for panels that expect text editing (so IME/text input should be enabled).
    - False otherwise (IME/text input should be stopped).
    """
    wants_text_input: bool = False

    def __init__(self) -> None:
        self.is_open: bool = False

    def open(self, *args, **kwargs) -> None:
        """Open the panel.

        Notes:
        - PanelManager typically calls this before making the panel active.
        - Subclasses may accept keyword args such as `state=...` for prefill.
        """
        self.is_open = True

    def close(self) -> None:
        """Close the panel and reset transient UI state.

        Subclasses should override when they own additional state that must be cleared.
        """
        self.is_open = False

    def handle_events(self, state, manager, events) -> bool:
        """Handle input events.

        Args:
            state: Shared GameState-like object (simulation + shared flags).
            manager: PanelManager-like object used to open/close modals/popups.
            events: Iterable of pygame events (already mapped to virtual coords).

        Returns:
            True if the panel consumed any event(s) and callers should stop propagation.
        """
        return False

    def draw(self, state, manager, surface, mouse_pos, ui) -> None:
        """Draw the panel onto the virtual surface.

        Args:
            surface: pygame.Surface for the virtual render target.
            mouse_pos: Current mouse position in virtual coordinates.
            ui: Overlay/renderer helper (fonts, colors, text wrapping, etc.).
        """
        return
