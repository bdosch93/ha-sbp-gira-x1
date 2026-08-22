"""Switch functions exposed by the Gira X1 UI configuration."""

from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import GiraX1ConfigEntry
from .const import SWITCH_FUNCTION_TYPES
from .entity import GiraX1Entity
from .models import GiraFunction, as_bool


async def async_setup_entry(
    hass: HomeAssistant,
    entry: GiraX1ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Gira switches and switched sockets."""
    coordinator = entry.runtime_data.coordinator
    async_add_entities(
        GiraX1Switch(coordinator, function)
        for function in coordinator.functions.values()
        if function.function_type in SWITCH_FUNCTION_TYPES
        and function.point("OnOff") is not None
    )


class GiraX1Switch(GiraX1Entity, SwitchEntity):
    """A binary Gira switch."""

    def __init__(self, coordinator, function: GiraFunction) -> None:
        super().__init__(coordinator, function)

    @property
    def is_on(self) -> bool | None:
        return as_bool(self.value("OnOff"))

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self.write("OnOff", 1)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.write("OnOff", 0)
