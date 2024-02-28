from funcnodes import WSWorker, FuncNodesExternalWorker, instance_nodefunction
from PIL import Image
import numpy as np
from funcnodes.utils import JSONEncoder
import time
import asyncio


class MyWorker(FuncNodesExternalWorker):
    NODECLASSID = "myworker"

    async def loop(self):
        asyncio.get_event_loop().create_task(self.generate_image())

    @instance_nodefunction(
        default_render_options={"data": {"src": "out", "type": "image"}}
    )
    def get_image(self) -> Image.Image:
        """gets the generated image."""
        if not hasattr(self, "_image"):
            return None
        return self._image

    @get_image.triggers
    async def generate_image(self) -> Image.Image:
        """Generates an random image."""
        img = Image.fromarray(
            np.random.randint(
                0,
                255,
                size=(
                    720,
                    1280,
                ),
                dtype=np.uint8,
            )
        )
        self._image = img


def main():
    worker = WSWorker(data_path="data", host="localhost", port=9382)
    worker.add_local_worker(MyWorker, "myworker")
    worker.add_shelf_by_module(module="funcnodes.basic_nodes.math")
    worker.add_shelf_by_module(module="funcnodes.basic_nodes.logic")
    worker.add_shelf_by_module(module="funcnodes.basic_nodes.frontend")
    worker.run_forever()


if __name__ == "__main__":
    main()
