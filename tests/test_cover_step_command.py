"""Test the actual diagnostic method without a running Home Assistant."""

import ast
from pathlib import Path
from types import SimpleNamespace
from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock

SOURCE = Path(__file__).parents[1] / "custom_components/sbp_gira_x1/cover.py"
tree = ast.parse(SOURCE.read_text(encoding="utf-8"))
cls = next(n for n in tree.body if isinstance(n, ast.ClassDef))
method = next(n for n in cls.body if isinstance(n, ast.AsyncFunctionDef) and n.name == "async_test_cover_step")
namespace = {"HomeAssistantError": RuntimeError}
exec(compile(ast.Module(body=[method], type_ignores=[]), str(SOURCE), "exec"), namespace)


class CoverStepCommandTests(IsolatedAsyncioTestCase):
    def entity(self, current_uid="a09s", writable=True):
        bound = SimpleNamespace(uid="a09s", can_write=True)
        current = SimpleNamespace(uid=current_uid, can_write=writable)
        function = SimpleNamespace(uid="a09r", point=lambda _: bound)
        return SimpleNamespace(
            function=function,
            coordinator=SimpleNamespace(functions={"a09r": SimpleNamespace(point=lambda _: current)}),
            write=AsyncMock(),
        )

    async def test_zero_is_single_step_write_without_direction(self):
        entity = self.entity()
        await namespace["async_test_cover_step"](entity, 0, "a09s")
        entity.write.assert_awaited_once_with("Step-Up-Down", 0)

    async def test_mapping_change_rejected_before_write(self):
        entity = self.entity(current_uid="different")
        with self.assertRaises(RuntimeError):
            await namespace["async_test_cover_step"](entity, 0, "a09s")
        entity.write.assert_not_awaited()

    async def test_invalid_values_rejected_before_write(self):
        for value in (2, -1, True, "0", 0.5):
            entity = self.entity()
            with self.assertRaises(RuntimeError):
                await namespace["async_test_cover_step"](entity, value, "a09s")
            entity.write.assert_not_awaited()

    async def test_readonly_point_rejected_before_write(self):
        entity = self.entity(writable=False)
        with self.assertRaises(RuntimeError):
            await namespace["async_test_cover_step"](entity, 0, "a09s")
        entity.write.assert_not_awaited()
