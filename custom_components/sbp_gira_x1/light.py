"""Lights exposed by the Gira X1 UI configuration."""

from __future__ import annotations

from typing import Any

from homeassistant.components.light import (
    DEFAULT_MAX_KELVIN,
    DEFAULT_MIN_KELVIN,
    ColorMode,
    LightEntity,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import GiraX1ConfigEntry
from .const import LIGHT_FUNCTION_TYPES
from .entity import GiraX1Entity
from .models import GiraFunction, as_bool, coerce_value


async def async_setup_entry(
    hass: HomeAssistant,
    entry: GiraX1ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up all light-like Gira functions."""
    coordinator = entry.runtime_data.coordinator
    async_add_entities(
        GiraX1Light(coordinator, function)
        for function in coordinator.functions.values()
        if function.function_type in LIGHT_FUNCTION_TYPES
        and function.point("OnOff") is not None
    )


class GiraX1Light(GiraX1Entity, LightEntity):
    """A switchable, dimmable or tunable Gira light."""

    def __init__(self, coordinator, function: GiraFunction) -> None:
        super().__init__(coordinator, function)
        if function.point("Color-Temperature") is not None:
            mode = ColorMode.COLOR_TEMP
            self._attr_min_color_temp_kelvin = DEFAULT_MIN_KELVIN
            self._attr_max_color_temp_kelvin = DEFAULT_MAX_KELVIN
        elif function.point("Brightness") is not None:
            mode = ColorMode.BRIGHTNESS
        else:
            mode = ColorMode.ONOFF
        self._attr_supported_color_modes = {mode}
        self._attr_color_mode = mode

    @property
    def is_on(self) -> bool | None:
        return as_bool(self.value("OnOff"))

    @property
    def brightness(self) -> int | None:
        value = coerce_value(self.value("Brightness"))
        if not isinstance(value, (int, float)):
            return None
        return round(max(0, min(100, value)) * 255 / 100)

    @property
    def color_temp_kelvin(self) -> int | None:
        value = coerce_value(self.value("Color-Temperature"))
        if not isinstance(value, (int, float)):
            return None
        return round(value)

    async def async_turn_on(self, **kwargs: Any) -> None:
        brightness_point = self.function.point("Brightness")
        if "brightness" in kwargs and brightness_point:
            # Absolute dimming is the command, not a prelude to switching on.
            # A following OnOff=1 can restore the actuator's switch-on level.
            if not brightness_point.can_write:
                raise ValueError("Gira brightness data point is not writable")
            brightness = max(0, min(255, kwargs["brightness"]))
            if brightness == 0:
                await self.write("OnOff", 0)
                return
            if "color_temp_kelvin" in kwargs and self.function.point("Color-Temperature"):
                await self.write("Color-Temperature", round(kwargs["color_temp_kelvin"]))
            await self.write("Brightness", round(brightness * 100 / 255, 1))
            return
        # Plain turn-on retains the actuator's configured switch-on behavior.
        # Changing color on an already-on light must not re-trigger that level.
        if self.is_on is not True:
            await self.write("OnOff", 1)
        if "color_temp_kelvin" in kwargs and self.function.point("Color-Temperature"):
            await self.write("Color-Temperature", round(kwargs["color_temp_kelvin"]))

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.write("OnOff", 0)
