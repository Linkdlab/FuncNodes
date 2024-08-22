import json
from funcnodes import (
    NodeSpace,
    JSONEncoder,
    JSONDecoder,
    NodeSpaceJSON,
    Node,
    NodeJSON,
    NoValue,
    NodeIO,
    NodeIOSerialization,
)


def serialize_nodeio_for_saving(io: NodeIO):
    ser = io.serialize()
    ser.pop("value", None)

    return ser


def serialize_node_for_saving(node: Node):
    ser = NodeJSON(
        name=node.name,
        id=node.uuid,
        node_id=node.node_id,
        node_name=getattr(node, "node_name", node.__class__.__name__),
        io={},
    )

    for iod in list(node.inputs.values()) + list(node.outputs.values()):
        if iod.uuid == "_triggerinput":
            continue
        ioser = dict(serialize_nodeio_for_saving(iod))
        print(iod.uuid, ioser)

        ioser.pop("id", None)

        # checking of the input is defined on a node class leven, if this is the case reduntant information
        # should be removed from the serialized data to reduce the size of the serialized data.
        cls_ser = None
        if iod.uuid in node._class_io_serialized:
            cls_ser = node._class_io_serialized[iod.uuid]

        if cls_ser:
            if "description" in ioser:
                if ioser["description"] == cls_ser.get("description", ""):
                    del ioser["description"]

            if "default" in ioser:
                if ioser["default"] == cls_ser.get("default", NoValue):
                    del ioser["default"]

            if "type" in ioser:
                if ioser["type"] == cls_ser.get("type", "Any"):
                    del ioser["type"]

            if "value_options" in ioser:
                if ioser["value_options"] == cls_ser.get("value_options", {}):
                    del ioser["value_options"]

            if "render_options" in ioser:
                if ioser["render_options"] == cls_ser.get("render_options", {}):
                    del ioser["render_options"]

        ser["io"][iod.uuid] = ioser

    # remove redundant information from the node serialization
    if node.reset_inputs_on_trigger != node.default_reset_inputs_on_trigger:
        ser["reset_inputs_on_trigger"] = node.reset_inputs_on_trigger

    if node.description != node.__class__.description:
        ser["description"] = node.description

    renderopt = node.render_options
    if renderopt:
        ser["render_options"] = renderopt

    return ser


def serialize_nodespace_for_saving(nodespace: NodeSpace):
    node_ret = []
    for node in nodespace.nodes:
        node_ret.append(serialize_node_for_saving(node))
    node_ret = json.loads(json.dumps(node_ret, cls=JSONEncoder), cls=JSONDecoder)

    ret = NodeSpaceJSON(
        nodes=node_ret,
        edges=nodespace.serialize_edges(),
        prop=nodespace._properties,
    )
    return json.loads(json.dumps(ret, cls=JSONEncoder), cls=JSONDecoder)
