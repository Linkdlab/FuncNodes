"""
Test examples
"""
import unittest

from funcnodes.node import (
    Node,
)

from funcnodes.nodespace import NodeSpace, NodeSpaceSerializationInterface


class TestExamples(unittest.IsolatedAsyncioTestCase):
    async def test_linear_add(self):
        from funcnodes.nodes.numpy_nodes.ufunc import AddNode

        N = 6

        oadd: Node = AddNode(
            {
                "id": "AN" + str(0),
                "io": {"x1": {"default_value": 1}, "x2": {"default_value": 0}},
            }
        ).initialize()

        await oadd.await_done()
        res1 = oadd.io("out").value

        for i in range(1, N):
            add = AddNode(
                {
                    "id": "AN" + str(i),
                    "io": {"x2": {"default_value": 1}},
                }
            ).initialize()

            oadd.io("out").c(add.io("x1"))
            oadd = add
            await oadd.await_done()

        res2 = oadd.get_data("out")

        assert res1 == 1
        assert res2 == N
        assert res1 + N - 1 == res2

    async def test_3np1(self):
        # import logging
        import numpy as np

        # logging.basicConfig(level=logging.DEBUG)
        N = 27  # 19
        n = N
        steps = []
        while n != 1:
            steps.append(n)
            if n % 2 == 0:
                n = n / 2
            else:
                n = 3 * n + 1
        steps.append(1)
        steps = np.array(steps)
        ns = NodeSpace()

        data: NodeSpaceSerializationInterface = {
            "nodes": [
                {
                    "id": "breakcon",
                    "io": {"ip": {"x2": {"default_value": 1}}},
                    "nid": "np.equal",
                },
                {"id": "ifbreak", "nid": "if"},
                {
                    "id": "modul",
                    "io": {"ip": {"x2": {"default_value": 2}}},
                    "nid": "np.mod",
                },
                {"id": "ifeq", "nid": "if"},
                {
                    "id": "div",
                    "io": {"ip": {"x2": {"default_value": 2}}},
                    "nid": "np.divide",
                },
                {
                    "id": "mult",
                    "io": {"ip": {"x2": {"default_value": 3}}},
                    "nid": "np.multiply",
                },
                {
                    "id": "add",
                    "io": {"ip": {"x2": {"default_value": 1}}},
                    "nid": "np.add",
                },
                {
                    "id": "mergeip",
                    "io": {
                        "ip": {
                            "i1": {"required": False},
                            "i2": {"required": False},
                            "i3": {"required": False},
                        }
                    },
                    "nid": "manyineachout",
                },
                {"id": "collect", "nid": "collectornode"},
                {
                    "id": "ip",
                    "io": {"ip": {"input": {"default_value": N}}},
                    "nid": "intip",
                },
            ],
            "edges": [
                ["ip", "output", "mergeip", "i3"],
                ["ifbreak", "else_", "ifeq", "input"],
                ["ifeq", "else_", "div", "x1"],
                ["add", "out", "mergeip", "i2"],
                ["ifeq", "condition", "modul", "out"],
                ["ifeq", "then", "mult", "x1"],
                ["ifbreak", "condition", "breakcon", "out"],
                ["mergeip", "out", "ifbreak", "input"],
                ["div", "out", "mergeip", "i1"],
                ["mult", "out", "add", "x1"],
                ["mergeip", "out", "collect", "input"],
                ["breakcon", "x1", "mergeip", "out"],
                ["modul", "x1", "mergeip", "out"],
            ],
            "prop": {},
        }

        ns.deserialize(data)
        try:
            await ns.await_done(timeout=20)
        except Exception as exc:
            out = np.array(ns.get_node("collect").output.value)
            print("\n" * 4, out, "\n" * 4)
            raise exc
        out = np.array(ns.get_node("collect").output.value)
        self.assertEqual(out.tolist(), steps.tolist())


# 3n+1
