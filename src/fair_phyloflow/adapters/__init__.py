"""Tool adapters (plugin-style integration points).

Adapters declare which routes they support and how to generate commands / parse outputs.
"""

from .registry import adapters_for_route, default_adapters

__all__ = ["adapters_for_route", "default_adapters"]
