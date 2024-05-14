import unittest
import funcnodes as fn


class TestNodeClassMixin(unittest.IsolatedAsyncioTestCase):

    async def test_nodeclassmixin_create_wo_id(self):
        with self.assertRaises(ValueError):

            class MyNodeClass(fn.NodeClassMixin):
                pass

    async def test_nodeclassmixin_create(self):
        class MyNodeClass(fn.NodeClassMixin):
            NODECLASSID = "test"
            pass

        ins = MyNodeClass()

        ins.uuid = "test"

    async def test_nodes(self):
        class MyNodeClass(fn.NodeClassMixin):
            NODECLASSID = "test"

            @fn.instance_nodefunction()
            def test(self, a: int) -> int:
                return 1

        ins = MyNodeClass()
        ins.uuid = "test"

        self.assertEqual(len(ins.get_all_nodeclasses()), 1)
        self.assertEqual(len(ins.get_all_nodes()), 0)

        testnode = ins.get_nodeclass("test")()
        self.assertIsInstance(testnode, fn.Node)

        self.assertEqual(len(ins.get_all_nodes()), 1)

        testnode.inputs["a"].value = 1
        await testnode
        self.assertEqual(testnode.outputs["out"].value, 1)

    async def test_remotetrigger(self):
        class MyNodeClass(fn.NodeClassMixin):
            NODECLASSID = "test_remotetrigger"

            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self.a = 1

            @fn.instance_nodefunction()
            def test(self, a=1) -> int:
                return self.a + a

            @test.triggers
            def remotetrigger(self):
                pass

        ins = MyNodeClass()
        ins.uuid = "test"

        self.assertEqual(len(ins.get_all_nodeclasses()), 1)
        self.assertEqual(len(ins.get_all_nodes()), 0)

        testnode1 = ins.get_nodeclass("test")()
        self.assertIsInstance(testnode1, fn.Node)
        testnode2 = ins.get_nodeclass("test")()

        self.assertEqual(len(ins.get_all_nodes()), 2)
        testnode1.inputs["a"].set_value(1, does_trigger=False)
        testnode2.inputs["a"].set_value(2, does_trigger=False)
        await testnode1.await_until_complete()
        await testnode2.await_until_complete()
        self.assertEqual(testnode1.outputs["out"].value, fn.NoValue)
        self.assertEqual(testnode2.outputs["out"].value, fn.NoValue)
        ins.remotetrigger()
        await testnode1.await_until_complete()
        await testnode2.await_until_complete()
        self.assertEqual(testnode1.outputs["out"].value, 2)
        self.assertEqual(testnode2.outputs["out"].value, 3)
