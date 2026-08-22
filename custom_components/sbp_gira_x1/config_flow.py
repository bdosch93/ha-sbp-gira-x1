"""Config flow for SBP Gira X1."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import config_validation as cv

from .api import GiraX1AuthError, GiraX1Client, GiraX1ConnectionError
from .const import (
    CONF_SCAN_INTERVAL,
    CONF_TOKEN,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    MAX_SCAN_INTERVAL,
    MIN_SCAN_INTERVAL,
)


async def _register_and_validate(
    hass: HomeAssistant,
    host: str,
    username: str,
    password: str,
) -> tuple[dict[str, Any], str]:
    client = GiraX1Client(hass, host)
    device = await client.async_get_device_info()
    token = await client.async_register(username, password)
    await client.async_get_ui_config()
    return device, token


def _normalize_host(host: str) -> str:
    """Store a stable hostname/IP without a scheme or trailing slash."""
    return host.strip().removeprefix("https://").removeprefix("http://").rstrip("/")


class GiraX1ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Guide secure setup and token renewal."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Set up a new X1."""
        errors: dict[str, str] = {}
        if user_input is not None:
            host = _normalize_host(str(user_input[CONF_HOST]))
            await self.async_set_unique_id(host.casefold())
            self._abort_if_unique_id_configured()
            try:
                device, token = await _register_and_validate(
                    self.hass,
                    host,
                    user_input[CONF_USERNAME],
                    user_input[CONF_PASSWORD],
                )
            except GiraX1AuthError:
                errors["base"] = "invalid_auth"
            except GiraX1ConnectionError:
                errors["base"] = "cannot_connect"
            else:
                return self.async_create_entry(
                    title=str(device.get("deviceName") or f"Gira X1 {host}"),
                    data={CONF_HOST: host, CONF_TOKEN: token},
                    options={CONF_SCAN_INTERVAL: user_input[CONF_SCAN_INTERVAL]},
                )

        schema = vol.Schema(
            {
                vol.Required(CONF_HOST): cv.string,
                vol.Required(CONF_USERNAME): cv.string,
                vol.Required(CONF_PASSWORD): cv.string,
                vol.Optional(
                    CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL
                ): vol.All(
                    vol.Coerce(int), vol.Range(MIN_SCAN_INTERVAL, MAX_SCAN_INTERVAL)
                ),
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    async def async_step_reauth(self, entry_data: dict[str, Any]) -> FlowResult:
        """Start token renewal after the X1 rejects the stored token."""
        self._reauth_entry = self._get_reauth_entry()
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Request credentials only long enough to create a fresh token."""
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                _, token = await _register_and_validate(
                    self.hass,
                    self._reauth_entry.data[CONF_HOST],
                    user_input[CONF_USERNAME],
                    user_input[CONF_PASSWORD],
                )
            except GiraX1AuthError:
                errors["base"] = "invalid_auth"
            except GiraX1ConnectionError:
                errors["base"] = "cannot_connect"
            else:
                return self.async_update_reload_and_abort(
                    self._reauth_entry,
                    data_updates={CONF_TOKEN: token},
                )

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_USERNAME): cv.string,
                    vol.Required(CONF_PASSWORD): cv.string,
                }
            ),
            errors=errors,
        )

    @staticmethod
    def async_get_options_flow(config_entry: config_entries.ConfigEntry) -> OptionsFlow:
        """Return the options flow."""
        return OptionsFlow()


class OptionsFlow(config_entries.OptionsFlow):
    """Allow changing only the safe polling interval."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_SCAN_INTERVAL,
                        default=self.config_entry.options.get(
                            CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
                        ),
                    ): vol.All(
                        vol.Coerce(int),
                        vol.Range(MIN_SCAN_INTERVAL, MAX_SCAN_INTERVAL),
                    )
                }
            ),
        )
