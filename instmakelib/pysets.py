# Copyright (c) 2010 by Cisco Systems, Inc.
from types import *

class SetClass:
    """This class performs set operations on the data sets of two SetClass
    objects.

    Public Methods:
    items()
    display()
    union()
    intersection()
    excluding()
    isempty()
    pretty_print()
    
    """
    
    def __init__(self, arg=None, name=None):
        """ Initialize private variable members.

        Arguments:
        arg -- the set of data (default None)

        """        

        if isinstance(arg, ListType):
            self.members = self.dict_from_list(arg)
        elif isinstance(arg, DictType):
            self.members = arg
        elif isinstance(arg, SetClass):
            self.members = {}
            self.members.update(arg.members)
        else:
            self.members = {}

        self.my_name = name

    def __getitem__(self, idx):
        return self.members[idx]
    
    def name(self):
        """Return the name of this set."""
        return self.my_name

    def isempty(self):
        """ Return 1 if there are no members, 0 otherwise """
        return len(self.members.keys()) == 0

    def __len__(self):
        return len(self.members)

    def display(self):
        """ Print out the entire members list."""

        print self.members.values()
        return
    
    def pretty_print(self):
        """ Print out the entire members list with each item per line."""

        members = self.members.values()
        members.sort()
        for member in members:
            print member
        return

    def items(self):
        """ Returns a list of the items in this set."""
        # This method can't be called 'members' because we have
        # a variable called 'members'
        return self.members.values()

    def filter(self, func):
        """Returns a new set, filtered by a function. Like Python's
        filter() function, but operates on sets instead of lists."""

        return SetClass(filter(func, self.items()))

    def union(self, other):
        """Return the union set of this object's members with the members
        of another SetClass.

        """
        res = {}
        other_dict = self.get_dict(other)
        res.update(self.members)
        res.update(other_dict)
        return SetClass(res)

    def intersection(self, other):
        """Return the intersection set of this object's members with the
        members of another SetClass. Returns a list.

        """
        res = {}
        other_dict = self.get_dict(other)

        for x in self.members.keys():
            if other_dict.has_key(x):
                res[x] = self.members[x]

        return SetClass(res)

    def excluding(self, other):
        """Return the exclusion set of this object's members with the
        members of another SetClass. Returns a list.

        """
        res = {}
        res.update(self.members)
        other_dict = self.get_dict(other)
            
        for x in other_dict.keys():
            if res.has_key(x):
                del res[x]

        return SetClass(res)

    def get_dict(self, object):
        """Given an object, either a SetClass, a dictionary, or a list,
        get a dictionary from it. Raises TypeError if the object is
        none of the 3 types listed above."""

        if isinstance(object, SetClass):
            dict = object.members
        elif isinstance(object, ListType):
            dict = self.dict_from_list(object)
        elif isinstance(object, DictType):
            dict = object
        else:
            raise TypeError("Requires a SetClass, dictionary, or list.")

        return dict

    def dict_from_list(self, list):
        """Returns a dictionary. Every item in 'list' is a key of
        the dictionary. The value of each key is None."""
        dict = {}
        for item in list:
            # If we can use the item directly in a hash, do so.
            # If not, use the repr(). We could use the repr() all
            # the time, but this would be wasteful ... if there's no
            # reason to allocate a string, don't do so.
            try:
                dict[item] = item
            except TypeError:
                # Who knows? It's possible the repr() of some
                # class returns another non-hashable type. Unlikely.
                try:
                    dict[repr(item)] = item
                except TypeError:
                    print "TypeError in pysets.py, dict_from_list()"
                    print "item=%s" % (item,)
        return dict

    def get_item_key(self, item):
        """Returns the key used to store this item, or None if
        the item is not hash-able or is not in the set. """
        try:
            # Maybe the item can be used directly in a hash.
            test = self.members[item]
            return item
        except TypeError:
            # Or maybe the repr() of the item can be used in a hash.
            try:
                repr_item = repr(item)
                test = self.members[repr_item]
                return repr_item
            except TypeError:
                return None

        except KeyError:
            return None

    def remove_item(self, item):
        """Removes an item from the set. Returns 1 on success,
        or 0 if the item is not in the set."""
        item_key = self.get_item_key(item)
        if item_key == None:
            return 0
        else:
            del self.members[item_key]
            return 1

    def add_item(self, item):
        """Add an item to the set. No-op if item is already in set.
        No return value."""
        # If we can use the item directly in a hash, do so.
        # If not, use the repr(). We could use the repr() all
        # the time, but this would be wasteful ... if there's no
        # reason to allocate a string, don't do so.
        try:
            self.members[item] = item
        except TypeError:
            # Who knows? It's possible the repr() of some
            # class returns another non-hashable type. Unlikely.
            try:
                self.members[repr(item)] = item
            except TypeError:
                print "TypeError in pysets.py, add()"
                print "item=%s" % (item,)

    def add_items(self, items):
        """Add multiple items to the set.  No return value."""
        for item in items:
            self.add_item(item)

    def contains_item(self, item):
        """Does the set contain the item? Returns 1 on true, 0 on false."""
        item_key = self.get_item_key(item)
        if item_key:
            return 1
        else:
            return 0



    def __repr__(self):
        return repr(self.members.values())


# Given 2 python lists, returns a tuple:
# (list of common items, items in list1 but not list2, items in list2 but not list1)
def CompareLists(list1, list2):
    set1 = SetClass(list1)
    set2 = SetClass(list2)

    excl1 = set1.excluding(set2)
    excl2 = set2.excluding(set1)

    common_set = set1.intersection(set2)

    return (common_set.items(), excl1.items(), excl2.items())
