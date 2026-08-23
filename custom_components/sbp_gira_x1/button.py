"""Stateless scene recall buttons exposed by the Gira X1 UI configuration."""

from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import GiraX1ConfigEntry
from .const import SCENE_CHANNEL_TYPES, SCENE_FUNCTION_TYPES
from .entity import GiraX1Entity
from .models import GiraFunction


def _scene_point_name(function: GiraFunction) -> str | None:
    """Return the recall-only data point for a supported scene channel."""
    if function.channel_type in {
        "de.gira.schema.channels.FunctionScene",
        "de.gira.schema.channels.SceneSet",
    }:
        return "Execute"
    if function.channel_type == "de.gira.schema.channels.SceneControl":
        return "Scene"
    return None


def _is_recallable_scene(function: GiraFunction) -> bool:
    """Return whether the scene can be recalled without exposing teach."""
    point_name = _scene_point_name(function)
    point = function.point(point_name) if point_name else None
    return (
        function.function_type in SCENE_FUNCTION_TYPES
        and function.channel_type in SCENE_CHANNEL_TYPES
        and function.scene_recall_value() is not None
        and point is not None
        and point.can_write
    )


async def async_setup_entry(
    hass: HomeAssistant,
    entry: GiraX1ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up safe, stateless Gira scene recall buttons."""
    coordinator = entry.runtime_data.coordinator
    async_add_entities(
        GiraX1SceneButton(coordinator, function)
        for function in coordinator.functions.values()
        if _is_recallable_scene(function)
    )


class GiraX1SceneButton(GiraX1Entity, ButtonEntity):
    """Recall one scene already configured in the Gira X1."""

    _attr_icon = "mdi:palette-outline"

    def __init__(self, coordinator, function: GiraFunction) -> None:
        super().__init__(coordinator, function)
        self._recall_value = function.scene_recall_value()
        self._scene_number = function.scene_number()
        self._point_name = _scene_point_name(function)

    async def async_press(self) -> None:
        """Recall the configured X1 scene; never write the Teach point."""
        if self._recall_value is None or self._point_name is None:
            return
        await self.write(self._point_name, self._recall_value)

    @property
    def extra_state_attributes(self):
        """Expose the scene number and safe action for diagnosis."""
        attributes = dict(super().extra_state_attributes)
        attributes["gira_scene_number"] = self._scene_number
        attributes["gira_scene_action"] = "recall"
        return attributes
