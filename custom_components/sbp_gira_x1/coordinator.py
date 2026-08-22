"""Data coordinator for SBP Gira X1."""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntryAuthFailed
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import GiraX1AuthError, GiraX1Client, GiraX1Error
from .models import GiraFunction, parse_ui_config

_LOGGER = logging.getLogger(__name__)


class GiraX1Coordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Keep X1 configuration and current values synchronized."""

    def __init__(
        self,
        hass: HomeAssistant,
        client: GiraX1Client,
        device_info: dict[str, Any],
        scan_interval: int,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name="SBP Gira X1",
            update_interval=timedelta(seconds=scan_interval),
        )
        self.client = client
        self.device_info = device_info
        self.functions: dict[str, GiraFunction] = {}
        self._config_uid = ""

    async def _async_update_data(self) -> dict[str, Any]:
        try:
            config_uid = await self.client.async_get_ui_config_uid()
            if not self.functions or config_uid != self._config_uid:
                raw_config = await self.client.async_get_ui_config()
                self.functions = parse_ui_config(raw_config)
                self._config_uid = str(raw_config.get("uid") or config_uid)
                _LOGGER.info(
                    "Loaded %d functions from Gira X1 %s",
                    len(self.functions),
                    self.client.host,
                )
            readable_functions = [
                function.uid
                for function in self.functions.values()
                if any(point.can_read for point in function.data_points.values())
            ]
            values = await self.client.async_get_all_values(readable_functions)
            return {
                "config_uid": self._config_uid,
                "functions": self.functions,
                "values": values,
            }
        except GiraX1AuthError as err:
            raise ConfigEntryAuthFailed from err
        except GiraX1Error as err:
            raise UpdateFailed(str(err)) from err

    async def async_write_value(self, uid: str, value: Any) -> None:
        """Write a value and refresh immediately."""
        await self.client.async_set_value(uid, value)
        await self.async_request_refresh()
