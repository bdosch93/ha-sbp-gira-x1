"""Async client for the official Gira IoT REST API v2."""

from __future__ import annotations

import asyncio
from collections import deque
from collections.abc import Iterable
from typing import Any

import aiohttp
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import CLIENT_ID


class GiraX1Error(Exception):
    """Base API error."""


class GiraX1AuthError(GiraX1Error):
    """Authentication or token error."""


class GiraX1ConnectionError(GiraX1Error):
    """Connection or protocol error."""


class GiraX1Client:
    """Small, token-based client for one X1."""

    def __init__(
        self, hass: HomeAssistant, host: str, token: str | None = None
    ) -> None:
        self.host = (
            host.strip().removeprefix("https://").removeprefix("http://").rstrip("/")
        )
        self.token = token
        self._base_url = f"https://{self.host}/api/v2"
        # Gira documents that its appliance certificate cannot be publicly trusted.
        self._session = async_get_clientsession(hass, verify_ssl=False)
        self._timeout = aiohttp.ClientTimeout(total=15)
        # Current poll only; exception messages may contain secret-bearing URLs.
        self.last_read_errors: dict[str, str] = {}
        self.cover_write_events: deque[dict[str, Any]] = deque(maxlen=40)

    async def _request(
        self,
        method: str,
        path: str,
        *,
        token_required: bool = True,
        auth: aiohttp.BasicAuth | None = None,
        json: dict[str, Any] | None = None,
    ) -> Any:
        params = None
        if token_required:
            if not self.token:
                raise GiraX1AuthError("No Gira X1 token available")
            params = {"token": self.token}
        try:
            async with self._session.request(
                method,
                f"{self._base_url}{path}",
                params=params,
                auth=auth,
                json=json,
                timeout=self._timeout,
            ) as response:
                if response.status in (401, 403):
                    raise GiraX1AuthError("Gira X1 rejected authentication")
                if response.status >= 400:
                    body = (await response.text())[:300]
                    raise GiraX1ConnectionError(
                        f"Gira X1 returned HTTP {response.status}: {body}"
                    )
                if response.status == 204:
                    return None
                return await response.json(content_type=None)
        except GiraX1Error:
            raise
        except (aiohttp.ClientError, TimeoutError, ValueError) as err:
            raise GiraX1ConnectionError(str(err)) from err

    async def async_get_device_info(self) -> dict[str, Any]:
        """Read the unauthenticated API availability response."""
        data = await self._request("GET", "/", token_required=False)
        if data.get("info") != "GDS-REST-API" or str(data.get("version")) != "2":
            raise GiraX1ConnectionError("Target is not a Gira IoT REST API v2 device")
        return data

    async def async_register(self, username: str, password: str) -> str:
        """Register this HA client and retain only the returned access token."""
        data = await self._request(
            "POST",
            "/clients",
            token_required=False,
            auth=aiohttp.BasicAuth(username, password),
            json={"client": CLIENT_ID},
        )
        token = str(data.get("token") or "")
        if len(token) != 32 or not token.isalnum():
            raise GiraX1AuthError("Gira X1 did not return a valid access token")
        self.token = token
        return token

    async def async_unregister(self) -> None:
        """Invalidate the current token."""
        if self.token:
            await self._request(
                "DELETE", f"/clients/{self.token}", token_required=False
            )
            self.token = None

    async def async_get_ui_config_uid(self) -> str:
        """Return the current GPA UI configuration identifier."""
        data = await self._request("GET", "/uiconfig/uid")
        return str(data.get("uid") or "")

    async def async_get_ui_config(self) -> dict[str, Any]:
        """Return functions, data-point flags, locations, trades and parameters."""
        if not self.token:
            raise GiraX1AuthError("No Gira X1 token available")
        try:
            async with self._session.get(
                f"{self._base_url}/uiconfig",
                params={
                    "token": self.token,
                    "expand": "dataPointFlags,parameters,locations,trades",
                },
                timeout=self._timeout,
            ) as response:
                if response.status in (401, 403):
                    raise GiraX1AuthError("Gira X1 rejected authentication")
                if response.status >= 400:
                    raise GiraX1ConnectionError(
                        f"Gira X1 returned HTTP {response.status} for UI config"
                    )
                return await response.json(content_type=None)
        except GiraX1Error:
            raise
        except (aiohttp.ClientError, TimeoutError, ValueError) as err:
            raise GiraX1ConnectionError(str(err)) from err

    async def async_get_function_values(self, function_uid: str) -> dict[str, Any]:
        """Read all values for one function."""
        data = await self._request("GET", f"/values/{function_uid}")
        return {
            str(item["uid"]): item.get("value")
            for item in data.get("values", [])
            if item.get("uid")
        }

    async def async_get_all_values(
        self, function_uids: Iterable[str]
    ) -> dict[str, Any]:
        """Read values without failing the hub for one unsupported function."""
        semaphore = asyncio.Semaphore(6)

        async def fetch(uid: str) -> dict[str, Any]:
            async with semaphore:
                return await self.async_get_function_values(uid)

        function_uids = tuple(function_uids)
        values: dict[str, Any] = {}
        results = await asyncio.gather(
            *(fetch(uid) for uid in function_uids), return_exceptions=True
        )
        errors: list[BaseException] = []
        self.last_read_errors = {}
        for uid, result in zip(function_uids, results):
            if isinstance(result, BaseException):
                errors.append(result)
                self.last_read_errors[uid] = type(result).__name__
            else:
                values.update(result)
        if errors and not values:
            first = errors[0]
            if isinstance(first, GiraX1Error):
                raise first
            raise GiraX1ConnectionError(str(first)) from first
        return values

    async def async_set_value(self, uid: str, value: Any) -> None:
        """Write one official Gira data point."""
        await self._request("PUT", f"/values/{uid}", json={"value": value})
