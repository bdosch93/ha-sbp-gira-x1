"""SBP Gira X1 integration."""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant

from .api import GiraX1Client
from .const import CONF_SCAN_INTERVAL, CONF_TOKEN, DEFAULT_SCAN_INTERVAL, PLATFORMS
from .coordinator import GiraX1Coordinator


@dataclass(slots=True)
class GiraX1RuntimeData:
    """Runtime data attached to the config entry."""

    coordinator: GiraX1Coordinator


type GiraX1ConfigEntry = ConfigEntry[GiraX1RuntimeData]


async def _async_reload_entry(hass: HomeAssistant, entry: GiraX1ConfigEntry) -> None:
    """Reload after the polling option changes."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_setup_entry(hass: HomeAssistant, entry: GiraX1ConfigEntry) -> bool:
    """Set up one Gira X1 config entry."""
    client = GiraX1Client(hass, entry.data[CONF_HOST], entry.data[CONF_TOKEN])
    device_info = await client.async_get_device_info()
    coordinator = GiraX1Coordinator(
        hass,
        client,
        device_info,
        int(entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)),
    )
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = GiraX1RuntimeData(coordinator)
    entry.async_on_unload(entry.add_update_listener(_async_reload_entry))
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: GiraX1ConfigEntry) -> bool:
    """Unload one Gira X1 config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
