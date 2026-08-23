"""Pure data models and mapping helpers for Gira X1."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class GiraDataPoint:
    """One Gira function data point."""

    uid: str
    name: str
    can_read: bool = True
    can_write: bool = False
    can_event: bool = False


@dataclass(frozen=True, slots=True)
class GiraFunction:
    """One user-visible Gira function."""

    uid: str
    name: str
    function_type: str
    channel_type: str
    data_points: dict[str, GiraDataPoint]
    parameters: tuple[dict[str, Any], ...] = ()
    location: str | None = None
    trade: str | None = None

    def point(self, name: str) -> GiraDataPoint | None:
        """Return a data point by its logical channel name."""
        return self.data_points.get(name)

    def parameter(self, name: str) -> Any:
        """Return a UI-config parameter by name across Gira firmware shapes."""
        wanted = name.casefold()
        for parameter in self.parameters:
            key = (
                parameter.get("key")
                or parameter.get("name")
                or parameter.get("parameter")
                or parameter.get("parameterName")
            )
            if str(key or "").casefold() == wanted:
                return coerce_value(parameter.get("value"))
        return None

    def scene_number(self) -> int | None:
        """Return the configured Gira scene number when it is valid."""
        value = self.parameter("Scene")
        if isinstance(value, (int, float)) and int(value) == value:
            number = int(value)
            if 1 <= number <= 64:
                return number
        return None

    def scene_recall_value(self) -> int | None:
        """Return the safe value that recalls this Gira scene function."""
        if (
            self.function_type == "de.gira.schema.functions.FunctionScene"
            and self.channel_type == "de.gira.schema.channels.FunctionScene"
        ):
            return 1
        return self.scene_number()


def _function_uid(value: Any) -> str | None:
    """Extract a function UID from the two shapes used by Gira firmware."""
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        uid = value.get("uid")
        return str(uid) if uid else None
    return None


def _collect_locations(
    locations: list[dict[str, Any]],
    parent: tuple[str, ...] = (),
) -> dict[str, str]:
    """Build function UID to human-readable GPA location path."""
    result: dict[str, str] = {}
    for location in locations:
        name = str(location.get("displayName") or "").strip()
        path = (*parent, name) if name else parent
        label = " / ".join(path)
        for item in location.get("functions", []):
            if uid := _function_uid(item):
                result[uid] = label
        children = location.get("locations", [])
        if isinstance(children, list):
            result.update(_collect_locations(children, path))
    return result


def parse_ui_config(raw: dict[str, Any]) -> dict[str, GiraFunction]:
    """Parse the official Gira UI configuration response."""
    locations = _collect_locations(raw.get("locations", []))
    trades: dict[str, str] = {}
    for trade in raw.get("trades", []):
        trade_name = str(trade.get("displayName") or "").strip()
        for item in trade.get("functions", []):
            if uid := _function_uid(item):
                trades[uid] = trade_name

    functions: dict[str, GiraFunction] = {}
    for item in raw.get("functions", []):
        uid = str(item.get("uid") or "").strip()
        if not uid:
            continue
        points: dict[str, GiraDataPoint] = {}
        for point in item.get("dataPoints", []):
            point_uid = str(point.get("uid") or "").strip()
            point_name = str(point.get("name") or "").strip()
            if not point_uid or not point_name:
                continue
            points[point_name] = GiraDataPoint(
                uid=point_uid,
                name=point_name,
                can_read=bool(point.get("canRead", True)),
                can_write=bool(point.get("canWrite", False)),
                can_event=bool(point.get("canEvent", False)),
            )
        functions[uid] = GiraFunction(
            uid=uid,
            name=str(item.get("displayName") or uid),
            function_type=str(item.get("functionType") or ""),
            channel_type=str(item.get("channelType") or ""),
            data_points=points,
            parameters=tuple(item.get("parameters", [])),
            location=locations.get(uid),
            trade=trades.get(uid),
        )
    return functions


def coerce_value(value: Any) -> Any:
    """Convert Gira's string values to useful native scalar types."""
    if not isinstance(value, str):
        return value
    stripped = value.strip()
    if stripped == "":
        return None
    if stripped in {"0", "1"}:
        return int(stripped)
    try:
        number = float(stripped)
    except ValueError:
        return stripped
    return int(number) if number.is_integer() else number


def exposes_cover_tilt(function: GiraFunction, *, is_shutter: bool) -> bool:
    """Return whether a cover should expose a writable tilt control.

    Gira projects can expose a writable ``Slat-Position`` data point even for
    roller shutters that have no user-visible tilt capability. Home Assistant's
    user-selected ``shutter`` device class is the authoritative presentation
    override in that case.
    """
    point = function.point("Slat-Position")
    return not is_shutter and point is not None and point.can_write


def as_bool(value: Any) -> bool | None:
    """Convert a Gira binary value to bool."""
    native = coerce_value(value)
    if native in (0, False):
        return False
    if native in (1, True):
        return True
    return None
