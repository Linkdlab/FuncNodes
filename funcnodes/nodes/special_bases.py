from __future__ import annotations
from typing import Any, List
from funcnodes import Node
from funcnodes import NodeInput
from funcnodes.io import NodeInput

class VariableInputNode(Node):
    node_id = "VariableInput"
    number = NodeInput(type=int, required=True, default_value=1)
    input_types: List[Any] = [Any]
    input_names: List[str] = ["input"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.variable_inputs: List[NodeInput] = []
        for ip in self.get_inputs():
            ip.deletable = True
        
        if not len(self.input_names) == len(self.input_types):
            raise ValueError("input_names and input_types must be the same length")
        
        for name in self.input_names:
            if len(name) == 0:
                raise ValueError("input_names must not be an empty strings")
            if name[-1].isdigit():
                raise ValueError("input_names must not end with a number")

    async def on_trigger(self):
        num = self.number.value
        if num < 0:
            self.number.value = 0
            num = 0

        while num> len(self.variable_inputs)/len(self.input_names):
            self.create_varinput()
        while num < len(self.variable_inputs)/len(self.input_names):
            self.remove_varinput(self.variable_inputs[-1].id)
        return True

    def create_varinput(self)->List[str]:

        var_ids = [ip.id for ip in self.variable_inputs]
        i=1
        while any([f"{ipname}{i}" in var_ids for ipname in self.input_names]):
            i += 1

        new_inputs = [
            NodeInput(
                deletable=True,
                type=ip_type,
                id=f"{name}{i}",
                required=False,
            )
            for name, ip_type in zip(self.input_names, self.input_types)
            ]

        for new_ip in new_inputs:
            self.add_input(new_ip)
            self.variable_inputs.append(new_ip)
        return [new_ip.id for new_ip in new_inputs]
    
    def remove_varinput(self, id: str) -> bool:
        basename = id.rstrip('0123456789')
        if basename not in self.input_names:
            return False
        
        number = id[len(basename):]

        if not number.isdigit() or len(number) == 0:
            return False

        inputs_to_remove = [f"{n}{number}" for n in self.input_names]
        for ip in self.variable_inputs:
            if ip.id in inputs_to_remove:
                self.remove_input(ip)
                self.variable_inputs.remove(ip)
            
        return True

    def get_input_pairs(self) -> List[List[NodeInput]]:
        ipdict = {ip.id: ip for ip in self.variable_inputs}
        numbers=[]
        for ip in self.variable_inputs:
            basename = ip.id.rstrip('0123456789')
            number = ip.id[len(basename):]
            if number not in numbers:
                numbers.append(number)
        
        pairs = [
            [ipdict.get(f"{name}{number}") for name in self.input_names]
            for number in numbers
                 ]
        return pairs
            

        