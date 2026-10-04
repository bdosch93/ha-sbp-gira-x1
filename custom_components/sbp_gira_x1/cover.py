"""Covers exposed by the Gira X1 UI configuration."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.components.cover import (
    ATTR_POSITION,
    ATTR_TILT_POSITION,
    CoverDeviceClass,
    CoverEntity,
    CoverEntityFeature,
)
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity_platform import (
    AddConfigEntryEntitiesCallback,
    async_get_current_platform,
)

from . import GiraX1ConfigEntry
from .const import COVER_FUNCTION_TYPES, DOMAIN
from .entity import GiraX1Entity
from .models import GiraFunction, coerce_value, exposes_cover_tilt


async def async_setup_entry(
    hass: HomeAssistant,
    entry: GiraX1ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up covers."""
    coordinator = entry.runtime_data.coordinator
    registry = er.async_get(hass)
    entities: list[GiraX1Cover] = []
    for function in coordinator.functions.values():
        if function.function_type not in COVER_FUNCTION_TYPES:
            continue
        unique_id = f"{coordinator.client.host}:{function.uid}"
        entity_id = registry.async_get_entity_id(Platform.COVER, DOMAIN, unique_id)
        registry_entry = registry.async_get(entity_id) if entity_id else None
        entities.append(
            GiraX1Cover(
                coordinator,
                function,
                is_shutter=bool(
                    registry_entry
                    and registry_entry.device_class == CoverDeviceClass.SHUTTER
                ),
            )
        )
    async_add_entities(entities)
    async_get_current_platform().async_register_entity_service(
        "test_cover_step",
        {
            vol.Required("value"): vol.All(int, vol.In((0, 1))),
            vol.Required("expected_point_uid"): str,
        },
        "async_test_cover_step",
        required_features=[CoverEntityFeature.STOP],
    )


class GiraX1Cover(GiraX1Entity, CoverEntity):
    """A Gira blind or shutter."""

    def __init__(
        self, coordinator, function: GiraFunction, *, is_shutter: bool = False
    ) -> None:
        super().__init__(coordinator, function)
        self._is_shutter = is_shutter
        features = CoverEntityFeature(0)
        if (point := function.point("Up-Down")) and point.can_write:
            features |= CoverEntityFeature.OPEN | CoverEntityFeature.CLOSE
        if (point := function.point("Step-Up-Down")) and point.can_write:
            features |= CoverEntityFeature.STOP
        if (point := function.point("Position")) and point.can_write:
            features |= CoverEntityFeature.SET_POSITION
        if exposes_cover_tilt(function, is_shutter=is_shutter):
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
        if self._is_shutter:
            return None
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

    async def async_test_cover_step(
        self, value: int, expected_point_uid: str
    ) -> None:
        """Send one explicit diagnostic step value to a verified cover point.

        No direction command, retry or automatic reversal is added. The caller
        must supply the known point UID, preventing an unnoticed mapping change.
        """
        current = self.coordinator.functions.get(self.function.uid)
        point = current.point("Step-Up-Down") if current else None
        bound = self.function.point("Step-Up-Down")
        if (
            type(value) is not int
            or value not in (0, 1)
            or point is None
            or bound is None
            or not point.can_write
            or not bound.can_write
            or point.uid != expected_point_uid
            or bound.uid != expected_point_uid
        ):
            raise HomeAssistantError("Cover test rejected: value or point mapping invalid")
        await self.write("Step-Up-Down", value)

    async def async_set_cover_position(self, **kwargs: Any) -> None:
        await self.write("Position", 100 - int(kwargs[ATTR_POSITION]))

    async def async_set_cover_tilt_position(self, **kwargs: Any) -> None:
        await self.write("Slat-Position", int(kwargs[ATTR_TILT_POSITION]))
