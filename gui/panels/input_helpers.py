"""Shared input helpers for GUI panels."""

import pygame


def shift_pressed() -> bool:
    """Return True when Shift is currently held."""
    return bool(pygame.key.get_mods() & pygame.KMOD_SHIFT)


def is_inc_key(key: int) -> bool:
    """Return True for keys that represent a positive nudge."""
    return key in (pygame.K_RIGHT, pygame.K_UP, pygame.K_d, pygame.K_w)


def is_dec_key(key: int) -> bool:
    """Return True for keys that represent a negative nudge."""
    return key in (pygame.K_LEFT, pygame.K_DOWN, pygame.K_a, pygame.K_s)


def key_to_digit(key: int):
    """Convert a pygame keycode into a digit character, or None."""
    if pygame.K_0 <= key <= pygame.K_9:
        return chr(ord("0") + (key - pygame.K_0))
    for digit in range(10):
        for name in (f"K_KP{digit}", f"K_KP_{digit}"):
            keypad_key = getattr(pygame, name, None)
            if keypad_key is not None and key == keypad_key:
                return str(digit)
    return None


def is_dot_key(key: int) -> bool:
    """Return True if the key represents a decimal dot on main or keypad."""
    return key in {
        pygame.K_PERIOD,
        getattr(pygame, "K_KP_PERIOD", -1),
        getattr(pygame, "K_KP_DECIMAL", -1),
    }


def is_minus_key(key: int) -> bool:
    """Return True if the key represents a minus sign on main or keypad."""
    return key in {
        pygame.K_MINUS,
        getattr(pygame, "K_KP_MINUS", -1),
    }
