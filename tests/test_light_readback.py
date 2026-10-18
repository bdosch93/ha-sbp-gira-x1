"""Actual production methods under test, no HA runtime or real X1 needed."""
import ast
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, Mock

BASE = Path(__file__).parents[1] / "custom_components/sbp_gira_x1"
LIGHT_TYPES = {"de.gira.schema.functions.KNX.Light",
               "de.gira.schema.functions.ColoredLight",
               "de.gira.schema.functions.TunableLight"}

def method(file, name):
    path = BASE / file
    tree = ast.parse(path.read_text(encoding="utf-8"))
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef))
    node = next(n for n in cls.body if isinstance(n, ast.AsyncFunctionDef) and n.name == name)
    ns = {"Any": Any, "LIGHT_FUNCTION_TYPES": LIGHT_TYPES}
    exec(compile(ast.Module(body=[node], type_ignores=[]), str(path), "exec"), ns)
    return ns[name]

write_light = method("coordinator.py", "async_write_light_value")
entity_write = method("entity.py", "write")

class LightReadbackTests(IsolatedAsyncioTestCase):
    def coordinator(self):
        client = SimpleNamespace(async_set_value=AsyncMock(),
            async_get_function_values=AsyncMock(return_value={"light_on": 1}))
        return SimpleNamespace(client=client, data={"config_uid":"v1",
            "functions":{"f_light":"kept"}, "values":{"light_on":0,"room_temp":22.5}},
            async_request_refresh=AsyncMock(), async_update_listeners=Mock())

    async def test_one_put_one_targeted_read_preserves_temperature_and_timer(self):
        c = self.coordinator()
        await write_light(c,"f_light","light_on",1)
        c.client.async_set_value.assert_awaited_once_with("light_on",1)
        c.client.async_get_function_values.assert_awaited_once_with("f_light")
        c.async_request_refresh.assert_not_awaited()
        c.async_update_listeners.assert_called_once_with()
        self.assertEqual(c.data["values"],{"light_on":1,"room_temp":22.5})
        self.assertEqual(c.data["config_uid"],"v1")

    async def test_readback_is_not_optimistic(self):
        c=self.coordinator()
        c.client.async_get_function_values.return_value={"light_on":0}
        await write_light(c,"f_light","light_on",1)
        self.assertEqual(c.data["values"]["light_on"],0)

    async def test_failed_put_never_reads_or_retries(self):
        c=self.coordinator();c.client.async_set_value.side_effect=TimeoutError()
        with self.assertRaises(TimeoutError):await write_light(c,"f_light","light_on",1)
        self.assertEqual(c.client.async_set_value.await_count,1)
        c.client.async_get_function_values.assert_not_awaited()
        c.async_update_listeners.assert_not_called()

    async def test_failed_read_never_retries_write_or_marks_success(self):
        c=self.coordinator();c.client.async_get_function_values.side_effect=TimeoutError()
        with self.assertRaises(TimeoutError):await write_light(c,"f_light","light_on",1)
        self.assertEqual(c.client.async_set_value.await_count,1)
        self.assertEqual(c.data["values"]["light_on"],0)
        c.async_update_listeners.assert_not_called()

    async def test_merge_uses_cache_after_concurrent_update(self):
        c=self.coordinator()
        async def read(_):
            c.data["values"]["room_temp"]=22.2
            return {"light_on":1}
        c.client.async_get_function_values.side_effect=read
        await write_light(c,"f_light","light_on",1)
        self.assertEqual(c.data["values"]["room_temp"],22.2)

    async def test_uninitialized_cache_keeps_existing_full_refresh(self):
        c=self.coordinator();c.data=None
        await write_light(c,"f_light","light_on",1)
        c.async_request_refresh.assert_awaited_once_with()
        c.client.async_get_function_values.assert_not_awaited()

    async def test_light_only_dispatch_other_domains_unchanged(self):
        for type_ in LIGHT_TYPES | {"de.gira.schema.functions.Switch","de.gira.schema.functions.KNX.HeatingCooling"}:
            c=SimpleNamespace(async_write_light_value=AsyncMock(),async_write_value=AsyncMock())
            p=SimpleNamespace(uid="p1",can_write=True)
            e=SimpleNamespace(function=SimpleNamespace(uid="f1",function_type=type_,point=lambda _:p),coordinator=c)
            await entity_write(e,"OnOff",1)
            if type_ in LIGHT_TYPES:
                c.async_write_light_value.assert_awaited_once_with("f1","p1",1)
                c.async_write_value.assert_not_awaited()
            else:
                c.async_write_value.assert_awaited_once_with("p1",1)
                c.async_write_light_value.assert_not_awaited()
