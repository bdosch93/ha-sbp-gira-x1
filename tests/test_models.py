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


if __name__ == "__main__":
    unittest.main()
