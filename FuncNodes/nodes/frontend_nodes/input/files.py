from typing import Any
from ..rendernode import RenderNode
from ....io import NodeOutput
from ....iotypes import IOType
import io
from js import document, window, Uint8Array
from pyodide import create_proxy, to_js, JsProxy
import asyncio


class FileInputNode(RenderNode):
    node_id = "fileinput"
    output = NodeOutput(type="BytesIO")
    trigger_on_create: bool = False

    async def legacy_get_file(self):
        input = document.createElement("input")
        self.element.element.appendChild(input)
        input.type = "file"
        input.click()

        while len(input.files) == 0:
            await asyncio.sleep(0.1)
        file = list(input.files)[0]
        input.remove()
        return file

    async def get_file(self):
        try:
            fileHandles = await window.showOpenFilePicker()
        except AttributeError as esc:
            return await self.legacy_get_file()
        file = await fileHandles[0].getFile()
        return file

    async def on_trigger(self, *args, **kwargs):
        file = await self.get_file()
        self.input.value = file.name
        data = Uint8Array.new(await file.arrayBuffer())
        self.output.value = io.BytesIO(bytearray(data))
        return True

    def render(self, id: str):
        super().render(id)

        self.input = document.createElement("input")
        self.input.type = "button"
        self.input.value = "Select File"
        file_select_proxy = create_proxy(self.trigger)
        self.input.addEventListener("click", file_select_proxy, False)

        self.element.element.appendChild(self.input)

        # fileHandles = await window.showOpenFilePicker(
        #    Object.fromEntries(to_js(options))
        # )
