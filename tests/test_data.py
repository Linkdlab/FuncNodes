import unittest

import funcnodes as fn


class TestDataEnum(unittest.IsolatedAsyncioTestCase):

    def test_enum(self):
        class TestEnum(fn.DataEnum):
            A = 1
            B = 2
            C = 3

        self.assertEqual(TestEnum.A.value, 1)
        self.assertEqual(TestEnum.interfere("A"), TestEnum.A)
        self.assertEqual(TestEnum.interfere(1), TestEnum.A)
        self.assertEqual(TestEnum.interfere(TestEnum.A), TestEnum.A)
        self.assertEqual(TestEnum.v("A"), 1)
        self.assertEqual(TestEnum.v(1), 1)
        self.assertEqual(TestEnum.v(TestEnum.A), 1)

        with self.assertRaises(ValueError):
            TestEnum.interfere("X")
        with self.assertRaises(ValueError):
            TestEnum.interfere(4)

    async def test_enum_val(self):
        class TestEnum(fn.DataEnum):
            A = 1
            B = 2
            C = 3

        self.assertEqual(TestEnum.A.value, 1)

        @fn.NodeDecorator(node_id="test_enum_val")
        def test_enum_node(a: TestEnum) -> TestEnum:
            a = TestEnum.interfere(a)
            return a

        node = test_enum_node()
        node.inputs["a"].value = "A"
        await node
        out = node.outputs["out"].value
        self.assertEqual(out, TestEnum.A)

        node = test_enum_node()
        node.inputs["a"].value = 1
        await node
        out = node.outputs["out"].value
        self.assertEqual(out, TestEnum.A)

        node = test_enum_node()
        node.inputs["a"].value = TestEnum.A
        await node
        out = node.outputs["out"].value
        self.assertEqual(out, TestEnum.A)

    async def test_enum_use(self):
        class TestEnum(fn.DataEnum):
            A = 1
            B = 2
            C = 3

        self.assertEqual(TestEnum.v("A"), 1)

        @fn.NodeDecorator(node_id="test_enum_use")
        def test_enum_node(a: TestEnum) -> int:
            a = TestEnum.v(a)
            return a + 1

        node = test_enum_node()
        node.inputs["a"].value = "A"
        await node
        out = node.outputs["out"].value
        self.assertEqual(out, 2)

        node = test_enum_node()
        node.inputs["a"].value = 1
        await node
        out = node.outputs["out"].value
        self.assertEqual(out, 2)

        node = test_enum_node()
        node.inputs["a"].value = TestEnum.A
        await node
        out = node.outputs["out"].value
        self.assertEqual(out, 2)

    async def test_enum_default(self):
        class TestEnum(fn.DataEnum):
            A = 1
            B = 2
            C = 3

        self.assertEqual(TestEnum.v("A"), 1)

        @fn.NodeDecorator(node_id="test_enum_use")
        def test_enum_node(a: TestEnum = TestEnum.A) -> int:
            a = TestEnum.v(a)
            return a + 1

        node = test_enum_node()
        await node
        out = node.outputs["out"].value
        self.assertEqual(out, 2)

        node = test_enum_node()
        await node
        out = node.outputs["out"].value
        self.assertEqual(out, 2)

        node = test_enum_node()
        await node
        out = node.outputs["out"].value
        self.assertEqual(out, 2)
