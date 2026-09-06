"""Diagnostics for the SBP Gira X1 integration."""

from __future__ import annotations

from collections import Counter
from typing import Any

from homeassistant.core import HomeAssistant

from . import GiraX1ConfigEntry
from .diagnostic_helpers import cover_diagnostics


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant,
    entry: GiraX1ConfigEntry,
) -> dict[str, Any]:
    """Return non-secret function metadata for mapping and troubleshooting."""
    coordinator = entry.runtime_data.coordinator
    functions = tuple(coordinator.functions.values())
    return {
        "diagnostics_version": 2,
        "cover_write_events": list(coordinator.client.cover_write_events),
        "read_errors": dict(coordinator.client.last_read_errors),
        "cover_functions": cover_diagnostics(
            functions,
            (coordinator.data or {}).get("values", {}),
            coordinator.client.last_read_errors,
        ),
        "host": coordinator.client.host,
        "function_count": len(functions),
        "function_type_counts": dict(
            sorted(Counter(function.function_type for function in functions).items())
        ),
        "scene_functions": [
            {
                "uid": function.uid,
                "name": function.name,
                "function_type": function.function_type,
                "channel_type": function.channel_type,
                "location": function.location,
                "trade": function.trade,
                "parameters": list(function.parameters),
                "scene_number": function.scene_number(),
                "data_points": {
                    name: {
                        "uid": point.uid,
                        "can_read": point.can_read,
                        "can_write": point.can_write,
                        "can_event": point.can_event,
                    }
                    for name, point in function.data_points.items()
                },
            }
            for function in functions
            if "scene" in function.function_type.casefold()
        ],
    }
