"""Passive diagnostics contain only intended cover metadata and values."""

import importlib.util
import unittest
from pathlib import Path
from types import SimpleNamespace

PATH = Path(__file__).parents[1] / "custom_components/sbp_gira_x1/diagnostic_helpers.py"
SPEC = importlib.util.spec_from_file_location("diagnostic_helpers", PATH)
module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(module)


class DiagnosticsTests(unittest.TestCase):
    def function(self, kind="de.gira.schema.functions.Covering"):
        return SimpleNamespace(
            uid="f1", name="Roof", location="Room", channel_type="Blind",
            function_type=kind,
            data_points={
                "Up-Down": SimpleNamespace(uid="p1", can_read=True, can_write=True),
                "Position": SimpleNamespace(uid="p2", can_read=True, can_write=False),
                "Secret": SimpleNamespace(uid="secret", can_read=True, can_write=False),
            },
        )

    def test_cached_zero_and_missing_are_distinct(self):
        result = module.cover_diagnostics([self.function()], {"p1": 0}, {})[0]
        self.assertTrue(result["data_points"]["Up-Down"]["has_cached_value"])
        self.assertEqual(result["data_points"]["Up-Down"]["value"], 0)
        self.assertFalse(result["data_points"]["Position"]["has_cached_value"])
        self.assertIsNone(result["read_error_type"])

    def test_only_cover_allowlisted_points(self):
        result = module.cover_diagnostics(
            [self.function(), self.function("Light")], {"secret": "hidden"},
            {"f1": "GiraX1ConnectionError"},
        )
        self.assertEqual(len(result), 1)
        self.assertNotIn("Secret", result[0]["data_points"])
        self.assertEqual(result[0]["read_error_type"], "GiraX1ConnectionError")

    def test_empty_snapshot(self):
        self.assertEqual(module.cover_diagnostics([], {}, {}), [])
