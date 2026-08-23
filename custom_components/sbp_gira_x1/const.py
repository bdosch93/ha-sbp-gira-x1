"""Constants for the SBP Gira X1 integration."""

from typing import Final

from homeassistant.const import Platform

DOMAIN: Final = "sbp_gira_x1"

CONF_SCAN_INTERVAL: Final = "scan_interval"
CONF_TOKEN: Final = "token"

DEFAULT_SCAN_INTERVAL: Final = 15
MIN_SCAN_INTERVAL: Final = 5
MAX_SCAN_INTERVAL: Final = 300

CLIENT_ID: Final = "io.github.bdosch93.homeassistant.gira_x1"

PLATFORMS: Final = (
    Platform.BINARY_SENSOR,
    Platform.BUTTON,
    Platform.CLIMATE,
    Platform.COVER,
    Platform.LIGHT,
    Platform.SENSOR,
    Platform.SWITCH,
)

SCENE_FUNCTION_TYPES: Final = {
    "de.gira.schema.functions.Scene",
}

SCENE_CHANNEL_TYPES: Final = {
    "de.gira.schema.channels.SceneControl",
    "de.gira.schema.channels.SceneSet",
}

LIGHT_FUNCTION_TYPES: Final = {
    "de.gira.schema.functions.KNX.Light",
    "de.gira.schema.functions.ColoredLight",
    "de.gira.schema.functions.TunableLight",
}

SWITCH_FUNCTION_TYPES: Final = {
    "de.gira.schema.functions.Switch",
}

COVER_FUNCTION_TYPES: Final = {
    "de.gira.schema.functions.Covering",
}

CLIMATE_FUNCTION_TYPES: Final = {
    "de.gira.schema.functions.SaunaHeating",
    "de.gira.schema.functions.KNX.HeatingCooling",
    "de.gira.schema.functions.KNX.FanCoil",
}

BINARY_SENSOR_FUNCTION_TYPES: Final = {
    "de.gira.schema.functions.BinaryStatus",
}

SENSOR_FUNCTION_TYPES: Final = {
    "de.gira.schema.functions.NumericUnsignedStatus",
    "de.gira.schema.functions.NumericSignedStatus",
    "de.gira.schema.functions.NumericFloatStatus",
    "de.gira.schema.functions.TextStatus",
}
