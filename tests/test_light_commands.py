"""Exercise the actual light command method without moving physical devices."""
import ast
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, call

source = Path(__file__).parents[1] / 'custom_components/sbp_gira_x1/light.py'
tree = ast.parse(source.read_text(encoding='utf-8'))
cls = next(n for n in tree.body if isinstance(n, ast.ClassDef))
method = next(n for n in cls.body if isinstance(n, ast.AsyncFunctionDef) and n.name == 'async_turn_on')
ns = {'Any': Any}
exec(compile(ast.Module(body=[method], type_ignores=[]), str(source), 'exec'), ns)

class LightCommandTests(IsolatedAsyncioTestCase):
    def entity(self, on=False, dim=True, writable=True):
        points = {'OnOff': SimpleNamespace(can_write=True), 'Color-Temperature': SimpleNamespace(can_write=True)}
        if dim: points['Brightness'] = SimpleNamespace(can_write=writable)
        return SimpleNamespace(function=SimpleNamespace(point=points.get), is_on=on, write=AsyncMock())

    async def test_dimming_never_sends_switch_on(self):
        for on in (False, True, None):
            for level in (3, 5, 13, 255):
                e = self.entity(on)
                await ns['async_turn_on'](e, brightness=level)
                self.assertEqual(e.write.await_args_list, [call('Brightness', round(level*100/255, 1))])

    async def test_temperature_before_final_brightness(self):
        e = self.entity()
        await ns['async_turn_on'](e, brightness=13, color_temp_kelvin=2701)
        self.assertEqual(e.write.await_args_list, [call('Color-Temperature',2701), call('Brightness',5.1)])

    async def test_zero_only_switches_off(self):
        e = self.entity(True)
        await ns['async_turn_on'](e, brightness=0, color_temp_kelvin=2701)
        e.write.assert_awaited_once_with('OnOff',0)

    async def test_plain_switch_on(self):
        e = self.entity(dim=False)
        await ns['async_turn_on'](e)
        e.write.assert_awaited_once_with('OnOff',1)

    async def test_color_on_does_not_retrigger(self):
        e = self.entity(True)
        await ns['async_turn_on'](e,color_temp_kelvin=2701)
        e.write.assert_awaited_once_with('Color-Temperature',2701)

    async def test_unwritable_does_not_fall_back_to_full_on(self):
        e=self.entity(writable=False)
        with self.assertRaises(ValueError): await ns['async_turn_on'](e,brightness=3)
        e.write.assert_not_awaited()

    async def test_failed_brightness_does_not_switch_on(self):
        e=self.entity()
        e.write.side_effect=RuntimeError('write failed')
        with self.assertRaises(RuntimeError): await ns['async_turn_on'](e,brightness=3)
        e.write.assert_awaited_once_with('Brightness',1.2)
