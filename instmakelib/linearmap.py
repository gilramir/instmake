# Copyright (c) 2010 by Cisco Systems, Inc.
"""
The LinearMap class keeps track of things that occur over
a 1-dimensial space, thus the "linear" in "LinearMap". The LinearMap
helps you visualize the layout of "chunks" of linear space. The 
chunks may overlap, or they may not. Sample applications include
the visualization of headers, segments, and sections within an ELF file
(a file being a 1-dimensional series of bytes), or figuring out which
jobs ran at the same time during a 'make' with -jN > 1 (time is
1-dimensional).
"""

from __future__ import nested_scopes

B_START = "START"
B_END = "END"

class Boundary:
    """The boundaries in the linear-space. They indicate the start
    or end of something. This class is used by LinearMap; the user
    doesn't need to worry about it."""
    def __init__(self, btype, name, id):
        self.type = btype
        self.name = name
        self.id = id

    def Type(self):
        return self.type

    def Name(self):
        return self.name

    def ID(self):
        return self.id

    def __repr__(self):
        return "%s of %s" % (self.type, self.name)

class Chunk:
    """Represent a chunk of the linear-space, i.e., the space between
    2 boundaries in the linear map. Each chunk contains 0 or more 
    item IDs, which identify the items that were Add()ed to the LinearMap.
    The user doesn't create these, but LinearMap can return
    a list of Chunk objects."""
    def __init__(self, start):
        self.start = start
        self.ids = []
        self.end = None

    def SetIDs(self, ids):
        self.ids = ids

    def SetEnd(self, end):
        self.end = end

    def IDs(self):
        return self.ids

    def Start(self):
        return self.start

    def End(self):
        return self.end

    def Length(self):
        return self.end - self.start

    def __repr__(self):
        return "<START:%s END:%s IDs:%s>" % (self.start, self.end, self.ids)

class LinearMap:
    "Produces a map of linear space."

    def __init__(self, start=None, length=None, name=None):
        """Initialize a single 1-dimensional space. Without
        start/length/name parameters, the size of the space is unknown
        and unnamed.  With start/length/name parameters, the linear space
        is given an initial definition. This initial definition does not
        impose limits on the size of the linear space, but nevertheless
        can be useful, especially if your linear space should be bounded,
        and shown so on a printed representation.."""
        self.boundaries = {}
        self.num_chunks = 0
        self.boundary_pairs = []

        self.print_as_hex = 1
        self.print_diff = 1
        self.print_map_key = 1
        self.ids_start_at = 0

        self.comments = {}

        if start != None:
            assert length != None and name != None
        elif length != None:
            assert start != None and name != None
        elif name != None:
            assert start != None and length != None

        # Start with a block?
        if start != None and length != None and name != None:
            self.Add(start, length, name)

    def PrintRawOffsets(self):
        """During the printing of the map, print offsets as decimal
        instead of hexadecimal."""
        self.print_as_hex = 0

    def NoPrintDiff(self):
        """Don't print the size of the linear chunks; i.e., the difference
        between boundaries."""
        self.print_diff = 0

    def NoPrintMapKey(self):
        """Don't print the map key when printing the map."""
        self.print_map_key = 0

    def IDsStartAt(self, num):
        self.ids_start_at = num

    def Add(self, start, length, name, comment=None):
        """Add an item in the linear space. The item has a start
        and a length, and a name. An optional comment can be attached
        to the chunk. The comment appears in the Map Key to better
        identify the named chunk. Returns an ID, which is a number
        unique to the LinearMap that identifies this added item."""

        # The ID is a unique number for each item. The 'name'
        # may not be unique, so LinearMap forces uniqueness
        # by keeping track of an ID.
        id = self.num_chunks + self.ids_start_at

        if comment:
            self.comments[id] = comment

        boundary1 = Boundary(B_START, name, id)
        records = self.boundaries.setdefault(start, [])
        records.append(boundary1)

        boundary2 = Boundary(B_END, name, id)
        end = start + length
        records = self.boundaries.setdefault(end, [])
        records.append(boundary2)

        self.num_chunks += 1
        self.boundary_pairs.append((boundary1, boundary2))

        return id


    def Dump(self):
        """Dump the data to stdout."""
        boundary_ids = self.boundaries.keys()
        boundary_ids.sort()

        if self.print_as_hex:
            for boundary_id in boundary_ids:
                print "0x%x : %s" % (boundary_id, self.boundaries[boundary_id])
        else:
            for boundary_id in boundary_ids:
                print "%s : %s" % (boundary_id, self.boundaries[boundary_id])

    def BoundaryArrays(self):
        """Return an array of arrays of Boundary objects,
        in time-sorted order."""

        boundary_ids = self.boundaries.keys()
        boundary_ids.sort()

        return map(lambda x: self.boundaries[x], boundary_ids)

    def Chunks(self):
        """Return an array of Chunk objects, in time-sorted order.
        Each Chunk object represents the space between 2 boundaries
        in the linear space, and can contain 0 or more item IDs."""
        chunks = []

        boundary_ids = self.boundaries.keys()
        boundary_ids.sort()

        current_ids = []
        old_chunk = None
        for boundary_id in boundary_ids:
            if old_chunk:
                old_chunk.SetEnd(boundary_id)
                chunks.append(old_chunk)

            chunk = Chunk(boundary_id)

            boundaries = self.boundaries[boundary_id]

            for b in boundaries:
                if b.Type() == B_START:
                    current_ids.append(b.ID())
                elif b.Type() == B_END:
                    current_ids.remove(b.ID())
                else:
                    assert 0

            chunk.SetIDs(current_ids[:])
            old_chunk = chunk

        return chunks

    def ItemName(self, id):
        """Given the ID of an item, return the name."""
        return self.boundary_pairs[id][0].Name()

    def ItemComments(self, id):
        """Given the ID of an item, return the name. If the item
        has no comment, None is returned."""
        if self.comments.has_key(id):
            return self.comments[id]
        else:
            return None

    def PrintMap(self, fh):
        """Print the linear map."""

        if self.print_map_key:
            print "Map Key:"
            print "========"
            for (b1, b2) in self.boundary_pairs:
                name = b1.Name()
                id = b1.ID()
                if self.comments.has_key(id):
                    print "%2d. %s -- %s" % (id, name, self.comments[id])
                else:
                    print "%2d. %s" % (id, name)
            print

        boundary_ids = self.boundaries.keys()
        boundary_ids.sort()

        current_chunks = []
        chunk_str = None
        for boundary_id in boundary_ids:
            if self.print_diff:
                # Print chunk size for previous chunk
                if chunk_str != None:
                    if chunk_str:
                        spaces = max(20 - len(chunk_str), 1)
                    else:
                        spaces = 21
                    print " " * spaces,
                    diff = boundary_id - old_boundary_id
                    print "%d bytes (0x%x)" % (diff, diff)
            else:
                print

            boundaries = self.boundaries[boundary_id]
            if self.print_as_hex:
                print "-------- 0x%08x : %s" % (boundary_id, boundaries)
            else:
                print "-------- %s : %s" % (boundary_id, boundaries)

            for b in boundaries:
                if b.Type() == B_START:
                    current_chunks.append(b.ID())
                elif b.Type() == B_END:
                    current_chunks.remove(b.ID())
                else:
                    assert 0

            if current_chunks:
                chunk_str = ', '.join(map(str, current_chunks))
                print chunk_str,
            else:
                chunk_str = ""
            old_boundary_id = boundary_id
