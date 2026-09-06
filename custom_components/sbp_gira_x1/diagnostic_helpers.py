"""Secret-free, passive diagnostic projections."""

from __future__ import annotations


def cover_diagnostics(functions, values, errors):
    """Expose cover mapping and cached values, never request/device credentials."""
    return [
        {
            "uid": function.uid,
            "name": function.name,
            "location": function.location,
            "channel_type": function.channel_type,
            "read_error_type": errors.get(function.uid),
            "data_points": {
                name: {
                    "uid": point.uid,
                    "can_read": point.can_read,
                    "can_write": point.can_write,
                    "has_cached_value": point.uid in values,
                    "value": values.get(point.uid),
                }
                for name, point in function.data_points.items()
                if name in ("Up-Down", "Step-Up-Down", "Position", "Slat-Position")
            },
        }
        for function in functions
        if function.function_type == "de.gira.schema.functions.Covering"
    ]
