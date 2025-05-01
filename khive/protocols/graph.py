from collections import deque
from typing import Any, Literal
from uuid import UUID

from pydantic import Field, model_validator
from typing_extensions import Self

from khive._errors import ItemExistsError, ItemNotFoundError

_HAS_NETWORKX = True
try:
    import networkx as nx  # type: ignore
except ImportError:
    _HAS_NETWORKX = False

_HAS_MATPLOTLIB = True
try:
    import matplotlib.pyplot as plt  # type: ignore
except ImportError:
    _HAS_MATPLOTLIB = False


from .edge import Edge
from .element import Element
from .node import Node
from .pile import Pile

__all__ = ("Graph",)


class NodeEdgeMapping:

    def __init__(self):
        self.mapping = {}

    def __contains__(self, key: Any) -> bool:
        """Check if a node ID is in the mapping.

        Args:
            key: Either a UUID or a Node object

        Returns:
            bool: True if the node is in the mapping
        """
        if hasattr(key, "id"):  # Handle Node objects
            return key.id in self.mapping
        return key in self.mapping

    def add_node(self, node: Node):
        self.mapping[node.id] = {"in": {}, "out": {}}

    def add_edge(self, edge: Edge):
        self.mapping[edge.head]["out"][edge.id] = edge.tail
        self.mapping[edge.tail]["in"][edge.id] = edge.head

    def remove_node(self, node: Node | UUID) -> list[UUID]:
        """remove the node edge mapping and return the list of edge to remove in the graph"""
        _id = node.id if isinstance(node, Node) else node
        if _id not in self.mapping:
            raise ItemNotFoundError(f"Node {node} not found in the graph nodes.")

        edges_to_remove = []
        in_edges: dict = self.mapping[_id]["in"]
        for edge_id, node_id in in_edges.items():
            self.mapping[node_id]["out"].pop(edge_id)
            edges_to_remove.append(edge_id)

        out_edges: dict = self.mapping[_id]["out"]
        for edge_id, node_id in out_edges.items():
            self.mapping[node_id]["in"].pop(edge_id)
            edges_to_remove.append(edge_id)

        self.mapping.pop(_id)
        return edges_to_remove

    def remove_edge(self, edge: Edge):
        """remove the edge from the mapping"""
        self.mapping[edge.head]["out"].pop(edge.id)
        self.mapping[edge.tail]["in"].pop(edge.id)

    def find_node_edge(
        self,
        node: Node | UUID,
        /,
        direction: Literal["both", "in", "out"] = "both",
    ) -> list[UUID]:
        """Find edges associated with a node by direction (in, out, or both). Return a list of edge IDs."""
        if direction not in {"both", "in", "out"}:
            raise ValueError("The direction should be 'both', 'in', or 'out'.")

        # Convert Node to UUID if needed
        _id = node.id if hasattr(node, "id") else node

        if _id not in self.mapping:
            raise ItemNotFoundError(f"Node {node} not found in the graph nodes.")

        found_edge_ids = []
        if direction in {"both", "in"}:
            for edge_id in self.mapping[_id]["in"]:
                found_edge_ids.append(edge_id)

        if direction in {"both", "out"}:
            for edge_id in self.mapping[_id]["out"]:
                found_edge_ids.append(edge_id)

        return found_edge_ids

    def find_head(self) -> list[UUID]:
        """return a list of head node ids"""
        result = []
        for node_id in self.mapping.keys():
            if self.mapping[node_id]["in"] == {}:
                result.append(node_id)
        return result


