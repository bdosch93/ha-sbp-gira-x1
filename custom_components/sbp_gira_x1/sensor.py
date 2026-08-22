"""Numeric and text status functions exposed by Gira X1."""

from __future__ import annotations

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import PERCENTAGE, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import GiraX1ConfigEntry
from .const import SENSOR_FUNCTION_TYPES
from .entity import GiraX1Entity
from .models import GiraFunction, coerce_value


async def async_setup_entry(
    hass: HomeAssistant,
    entry: GiraX1ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up generic status sensors."""
    coordinator = entry.runtime_data.coordinator
    async_add_entities(
        GiraX1Sensor(coordinator, function)
        for function in coordinator.functions.values()
        if function.function_type in SENSOR_FUNCTION_TYPES
        and _readable_point(function) is not None
    )


def _readable_point(function: GiraFunction):
    return next(
        (point for point in function.data_points.values() if point.can_read), None
    )


class GiraX1Sensor(GiraX1Entity, SensorEntity):
    """One Gira status function represented by its readable data point."""

    def __init__(self, coordinator, function: GiraFunction) -> None:
        super().__init__(coordinator, function)
        self._point = _readable_point(function)
        descriptor = (
            f"{function.name} {function.channel_type} {self._point.name}".casefold()
        )
        if "temperatur" in descriptor or "temperature" in descriptor:
            self._attr_device_class = SensorDeviceClass.TEMPERATURE
            self._attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
            self._attr_state_class = SensorStateClass.MEASUREMENT
        elif (
            "prozent" in descriptor
            or "percent" in descriptor
            or "humidity" in descriptor
        ):
            self._attr_native_unit_of_measurement = PERCENTAGE
            self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self):
        if self._point is None or self.coordinator.data is None:
            return None
        return coerce_value(self.coordinator.data["values"].get(self._point.uid))
