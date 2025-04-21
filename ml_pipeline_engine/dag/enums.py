from enum import StrEnum


class NodeField(StrEnum):
    is_switch = 'is_switch'
    is_oneof_head = 'is_oneof'
    is_oneof_child = 'is_oneof_child'
    oneof_nodes = 'oneof_nodes'
    start_node = 'start_node'
    max_iterations = 'max_iterations'
    additional_data = 'additional_data'


class EdgeField(StrEnum):
    kwarg_name = 'kwarg_name'
    is_switch = 'is_switch'
    case_branch = 'case_branch'
