"""Covers exposed by the Gira X1 UI configuration."""

from __future__ import annotations

from typing import Any

from homeassistant.components.cover import (
    ATTR_POSITION,
    ATTR_TILT_POSITION,
    CoverEntity,
    CoverEntityFeature,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import GiraX1ConfigEntry
from .const import COVER_FUNCTION_TYPES
from .entity import GiraX1Entity
from .models import GiraFunction, coerce_value


async def async_setup_entry(
    hass: HomeAssistant,
    entry: GiraX1ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up covers."""
    coordinator = entry.runtime_data.coordinator
    async_add_entities(
        GiraX1Cover(coordinator, function)
        for function in coordinator.functions.values()
        if function.function_type in COVER_FUNCTION_TYPES
    )


class GiraX1Cover(GiraX1Entity, CoverEntity):
    """A Gira blind or shutter."""

    def __init__(self, coordinator, function: GiraFunction) -> None:
        super().__init__(coordinator, function)
        features = CoverEntityFeature(0)
        if (point := function.point("Up-Down")) and point.can_write:
            features |= CoverEntityFeature.OPEN | CoverEntityFeature.CLOSE
        if (point := function.point("Step-Up-Down")) and point.can_write:
            features |= CoverEntityFeature.STOP
        if (point := function.point("Position")) and point.can_write:
            features |= CoverEntityFeature.SET_POSITION
        if (point := function.point("Slat-Position")) and point.can_write:
            features |= CoverEntityFeature.SET_TILT_POSITION
        self._attr_supported_features = features

    @property
    def current_cover_position(self) -> int | None:
        value = coerce_value(self.value("Position"))
        if not isinstance(value, (int, float)):
            return None
        return round(100 - max(0, min(100, value)))

    @property
    def current_cover_tilt_position(self) -> int | None:
        value = coerce_value(self.value("Slat-Position"))
        if not isinstance(value, (int, float)):
            return None
        return round(max(0, min(100, value)))

    @property
    def is_closed(self) -> bool | None:
        position = self.current_cover_position
        return None if position is None else position == 0

    async def async_open_cover(self, **kwargs: Any) -> None:
        await self.write("Up-Down", 0)

    async def async_close_cover(self, **kwargs: Any) -> None:
        await self.write("Up-Down", 1)

    async def async_stop_cover(self, **kwargs: Any) -> None:
        await self.write("Step-Up-Down", 1)

    async def async_set_cover_position(self, **kwargs: Any) -> None:
        await self.write("Position", 100 - int(kwargs[ATTR_POSITION]))

    async def async_set_cover_tilt_position(self, **kwargs: Any) -> None:
        await self.write("Slat-Position", int(kwargs[ATTR_TILT_POSITION]))
