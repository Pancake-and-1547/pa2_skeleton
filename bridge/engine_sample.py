"""GUI-facing Engine wired to `encrypted_solution.core`."""

import encrypted_solution.core as core_module

from .engine_base import BaseEngine


class Engine(BaseEngine):
    CORE = core_module
