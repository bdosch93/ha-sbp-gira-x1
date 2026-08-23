"""Unit tests for the API response parser without Home Assistant imports."""

import importlib.util
import sys
import unittest
from pathlib import Path

MODELS = Path(__file__).parents[1] / "custom_components" / "sbp_gira_x1" / "models.py"
SPEC = importlib.util.spec_from_file_location("sbp_gira_x1_models", MODELS)
module = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
sys.modules[SPEC.name] = module
SPEC.loader.exec_module(module)


class ParseUiConfigTests(unittest.TestCase):
    def test_parses_flags_and_location(self):
        raw = {
            "functions": [
                {
                    "uid": "f1",
                    "displayName": "Deckenlicht",
                    "functionType": "de.gira.schema.functions.KNX.Light",
                    "channelType": "de.gira.schema.channels.KNX.Dimmer",
                    "dataPoints": [
                        {
                            "uid": "p1",
                            "name": "OnOff",
                            "canRead": True,
                            "canWrite": True,
                            "canEvent": True,
                        }
                    ],
                }
            ],
            "locations": [
                {
                    "displayName": "Erdgeschoss",
                    "locations": [
                        {"displayName": "Küche", "functions": [{"uid": "f1"}]}
                    ],
                }
            ],
            "trades": [{"displayName": "Licht", "functions": ["f1"]}],
        }
        function = module.parse_ui_config(raw)["f1"]
        self.assertEqual(function.location, "Erdgeschoss / Küche")
        self.assertEqual(function.trade, "Licht")
        self.assertTrue(function.point("OnOff").can_write)

    def test_coercion(self):
        self.assertEqual(module.coerce_value("42.5"), 42.5)
        self.assertEqual(module.coerce_value("1"), 1)
        self.assertIsNone(module.coerce_value(""))
        self.assertTrue(module.as_bool("1"))
        self.assertFalse(module.as_bool("0"))

    def test_cover_tilt_is_hidden_for_shutters(self):
        function = module.GiraFunction(
            uid="cover-1",
            name="Rollladen",
            function_type="de.gira.schema.functions.Covering",
            channel_type="de.gira.schema.channels.KNX.Covering",
            data_points={
                "Slat-Position": module.GiraDataPoint(
                    uid="slat-1",
                    name="Slat-Position",
                    can_write=True,
                )
            },
        )

        self.assertTrue(module.exposes_cover_tilt(function, is_shutter=False))
        self.assertFalse(module.exposes_cover_tilt(function, is_shutter=True))

    def test_cover_tilt_requires_a_writable_data_point(self):
        function = module.GiraFunction(
            uid="cover-2",
            name="Rollladen",
            function_type="de.gira.schema.functions.Covering",
            channel_type="de.gira.schema.channels.KNX.Covering",
            data_points={
                "Slat-Position": module.GiraDataPoint(
                    uid="slat-2",
                    name="Slat-Position",
                    can_write=False,
                )
            },
        )

        self.assertFalse(module.exposes_cover_tilt(function, is_shutter=False))

    def test_scene_number_from_key_parameter(self):
        function = module.GiraFunction(
            uid="scene-1",
            name="Sonnig",
            function_type="de.gira.schema.functions.Scene",
            channel_type="de.gira.schema.channels.SceneSet",
            data_points={},
            parameters=({"key": "Scene", "value": "12"},),
        )

        self.assertEqual(function.parameter("scene"), 12)
        self.assertEqual(function.scene_number(), 12)

    def test_scene_number_from_name_parameter(self):
        function = module.GiraFunction(
            uid="scene-2",
            name="Schatten",
            function_type="de.gira.schema.functions.Scene",
            channel_type="de.gira.schema.channels.SceneControl",
            data_points={},
            parameters=({"name": "Scene", "value": 64},),
        )

        self.assertEqual(function.scene_number(), 64)

    def test_scene_number_rejects_out_of_range_values(self):
        function = module.GiraFunction(
            uid="scene-3",
            name="Ungültig",
            function_type="de.gira.schema.functions.Scene",
            channel_type="de.gira.schema.channels.SceneSet",
            data_points={},
            parameters=({"key": "Scene", "value": "65"},),
        )

        self.assertIsNone(function.scene_number())

    def test_function_scene_uses_execute_trigger(self):
        function = module.GiraFunction(
            uid="function-scene-1",
            name="Beschattung",
            function_type="de.gira.schema.functions.FunctionScene",
            channel_type="de.gira.schema.channels.FunctionScene",
            data_points={},
        )

        self.assertIsNone(function.scene_number())
        self.assertEqual(function.scene_recall_value(), 1)


if __name__ == "__main__":
    unittest.main()