class Graph(Element):

    internal_nodes: Pile[Node] = Field(default_factory=Pile)
    internal_edges: Pile[Edge] = Field(default_factory=Pile)
    node_edge_mapping: NodeEdgeMapping = Field(default_factory=NodeEdgeMapping)

    @model_validator(mode="after")
    def _validate_node_mapping(self) -> Self:
        self.node_edge_mapping = NodeEdgeMapping()
        if self.internal_nodes:
            for node in self.internal_nodes:
                if node.id not in self.node_edge_mapping.mapping:
                    self.node_edge_mapping.add_node(node)

        if self.internal_edges:
            for edge in self.internal_edges:
                self.node_edge_mapping.add_edge(edge)
        return self

    def add_node(self, node: Node) -> None:
        """Add a node to the graph."""
        if not isinstance(node, Node):
            raise TypeError(
                "Failed to add node: Invalid node type. Expected Node instance."
            )
        try:
            self.internal_nodes.append(node)
            self.node_edge_mapping.add_node(
                node
            )  # Update the mapping after successful append
        except ItemExistsError:
            raise ItemExistsError(
                f"Failed to add node: Node with ID {node.id} already exists. If you need to update the node, use `graph.internal_nodes.update()` instead."
            )

    def add_edge(self, edge: Edge, /) -> None:
        """Add an edge to the graph, linking two existing nodes."""

        if not isinstance(edge, Edge):
            raise TypeError(
                "Failed to add edge: Invalid edge type. Expected Edge instance."
            )

        not_found = []
        if edge.head not in self.internal_nodes:
            not_found.append(edge.head)
        if edge.tail not in self.internal_nodes:
            not_found.append(edge.tail)

        if not_found:
            raise ItemNotFoundError(
                f"Failed to add edge: Node(s) {', '.join(map(str, not_found))} not found in the graph."
            )
        try:
            self.internal_edges.append(edge)
            self.node_edge_mapping.add_edge(edge)
        except ItemExistsError:
            raise ItemExistsError(
                f"Failed to add edge: Edge with ID {edge.id} already exists. If you need to update the edge, use `graph.internal_edges.update()` instead."
            )

    def pop_node(self, node: Node | UUID, /) -> Node:
        """Remove a node from the graph, and all connected edges from the graph."""
        if node not in self.internal_nodes:
            raise ItemNotFoundError(
                f"Node {str(node.id)} not found in the graph nodes."
            )

        edges_to_remove = self.node_edge_mapping.remove_node(node)
        for edge_id in edges_to_remove:
            self.internal_edges.pop(edge_id)
        return self.internal_nodes.pop(node)

    def pop_edge(self, edge: Edge | str, /) -> Edge:
        """
        Remove an edge from the graph.
        """
        if edge not in self.internal_edges:
            raise ItemNotFoundError(
                f"Edge {str(edge.id)} not found in the graph edges."
            )

        edge = self.internal_edges[edge]
        self.node_edge_mapping.remove_edge(edge)
        return self.internal_edges.pop(edge)

    def find_node_edge(
        self,
        node: Any,
        /,
        direction: Literal["both", "in", "out"] = "both",
    ) -> list[Edge]:
        """Find edges associated with a node by direction (in, out, or both)."""

        found_edge_ids = self.node_edge_mapping.find_node_edge(node, direction)
        return [self.internal_edges[edge_id] for edge_id in found_edge_ids]

    def get_heads(self) -> list[Node]:
        """Return nodes with no incoming edges (head nodes)."""
        head_ids = self.node_edge_mapping.find_head()
        return [self.internal_nodes[head_id] for head_id in head_ids]

    def get_predecessors(self, node: Node, /) -> Pile[Node]:
        """Return all nodes that have outbound edges to the given node."""
        edges = self.find_node_edge(node, direction="in")
        result = []
        for edge in edges:
            result.append(self.internal_nodes[edge.head])
        return result

    def get_successors(self, node: Node, /) -> Pile[Node]:
        """Return all nodes that have inbound edges to the given node."""
        edges = self.find_node_edge(node, direction="out")
        result = []
        for edge in edges:
            result.append(self.internal_nodes[edge.tail])
        return result

    def to_networkx(self, **kwargs) -> Any:
        """Convert the graph to a NetworkX graph object."""
        if _HAS_NETWORKX is False:
            raise ImportError(
                "Package `networkx` is required to convert the graph to a NetworkX object. Please install it via `pip install networkx` to use this feature."
            )

        from networkx import DiGraph  # type: ignore

        g = DiGraph(**kwargs)
        for node in self.internal_nodes:
            node_info = node.to_dict()
            node_info.pop("id")
            g.add_node(str(node.id), **node_info)

        for _edge in self.internal_edges:
            edge_info = _edge.to_dict()
            edge_info.pop("id")
            source_node_id = edge_info.pop("head")
            target_node_id = edge_info.pop("tail")
            g.add_edge(str(source_node_id), str(target_node_id), **edge_info)

        return g

    def display(
        self,
        node_label="lion_class",
        edge_label="label",
        draw_kwargs=None,
        **kwargs,
    ):
        """Display the graph using NetworkX and Matplotlib."""

        if _HAS_NETWORKX is False:
            raise ImportError(
                "Package `networkx` is required to convert the graph to a NetworkX object. Please install it via `pip install networkx` to use this feature."
            )
        if _HAS_MATPLOTLIB is False:
            raise ImportError(
                "Package `matplotlib` is required to display the graph. Please install it via `pip install matplotlib` to use this feature."
            )

        import matplotlib.pyplot as plt  # type: ignore
        import networkx as nx  # type: ignore

        g = self.to_networkx(**kwargs)
        pos = nx.spring_layout(g)
        if draw_kwargs is None:
            draw_kwargs = {}
        nx.draw(
            g,
            pos,
            labels=nx.get_node_attributes(g, node_label),
            **draw_kwargs,
        )

        edge_labels = nx.get_edge_attributes(g, edge_label)
        if edge_labels:
            nx.draw_networkx_edge_labels(g, pos, edge_labels=edge_labels)

        plt.axis("off")
        plt.show()

    def is_acyclic(self) -> bool:
        """Check if the graph is acyclic (contains no cycles)."""
        # Fast path using NetworkX if available
        if _HAS_NETWORKX:
            try:
                nx_graph = self.to_networkx()
                nx.find_cycle(nx_graph, orientation="original")
                return False  # Cycle found
            except nx.exception.NetworkXNoCycle:
                return True  # No cycle found
            except Exception:
                # Fall back to custom implementation if NetworkX fails
                pass

        # Custom DFS-based cycle detection
        node_ids = [node.id for node in self.internal_nodes]
        check_deque = deque(node_ids)

        # 0: unvisited, 1: visiting, 2: visited
        check_dict = {nid: 0 for nid in node_ids}

        def visit(nid):
            if check_dict[nid] == 2:
                return True
            elif check_dict[nid] == 1:
                return False

            check_dict[nid] = 1
            for edge_id in self.node_edge_mapping.mapping[nid]["out"]:
                edge: Edge = self.internal_edges[edge_id]
                if not visit(edge.tail):
                    return False
            check_dict[nid] = 2
            return True

        while check_deque:
            key = check_deque.pop()
            if not visit(key):
                return False
        return True

    def __contains__(self, item: object) -> bool:
        return item in self.internal_nodes or item in self.internal_edges

    def __repr__(self) -> str:
        """Return a string representation of the graph for debugging."""
        node_count = len(self.internal_nodes)
        edge_count = len(self.internal_edges)

        # Show first 3 node IDs
        node_preview = []
        for i, node_id in enumerate(self.internal_nodes.order):
            if i >= 3:
                break
            node_preview.append(str(node_id)[:8] + "...")

        return f"Graph(nodes={node_count}, edges={edge_count}, preview=[{', '.join(node_preview)}])"
