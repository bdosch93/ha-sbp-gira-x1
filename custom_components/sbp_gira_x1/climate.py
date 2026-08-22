"""Heating controls exposed by the Gira X1 UI configuration."""

from __future__ import annotations

from typing import Any

from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityFeature,
    HVACMode,
)
from homeassistant.const import ATTR_TEMPERATURE, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import GiraX1ConfigEntry
from .const import CLIMATE_FUNCTION_TYPES
from .entity import GiraX1Entity
from .models import GiraFunction, as_bool, coerce_value


async def async_setup_entry(
    hass: HomeAssistant,
    entry: GiraX1ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up climate controls."""
    coordinator = entry.runtime_data.coordinator
    async_add_entities(
        GiraX1Climate(coordinator, function)
        for function in coordinator.functions.values()
        if function.function_type in CLIMATE_FUNCTION_TYPES
        and function.point("Set-Point") is not None
    )


class GiraX1Climate(GiraX1Entity, ClimateEntity):
    """A conservative heat-only representation of a Gira controller."""

    _attr_temperature_unit = UnitOfTemperature.CELSIUS

    def __init__(self, coordinator, function: GiraFunction) -> None:
        super().__init__(coordinator, function)
        self._attr_hvac_modes = [HVACMode.HEAT]
        features = ClimateEntityFeature.TARGET_TEMPERATURE
        if function.point("OnOff") is not None:
            self._attr_hvac_modes = [HVACMode.OFF, HVACMode.HEAT]
            features |= ClimateEntityFeature.TURN_ON | ClimateEntityFeature.TURN_OFF
        self._attr_supported_features = features

    @property
    def current_temperature(self) -> float | None:
        value = coerce_value(self.value("Current"))
        return float(value) if isinstance(value, (int, float)) else None

    @property
    def target_temperature(self) -> float | None:
        value = coerce_value(self.value("Set-Point"))
        return float(value) if isinstance(value, (int, float)) else None

    @property
    def hvac_mode(self) -> HVACMode:
        if (
            self.function.point("OnOff") is not None
            and as_bool(self.value("OnOff")) is False
        ):
            return HVACMode.OFF
        return HVACMode.HEAT

    async def async_set_temperature(self, **kwargs: Any) -> None:
        if ATTR_TEMPERATURE in kwargs:
            await self.write("Set-Point", float(kwargs[ATTR_TEMPERATURE]))

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        if self.function.point("OnOff") is None:
            return
        await self.write("OnOff", 0 if hvac_mode == HVACMode.OFF else 1)

    async def async_turn_on(self) -> None:
        await self.write("OnOff", 1)

    async def async_turn_off(self) -> None:
        await self.write("OnOff", 0)
