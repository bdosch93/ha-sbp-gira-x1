"""Binary status functions exposed by the Gira X1 UI configuration."""

from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import GiraX1ConfigEntry
from .const import BINARY_SENSOR_FUNCTION_TYPES
from .entity import GiraX1Entity
from .models import GiraFunction, as_bool


async def async_setup_entry(
    hass: HomeAssistant,
    entry: GiraX1ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up binary sensors."""
    coordinator = entry.runtime_data.coordinator
    async_add_entities(
        GiraX1BinarySensor(coordinator, function)
        for function in coordinator.functions.values()
        if function.function_type in BINARY_SENSOR_FUNCTION_TYPES
        and _readable_point(function) is not None
    )


def _readable_point(function: GiraFunction):
    return next(
        (point for point in function.data_points.values() if point.can_read), None
    )


class GiraX1BinarySensor(GiraX1Entity, BinarySensorEntity):
    """A read-only binary Gira status."""

    def __init__(self, coordinator, function: GiraFunction) -> None:
        super().__init__(coordinator, function)
        self._point = _readable_point(function)
        name = function.name.casefold()
        if "beweg" in name or "motion" in name:
            self._attr_device_class = BinarySensorDeviceClass.MOTION
        elif "präsenz" in name or "presence" in name or "anwesen" in name:
            self._attr_device_class = BinarySensorDeviceClass.OCCUPANCY
        elif "fenster" in name or "window" in name:
            self._attr_device_class = BinarySensorDeviceClass.WINDOW
        elif "tür" in name or "door" in name:
            self._attr_device_class = BinarySensorDeviceClass.DOOR

    @property
    def is_on(self) -> bool | None:
        if self._point is None or self.coordinator.data is None:
            return None
        return as_bool(self.coordinator.data["values"].get(self._point.uid))
