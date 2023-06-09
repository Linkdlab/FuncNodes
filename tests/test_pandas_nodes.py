"""
This file contains the tests the pandas nodes
"""
import unittest
import logging
import numpy as np

logging.basicConfig(level=logging.INFO)


class TestPandasNodes(unittest.IsolatedAsyncioTestCase):
    async def test_gen_dfnode(self):
        from funcnodes.nodes.pandas_nodes.generate import BuildDataFrameNode

        node: BuildDataFrameNode = BuildDataFrameNode().initialize()
        self.assertEqual(len(node.get_inputs()), 1)
        await node.await_done()

        self.assertEqual(len(node.get_inputs()), 3)

        node.number.value = 2
        node.trigger()
        await node.await_done()

        self.assertEqual(len(node.get_inputs()), 5)

        node.number.value = 3
        node.trigger()
        await node.await_done()

        self.assertEqual(len(node.get_inputs()), 7)

        node.number.value = 1
        node.trigger()
        await node.await_done()

        self.assertEqual(len(node.get_inputs()), 3)

        node.number.value = 0
        node.trigger()
        await node.await_done()

        self.assertEqual(len(node.get_inputs()), 1)

        node.number.value = -1
        node.trigger()
        await node.await_done()

        self.assertEqual(len(node.get_inputs()), 1)

        node.number.value = 3
        node.trigger()
        await node.await_done()

        node.col1.value = "a"
        node.col2.value = "b"
        node.col3.value = "c"

        node.data1.value = [1, 2, 3]
        node.data2.value = [4, 5, 6]
        node.data3.value = [7, 8, 9, 10]

        node.trigger()
        await node.await_done()

        df = node.dataframe.value

        self.assertEqual(df.shape, (4, 3))

        # equal with nan  not working
        # self.assertEqual(df["a"].tolist(), [1., 2., 3., np.nan])
        with self.assertRaises(AssertionError):
            np.testing.assert_equal(df["a"].values, [1.0, 2.0, 3.0])

        np.testing.assert_equal(df["a"].values, [1.0, 2.0, 3.0, np.nan])
        np.testing.assert_equal(df["b"].values, [4.0, 5.0, 6.0, np.nan])
        np.testing.assert_equal(df["c"].values, [7.0, 8.0, 9.0, 10.0])

        node.number.value = 2
        node.trigger()
        await node.await_done()

        df = node.dataframe.value
        print(df)

        self.assertEqual(df.shape, (3, 2))
        np.testing.assert_equal(df["a"].values, [1.0, 2.0, 3.0])
        np.testing.assert_equal(df["b"].values, [4.0, 5.0, 6.0])

        node.number.value = 1
        node.trigger()
        await node.await_done()

        from funcnodes.nodes.numpy_nodes.ranges import LinspaceNode

        linspacenode = LinspaceNode().initialize()

        linspacenode.start.value = 0
        linspacenode.stop.value = 10
        linspacenode.num.value = 10

        linspacenode.trigger()
        await linspacenode.await_done()

        linspacenode.out.c(node.data1)
        node.number.value = 2
        await node.await_done()

        df = node.dataframe.value

        self.assertEqual(df.shape, (10, 2))
        self.assertEqual(df.columns.tolist(), ["a", 0])
        np.testing.assert_equal(df["a"].values, np.linspace(0, 10, 10))
        np.testing.assert_equal(df[0].values.astype(float), np.zeros((10,)) * np.nan)

        linspacenode2 = LinspaceNode().initialize()
        linspacenode2.start.value = 0
        linspacenode2.stop.value = 1
        linspacenode2.num.value = 10

        node.data2.c(linspacenode2.out)

        node.trigger()
        await node.await_done()

        df = node.dataframe.value

        self.assertEqual(df.shape, (10, 2))
        self.assertEqual(df.columns.tolist(), ["a", 0])
        np.testing.assert_equal(df["a"].values, np.linspace(0, 10, 10))
        np.testing.assert_equal(df[0].values, np.linspace(0, 1, 10))

        node.number.value = 1

        node.trigger()
        await node.await_done()

        self.assertEqual(linspacenode2.out.get_other_io(), [])
