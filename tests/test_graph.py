import uuid

import pytest

from khive._errors import ItemNotFoundError
from khive.protocols.edge import Edge
from khive.protocols.graph import Graph, NodeEdgeMapping
from khive.protocols.node import Node


def test_add_node_uuid():
    """Test that NodeEdgeMapping.add_node accepts UUID."""
    mapping = NodeEdgeMapping()

    # Create a UUID
    node_id = uuid.uuid4()

    # Add the UUID directly
    mapping.add_node(node_id)

    # Verify it's in the mapping
    assert node_id in mapping
    assert node_id in mapping.mapping
    assert "in" in mapping.mapping[node_id]
    assert "out" in mapping.mapping[node_id]


def test_graph_with_node_uuid():
    """Test that Graph works with NodeEdgeMapping using UUIDs."""
    graph = Graph()

    # Add a node to the graph
    node = Node()
    graph.add_node(node)

    # Add a UUID directly to the mapping
    new_id = uuid.uuid4()
    graph.node_edge_mapping.add_node(new_id)

    # Verify it's in the mapping
    assert new_id in graph.node_edge_mapping

    # But it's not in the graph's nodes
    with pytest.raises(ItemNotFoundError):
        graph.find_node_edge(new_id)


def test_find_node_edge_with_node_object():
    """Test that find_node_edge works with Node objects."""
    graph = Graph()
    node = Node()
    graph.add_node(node)

    # Should work with a Node object
    graph.find_node_edge(node)

    # Should fail with a Node that's not in the graph
    with pytest.raises(ItemNotFoundError):
        graph.find_node_edge(Node())
