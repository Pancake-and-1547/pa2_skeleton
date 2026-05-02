"""GUI-facing Engine wired to the real `core` package."""

import core as core_module

from .engine_base import BaseEngine


class Engine(BaseEngine):
    CORE = core_module
