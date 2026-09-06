"""Base entity for SBP Gira X1."""

from __future__ import annotations

from datetime import datetime, timezone
from time import monotonic

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import GiraX1Coordinator
from .models import GiraFunction


class GiraX1Entity(CoordinatorEntity[GiraX1Coordinator]):
    """Base class shared by every X1 entity."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: GiraX1Coordinator, function: GiraFunction) -> None:
        super().__init__(coordinator)
        self.function = function
        self._attr_name = function.name
        self._attr_unique_id = f"{coordinator.client.host}:{function.uid}"
        info = coordinator.device_info
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.client.host)},
            name=str(info.get("deviceName") or "Gira X1"),
            manufacturer="Gira",
            model=str(info.get("deviceType") or "X1"),
            sw_version=str(info.get("deviceVersion") or "unknown"),
            configuration_url=f"https://{coordinator.client.host}",
        )

    def value(self, point_name: str):
        """Return the current raw value of a logical data point."""
        point = self.function.point(point_name)
        if point is None or self.coordinator.data is None:
            return None
        return self.coordinator.data["values"].get(point.uid)

    async def write(self, point_name: str, value) -> None:
        """Write a logical data point when the X1 marks it writable."""
        point = self.function.point(point_name)
        event = None
        if self.function.function_type == "de.gira.schema.functions.Covering":
            current = self.coordinator.functions.get(self.function.uid)
            current_point = current.point(point_name) if current else None
            event = {
                "at": datetime.now(timezone.utc).isoformat(),
                "entity_id": self.entity_id,
                "function_uid": self.function.uid,
                "point_name": point_name,
                "point_uid": point.uid if point else None,
                "current_point_uid": current_point.uid if current_point else None,
                "value": value,
                "result": "pending",
            }
            self.coordinator.client.cover_write_events.append(event)
        if point is None or not point.can_write:
            if event is not None:
                event["result"] = "skipped_not_writable"
            return
        if event is None:
            await self.coordinator.async_write_value(point.uid, value)
            return
        started = monotonic()
        try:
            # Same single write + refresh, but distinguish each failure stage.
            await self.coordinator.client.async_set_value(point.uid, value)
            event["result"] = "write_returned_without_error"
            await self.coordinator.async_request_refresh()
        except Exception as err:
            event["error_type"] = type(err).__name__
            event["result"] = (
                "refresh_failed" if event["result"] == "write_returned_without_error"
                else "write_failed"
            )
            raise
        finally:
            event["elapsed_seconds"] = round(monotonic() - started, 3)

    @property
    def extra_state_attributes(self):
        """Expose the GPA location/trade for diagnosis and dashboard building."""
        attributes = {
            "gira_function_uid": self.function.uid,
            "gira_function_type": self.function.function_type,
            "gira_channel_type": self.function.channel_type,
        }
        if self.function.location:
            attributes["gira_location"] = self.function.location
        if self.function.trade:
            attributes["gira_trade"] = self.function.trade
        return attributes
