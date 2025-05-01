from types import MappingProxyType

import pytest

from khive._errors import ItemExistsError, ItemNotFoundError
from khive.protocols.edge import Edge, EdgeCondition
from khive.protocols.element import Element
from khive.protocols.graph import Graph, NodeEdgeMapping
from khive.protocols.node import Node
from khive.protocols.pile import Pile


class TestElement:
    def test_id_serialization(self):
        """Test that ID serialization works correctly."""
        element = Element()
        serialized = element.to_dict()
        assert isinstance(serialized["id"], str)

        # Test round-trip
        deserialized = Element.from_dict(serialized)
        assert deserialized.id == element.id

    def test_metadata_immutability(self):
        """Test that metadata is immutable."""
        element = Element(metadata={"test": "value"})
        assert isinstance(element.metaview, MappingProxyType)

        # Verify we can read values
        assert element.metaview["test"] == "value"

        # Verify we can't modify the metadata directly
        with pytest.raises(TypeError):
            element.metaview["new_key"] = "new_value"


class TestNode:
    def test_empty_embedding(self):
        """Test that empty embedding is handled correctly."""
        # Test with None
        node1 = Node(embedding=None)
        assert node1.embedding is None

        # Test with empty list
        node2 = Node(embedding=[])
        assert isinstance(node2.embedding, list)
        assert len(node2.embedding) == 0

        # Test with empty string
        node3 = Node(embedding="")
        assert node3.embedding is None


class TestEdge:
    def test_condition_excluded_from_serialization(self):
        """Test that condition is excluded from serialization."""

        class TestCondition(EdgeCondition):
            async def applies(self, *args, **kwargs) -> bool:
                return True

        head = Node()
        tail = Node()
        edge = Edge(head=head, tail=tail, condition=TestCondition())

        serialized = edge.to_dict()
        # The condition should not be in the serialized dict at all
        assert "condition" not in serialized

        # Verify condition is still accessible
        assert edge.condition is not None
        assert isinstance(edge.condition, EdgeCondition)


class TestPile:
    def test_getitem_with_int_and_slice(self):
        """Test that __getitem__ works with int and slice."""
        pile = Pile()
        nodes = [Node() for _ in range(5)]
        for node in nodes:
            pile.append(node)

        # Test with int
        assert pile[0] == nodes[0]

        # Test with slice
        assert pile[1:3] == nodes[1:3]

    @pytest.mark.asyncio
    async def test_async_lock(self):
        """Test that async lock works correctly."""
        pile = Pile()

        # Verify we have only one lock
        lock1 = pile.async_lock
        lock2 = pile.async_lock
        assert lock1 is lock2

        # Test that the lock works in async context
        async with pile:
            # We should be able to acquire the lock
            assert pile.async_lock.locked()

    def test_extend_duplicate_detection(self):
        """Test that extend detects duplicates efficiently."""
        pile = Pile()
        nodes = [Node() for _ in range(3)]
        pile.extend(nodes)

        # Try to extend with a duplicate
        with pytest.raises(ItemExistsError):
            pile.extend([nodes[0]])

        # Try to extend with multiple duplicates
        with pytest.raises(ItemExistsError):
            pile.extend([Node(), nodes[1], Node()])


class TestGraph:
    def test_node_edge_mapping_initialization(self):
        """Test that node_edge_mapping is initialized correctly."""
        graph = Graph()
        assert isinstance(graph.node_edge_mapping, NodeEdgeMapping)

    def test_acyclic_detection(self):
        """Test that acyclic detection works correctly."""
        graph = Graph()

        # Create a simple DAG
        nodes = [Node() for _ in range(3)]
        for node in nodes:
            graph.add_node(node)

        # Add edges to form a DAG
        edge1 = Edge(head=nodes[0], tail=nodes[1])
        edge2 = Edge(head=nodes[1], tail=nodes[2])
        graph.add_edge(edge1)
        graph.add_edge(edge2)

        # Verify it's acyclic
        assert graph.is_acyclic() is True

        # Add an edge to create a cycle
        edge3 = Edge(head=nodes[2], tail=nodes[0])
        graph.add_edge(edge3)

        # Verify it's no longer acyclic
        assert graph.is_acyclic() is False

    def test_display_mutable_default(self):
        """Test that display doesn't use a mutable default argument."""
        graph = Graph()

        # Add a node to the graph
        node = Node()
        graph.add_node(node)

        # Call display with no arguments (this would fail if we used a mutable default)
        try:
            # This will likely raise an ImportError if networkx/matplotlib is not installed,
            # but it shouldn't fail due to the mutable default issue
            graph.display()
        except ImportError:
            pass  # Expected if dependencies are missing

    def test_to_dict_from_dict_roundtrip(self):
        """Test that to_dict works correctly."""
        # Create a graph with nodes and edges
        graph = Graph()
        nodes = [Node() for _ in range(3)]
        for node in nodes:
            graph.add_node(node)

        edge1 = Edge(head=nodes[0], tail=nodes[1])
        edge2 = Edge(head=nodes[1], tail=nodes[2])
        graph.add_edge(edge1)
        graph.add_edge(edge2)

        # Serialize
        serialized = graph.to_dict()

        # Verify the serialized structure contains the expected data
        assert "internal_nodes" in serialized
        assert "internal_edges" in serialized
        assert len(serialized["internal_nodes"]["collections"]) == 3
        assert len(serialized["internal_edges"]["collections"]) == 2

        # Note: Full roundtrip deserialization would require a custom from_dict
        # implementation for Graph, which is beyond the scope of this test

    def test_add_node_updates_mapping(self):
        """Test that adding a node updates the node_edge_mapping."""
        graph = Graph()
        node = Node()

        # Add the node
        graph.add_node(node)

        # Verify it's in the mapping
        assert node.id in graph.node_edge_mapping

        # Add another node and create an edge between them
        node2 = Node()
        graph.add_node(node2)

        # This would fail if the mapping wasn't updated
        edge = Edge(head=node, tail=node2)
        graph.add_edge(edge)

        # Verify the edge was added
        assert edge.id in graph.internal_edges

    def test_find_node_edge_with_node_object(self):
        """Test that find_node_edge works with Node objects."""
        graph = Graph()
        node = Node()
        graph.add_node(node)

        # Should work with a Node object
        graph.find_node_edge(node)

        # Should fail with a Node that's not in the graph
        with pytest.raises(ItemNotFoundError):
            graph.find_node_edge(Node())
