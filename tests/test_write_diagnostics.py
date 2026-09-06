"""Exercise the actual entity write method without a Home Assistant runtime."""

import ast
from collections import deque
from datetime import datetime, timezone
from pathlib import Path
from time import monotonic
from types import SimpleNamespace
from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock

SOURCE = Path(__file__).parents[1] / "custom_components/sbp_gira_x1/entity.py"
tree = ast.parse(SOURCE.read_text(encoding="utf-8"))
cls = next(node for node in tree.body if isinstance(node, ast.ClassDef))
method = next(node for node in cls.body if isinstance(node, ast.AsyncFunctionDef) and node.name == "write")
namespace = {"datetime": datetime, "timezone": timezone, "monotonic": monotonic}
exec(compile(ast.Module(body=[method], type_ignores=[]), str(SOURCE), "exec"), namespace)


class WriteDiagnosticsTests(IsolatedAsyncioTestCase):
    def setup_entity(self, writable=True):
        point = SimpleNamespace(uid="p1", can_write=writable)
        function = SimpleNamespace(uid="f1", function_type="de.gira.schema.functions.Covering", point=lambda name: point)
        client = SimpleNamespace(cover_write_events=deque(maxlen=40), async_set_value=AsyncMock())
        coordinator = SimpleNamespace(client=client, functions={"f1": function}, async_request_refresh=AsyncMock())
        return SimpleNamespace(function=function, coordinator=coordinator, entity_id="cover.test")

    async def test_one_write_then_refresh_and_event(self):
        entity = self.setup_entity()
        await namespace["write"](entity, "Up-Down", 0)
        entity.coordinator.client.async_set_value.assert_awaited_once_with("p1", 0)
        entity.coordinator.async_request_refresh.assert_awaited_once()
        event = entity.coordinator.client.cover_write_events[-1]
        self.assertEqual(event["result"], "write_returned_without_error")
        self.assertEqual(event["current_point_uid"], "p1")

    async def test_failure_omits_secret_message(self):
        entity = self.setup_entity()
        entity.coordinator.client.async_set_value.side_effect = ValueError("SECRET_TOKEN")
        with self.assertRaises(ValueError):
            await namespace["write"](entity, "Up-Down", 1)
        entity.coordinator.async_request_refresh.assert_not_awaited()
        event = entity.coordinator.client.cover_write_events[-1]
        self.assertEqual(event["result"], "write_failed")
        self.assertNotIn("SECRET_TOKEN", str(event))

    async def test_missing_permission_is_recorded_without_write(self):
        entity = self.setup_entity(False)
        await namespace["write"](entity, "Up-Down", 1)
        entity.coordinator.client.async_set_value.assert_not_awaited()
        self.assertEqual(entity.coordinator.client.cover_write_events[-1]["result"], "skipped_not_writable")

    async def test_refresh_failure_distinct(self):
        entity = self.setup_entity()
        entity.coordinator.async_request_refresh.side_effect = ValueError("refresh")
        with self.assertRaises(ValueError):
            await namespace["write"](entity, "Up-Down", 1)
        self.assertEqual(entity.coordinator.client.cover_write_events[-1]["result"], "refresh_failed")
