# Copyright (c) 2010 by Cisco Systems, Inc.
"""
Graph data structure.
"""

import sys

class DAG:
	"""Directed Acyclic Graph"""

	def __init__(self):
		self.nodes = {}
		self.root_nodes = {}
		self.leaf_nodes = {}
		self.num_edges = 0

	def Nodes(self):
		"""Return a list of tuples. Each tuple contains
		2 members, the node_datum (what the user thinks is the node
		in the DAG) and the Node object."""
		return self.nodes.items()

	def SetUserData(self, node_datum, user_data):
		node = self.nodes[node_datum]
		node.SetUserData(user_data)

	def UserData(self, node_datum):
		node = self.nodes[node_datum]
		return node.UserData()

	def AddNode(self, node_datum):
		"""Add a new node to the DAG. If the node
		already exists, no action is taken."""
		if self.nodes.has_key(node_datum):
			return

		node = Node()
		self.nodes[node_datum] = node

		self.root_nodes[node_datum] = node
		self.leaf_nodes[node_datum] = node

	def AddEdge(self, node_datum_a, node_datum_b):
		"""(child) node_a --> (parent) node_b"""
		node_a = self.nodes[node_datum_a]
		node_b = self.nodes[node_datum_b]

		node_a.AddOutEdge(node_datum_b)
		node_b.AddInEdge(node_datum_a)

		if self.root_nodes.has_key(node_datum_a):
			del self.root_nodes[node_datum_a]

		if self.leaf_nodes.has_key(node_datum_b):
			del self.leaf_nodes[node_datum_b]

		self.num_edges += 1

	def AttachDAG(self, attach_point_node_datum, other_DAG):
		"""Attach another DAG to this DAG, either
		at the root node (node_datum == None), or
		beneath a node."""

		other_root_node_data = other_DAG.Roots()

		# Copy the nodes over to us.
		nodes = other_DAG.Nodes()
		for (node_datum, node) in nodes:
			self.AddNode(node_datum)
			self.SetUserData(node_datum, node.UserData())

		# Copy the edges over too.
		for (node_datum, node) in nodes:

			for in_node_datum in node.InEdges():
				self.AddEdge(in_node_datum, node_datum)

			for out_node_datum in node.OutEdges():
				self.AddEdge(node_datum, out_node_datum)

		# Connect the other DAG's root nodes under
		# the node specified in the method arguments, if
		# any.
		if attach_point_node_datum:
			for other_root_node_datum in other_root_node_data:
				self.AddEdge(other_root_node_datum, attach_point_node_datum)


	def Inputs(self, node_datum):
		"""Input nodes for a particular node."""
		node = self.nodes[node_datum]
		return node.InEdges()

	def Outputs(self, node_datum):
		"""Output nodes for a particular node."""
		node = self.nodes[node_datum]
		return node.OutEdges()

	def Leafs(self):
		"""List of leaf nodes in the DAG."""
		return self.leaf_nodes.keys()

	def Leaves(self):
		"""List of leaf nodes in the DAG."""
		return self.Leafs()

	def Roots(self):
		"""List of root nodes in the DAG."""
		return self.root_nodes.keys()

	def Print(self):
		"""Print DAG to stdout"""
		self.Write(sys.stdout)

	def Write(self, fh):
		"""Write DAG to stream."""
                self._write(fh, None, 0)

	def _write(self, fh, datum, indent_level):
                indent = indent_level * "   "

                if indent_level == 0:
                    inputs = self.root_nodes.keys()
                else:
                    inputs = self.Inputs(datum)

                # If the sub-graphs of multiple inputs are the same,
                # then group them together.
		inputs.sort()
                groups = {}
                for input in inputs:
                    sub_inputs = self.Inputs(input)
                    sub_inputs.sort()
                    group_key = ' '.join(map(str, sub_inputs))
                    group_values = groups.setdefault(group_key, [])
                    group_values.append(input)

		new_indent_level = indent_level + 1
                group_keys = groups.keys()
                group_keys.sort()

                for group_key in group_keys:
                    group = groups[group_key]

                    if len(group) == 1:
                        # Print the single member of the group
                        input = group[0]
                        print >> fh, indent + str(input)

                        # and it's subgraph
                        self._write(fh, group[0], new_indent_level)
                    else:
                        # Print all but the last member of the group,
                        # with a trailing backslash to denote the set of group members.
                        for input in group[:-1]:
                            print >> fh, indent + str(input), "\\"
                  
                        # Then print the last member of the group
                        input = group[-1]
                        print >> fh, indent + str(input)

                        # and it's subgraph (which is shared for all members of the group)
                        self._write(fh, input, new_indent_level)

                        # Add vertical space between groups
                        print >> fh, ""

	def NumNodes(self):
		"""The number of nodes in the DAG."""
		return len(self.nodes)

	def NumEdges(self):
		"""The number of edges in the DAG."""
		return self.num_edges


class Node:
	"""Maintains list of inputs and output nodes for a node."""
	def __init__(self):
		self.in_edges = []
		self.out_edges = []
		self.user_data = None

	def AddOutEdge(self, datum):
		if not datum in self.out_edges:
			self.out_edges.append(datum)

	def AddInEdge(self, datum):
		if not datum in self.in_edges:
			self.in_edges.append(datum)

	def InEdges(self):
		return self.in_edges

	def OutEdges(self):
		return self.out_edges

	def SetUserData(self, user_data):
		self.user_data = user_data

	def UserData(self):
		return self.user_data
