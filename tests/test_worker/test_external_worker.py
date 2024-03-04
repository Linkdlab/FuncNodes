from unittest import IsolatedAsyncioTestCase
from funcnodes import FuncNodesExternalWorker, RemoteWorker, instance_nodefunction
import asyncio
from unittest.mock import patch, MagicMock
import tempfile


class ExternalWorker_Test(FuncNodesExternalWorker):
    pass


class RaiseErrorLogger:
    def exception(self, e: Exception):
        raise e


class TestWorker(RemoteWorker):
    def __init__(self, *args, **kwargs) -> None:
        self._dir = tempfile.TemporaryDirectory()
        kwargs.setdefault("data_path", self._dir.name)
        super().__init__(*args, **kwargs)

    def __del__(self):
        print("deleting")
        self._dir.cleanup()

    async def sendmessage(self, *args, **kwargs):
        return MagicMock()


class TestExternalWorker(IsolatedAsyncioTestCase):

    def test_external_worker_missing_loop(self):
        class ExternalWorker1(FuncNodesExternalWorker):
            pass

        with self.assertRaises(TypeError):
            ExternalWorker1()

    def test_external_worker_missing_nodeclassid(self):
        with self.assertRaises(ValueError):

            class ExternalWorker2(FuncNodesExternalWorker):

                async def loop(self):
                    pass

    async def test_external_worker_sync_loop(self):

        class ExternalWorker1(FuncNodesExternalWorker):
            NODECLASSID = "testexternalworker"

            def loop(self):
                self.stop()

        worker = ExternalWorker1(workerid="test")
        worker._logger = RaiseErrorLogger()

        with self.assertRaises(TypeError) as e:
            await worker.continuous_run()

        self.assertEqual(
            "object NoneType can't be used in 'await' expression", str(e.exception)
        )

    async def test_external_worker_loop(self):

        class ExternalWorker1(FuncNodesExternalWorker):
            NODECLASSID = "testexternalworker"

            async def loop(self):
                await self.stop()

        worker = ExternalWorker1(workerid="test")
        worker._logger = RaiseErrorLogger()
        await worker.continuous_run()

    async def test_external_worker_nodes(self):

        class ExternalWorker1(FuncNodesExternalWorker):
            NODECLASSID = "testexternalworker"

            async def loop(self):
                self.stop()

            @instance_nodefunction()
            def test(self, a: int) -> int:
                return 1

        retmoteworker = TestWorker()
        retmoteworker.add_local_worker(ExternalWorker1, "test")

        nodeclass = retmoteworker.nodespace.lib.get_node_by_id(
            "testexternalworker.test.test"
        )
        self.assertEqual(nodeclass.node_name, "Test")
        node = retmoteworker.add_node("testexternalworker.test.test", name="TestNode")
        expected_node_ser = {
            "name": "TestNode",
            "id": node.uuid,
            "node_id": "testexternalworker.test.test",
            "node_name": "Test",
            "io": {
                "a": {
                    "name": "a",
                    "type": "int",
                    "id": "a",
                    "is_input": True,
                    "render_options": {},
                    "value_options": {},
                },
                "out": {
                    "name": "out",
                    "type": "int",
                    "id": "out",
                    "is_input": False,
                    "render_options": {},
                    "value_options": {},
                },
            },
        }
        self.assertEqual(node.serialize(), expected_node_ser)
