import os


from funcnodes import WSWorker, FuncNodesExternalWorker, instance_nodefunction
from PIL import Image
import numpy as np
import time
import asyncio

from typing import Optional, List

from funcnodes.io import NoValue
import cv2
import threading
import signal
import sys
from multiprocessing import Process, Queue

os.environ["OPENCV_LOG_LEVEL"] = "FATAL"

if sys.platform.startswith("win"):

    def VideoCapture(index):
        print("Using cv2.CAP_DSHOW", index)
        return cv2.VideoCapture(index, cv2.CAP_DSHOW)

else:

    def VideoCapture(index):
        return cv2.VideoCapture(index)


def get_available_cameras(queue, max_index=10) -> List[int]:
    available_devices = []
    for i in range(max_index):
        cap = VideoCapture(i)
        if cap.isOpened():
            available_devices.append(i)
            cap.release()
    queue.put(available_devices)
    return available_devices


AVAILABLE_DEVICES = []
LAST_DEVICE_UPDATE = 0
DEVICE_UPDATE_TIME = 20


class WebcamWorker(FuncNodesExternalWorker):
    NODECLASSID = "webcam"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._image: np.ndarray = None
        self._last_frame: np.ndarray = None
        self._image_lock = threading.Lock()
        self._stop_thread: threading.Event = threading.Event()
        self._capture_thread: Optional[threading.Thread] = None
        self._capturing = False
        self._last_device_update = 0

        self.original_sigint_handler = signal.getsignal(signal.SIGINT)
        signal.signal(
            signal.SIGINT, self.signal_handler
        )  # until everythin shuts down automatically

    def signal_handler(self, sig, frame):
        print("Signal handler called with signal", sig, "calling", self.stop)
        self.stop()
        signal.signal(signal.SIGINT, self.original_sigint_handler)

        raise KeyboardInterrupt

    @instance_nodefunction()
    def stop_capture(self):
        """Stops the webcam capture thread."""
        print("Stopping capture1")
        if self._stop_thread is not None or self._capture_thread is not None:
            print("Stopping capture2")
            if self._stop_thread:
                self._stop_thread.set()
            self._capturing = False
            print("Waiting for capture thread to stop")
            if self._capture_thread is not None and self._capture_thread.is_alive():
                self._capture_thread.join()
            print("Capture thread stopped")

        for node in self.start_capture.nodes(self):
            node.inputs["device"].default_value = NoValue
        self.start_capture.nodeclass(self).input_device.default_value = NoValue

    @instance_nodefunction()
    async def start_capture(self, device: int = -1):
        """Starts the webcam capture thread."""
        print("Starting capture", device)
        if device < 0:
            devicelist = await self.list_available_cameras()
            if not devicelist:
                devicelist = []
            print(f"Available devices: {devicelist}")
            if len(devicelist) == 0:
                raise ValueError("No available devices.")
            device = devicelist[0]
        if device < 0:
            raise ValueError("No device specified.")
        self._device = device
        self._stop_thread.clear()
        self._capturing = True

        self._capture_thread = threading.Thread(target=self._capture_loop)
        self._capture_thread.start()

    async def update_available_cameras(self):
        available_devices = await self.list_available_cameras()
        if available_devices is None:
            return
        available_devices = AVAILABLE_DEVICES
        if len(available_devices) > 0:
            available_devices = available_devices
        for node in self.start_capture.nodes(self):
            node.inputs["device"].update_value_options(options=available_devices)
        self.start_capture.nodeclass(self).input_device.update_value_options(
            options=available_devices
        )

    async def list_available_cameras(self, max_index=10):
        """
        List the indices of all available video capture devices.

        Parameters:
        - max_index: Maximum device index to check. Increase if you have more devices.

        Returns:
        - List of integers, where each integer is an index of an available device.
        """
        global AVAILABLE_DEVICES, LAST_DEVICE_UPDATE
        if time.time() - LAST_DEVICE_UPDATE > DEVICE_UPDATE_TIME:
            LAST_DEVICE_UPDATE = time.time()
            print(f"Checking for available devices up to index {max_index}.")
            self.stop_capture()
            queue = Queue()
            proc = Process(target=get_available_cameras, args=(queue, max_index))
            proc.start()
            while proc.is_alive():
                await asyncio.sleep(0.1)
            proc.join()
            # check if the process ended with an error
            res = None
            if proc.exitcode != 0:
                return
            res = queue.get()

            AVAILABLE_DEVICES = res
        return AVAILABLE_DEVICES

    def _capture_loop(self):
        """Continuously grabs images from the webcam."""
        cap = VideoCapture(self._device)  # Open the default camera
        while not self._stop_thread.is_set() and self._capturing:
            print(".")
            if not cap.isOpened():
                time.sleep(0.1)
                cap = VideoCapture(self._device)
            if not cap.isOpened():
                time.sleep(0.1)
                continue
            ret, frame = cap.read()
            if ret:
                # Convert the color space from BGR to RGB
                # frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                # Convert the frame to PIL image
                with self._image_lock:
                    self._last_frame = frame
            time.sleep(0.02)
        if cap.isOpened():
            cap.release()

    async def loop(self):
        if (
            self._capture_thread is not None
            and self._capture_thread.is_alive()
            and self._capturing
        ):
            await self.update_image()
        else:
            if time.time() - self._last_device_update > DEVICE_UPDATE_TIME:
                await self.update_available_cameras()
                self._last_device_update = time.time()

    @instance_nodefunction(
        default_render_options={"data": {"src": "out", "type": "image"}}
    )
    def get_image(self) -> bytes:
        """gets the generated image."""
        with self._image_lock:
            self._image = self._last_frame
        if self._image is None:
            return NoValue
        retval, buffer_cv2 = cv2.imencode(
            ".jpeg",
            self._image,
            [int(cv2.IMWRITE_JPEG_QUALITY), 50],
        )
        return buffer_cv2.tobytes()

    @get_image.triggers
    async def update_image(self) -> Image.Image:
        """Generates an random image."""
        ...

    async def stop(self):
        self.stop_capture()
        return await super().stop()


def main():
    worker = WSWorker(data_path="data", host="127.0.0.1", port=9382)
    worker.add_local_worker(WebcamWorker, "myworker")
    worker.add_local_worker(WebcamWorker, "myworker2")
    worker.add_shelf_by_module(module="funcnodes.basic_nodes.math")
    worker.add_shelf_by_module(module="funcnodes.basic_nodes.logic")
    worker.add_shelf_by_module(module="funcnodes.basic_nodes.frontend")
    worker.run_forever()


print("PROCESS", __name__)
if __name__ == "__main__":
    main()
