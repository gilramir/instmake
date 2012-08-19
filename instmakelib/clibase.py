# Copyright (c) 2010 by Cisco Systems, Inc.
"""
CLI Plugin Base Class
"""

import re
from instmakelib import pysets
from instmakelib import instmake_log as LOG

class NotHandledException(Exception):
    pass

class BadCLIException(Exception):
    pass

class CLIPluginBase:
    shell_terminators = [ "|", ";", "||", "&&", ">", ">>", ">&" ]

    def __init__(self):
        self.outputs_printed = {}
        self.outputs = []

    def Outputs(self):
        return self.outputs

    def EnsureFilenamePrinted(self, dir, my_file, other_file):
        if not self.outputs_printed.has_key(my_file):
            print
            print "DIR:  ", dir
#            print "[", os.path.basename(my_file), "]"
            print "FILE1:", my_file
            print "FILE2:", other_file

            num_dashes = max(len(my_file), len(other_file))
            print "-" * (7 + num_dashes) # 6 = len("FILE1: ")

            self.outputs_printed[my_file] = None

    def CompareValue(self, dir, my_file, other_file, my_value, other_value, label,
            collator):
        """Returns 1 if no problems were found, 0 if problems were found."""
        if my_value != other_value:
            self.EnsureFilenamePrinted(dir, my_file, other_file)
            print "\tDifferent %s:" % (label,)
            print "\t%s : %s" % (my_file, my_value)
            print "\t%s : %s" % (other_file, other_value)
            collator.Add(label + "(%s != %s)" % (my_value, other_value),
                    dir, my_file, other_file)
            return 0
        else:
            return 1


    def CompareUnorderedList(self, dir, my_file, other_file, my_list, other_list, label,
            collator):
        """Returns 1 if no problems were found, 0 if problems were found."""
        (common, excl1, excl2) = pysets.CompareLists(my_list, other_list)
        ok = 1
        if excl1:
            self.EnsureFilenamePrinted(dir, my_file, other_file)
            print "\t%s present in %s but not in %s:" % (label, my_file, other_file)
            LOG.print_enumerated_list(excl1)
            collator.AddOneOfEach(label + " added", excl1, dir, my_file, other_file)
            ok = 0

        if excl2:
            self.EnsureFilenamePrinted(dir, my_file, other_file)
            print "\t%s present in %s but not in %s:" % (label, other_file, my_file)
            LOG.print_enumerated_list(excl2)
            collator.AddOneOfEach(label + " missing", excl2, dir, my_file, other_file)
            ok = 0

        return ok

    def CompareOrderedList(self, dir, my_file, other_file, my_list, other_list, label, collator):
        """Returns 1 if no problems were found, 0 if problems were found."""
        # First check for the same content
        ok = self.CompareUnorderedList(dir, my_file, other_file, my_list, other_list, label, collator)

        if ok:
            # Then check for the same order.
            i = 0
            for pair in zip(my_list, other_list):
                if pair[0] != pair[1]:
                    self.EnsureFilenamePrinted(dir, my_file, other_file)
                    print "\t%s has mismatch at index %d:" % (label, i)
                    print "\t%s != %s" % (pair[0], pair[1])
                    collator.Add(label + ": at index %d, %s != %s" % (i, pair[0],
                        pair[1]), dir, my_file, other_file)
                    ok = 0
                i += 1
        return ok


    def CompareHashOfValues(self, dir, my_file, other_file, my_hash, other_hash, label,
            collator):
        """Returns 1 if no problems were found, 0 if problems were found."""
        ok = 1

        # Short-cut
        if not my_hash and not other_hash:
            return ok

        (common, excl1, excl2) = pysets.CompareLists(my_hash.keys(), other_hash.keys())

        if excl1:
            self.EnsureFilenamePrinted(dir, my_file, other_file)
            print "\t%s values present in %s but not in %s:" % (label, my_file, other_file)
            LOG.print_enumerated_list(excl1)
            collator.AddOneOfEach(label + " missing", excl1, dir, my_file, other_file)
            ok = 0

        if excl2:
            self.EnsureFilenamePrinted(dir, my_file, other_file)
            print "\t%s values present in %s but not in %s:" % (label, other_file, my_file)
            LOG.print_enumerated_list(excl2)
            collator.AddOneOfEach(label + " added", excl2, dir, my_file, other_file)
            ok = 0

        for key in common:
            my_value = my_hash[key]
            other_value = other_hash[key]
            new_label = "%s (%s)" % (label, key)
            ok *= self.CompareValue(dir, my_file, other_file, my_value, other_value, new_label, collator)

        return ok


# For IBR4 dso name comparison
re_dso_num_trim = re.compile(r"-(?P<zeroes>0+)(?P<num>\d*)-dso-")

def dso_trim(x):
    m = re_dso_num_trim.search(x)
    if m:
        # 000 case
        if m.group("num") == "":
            num = "0"
        else:
            num = m.group("num")
        new_text = "-" + num + "-dso-"
        return re_dso_num_trim.sub(new_text, x)
    else:
        return x
