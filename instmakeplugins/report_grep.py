# Copyright (c) 2010 by Cisco Systems, Inc.
"""
Show individual records, letting the user 'grep' for text.
"""
from instmakelib import instmake_log as LOG
import getopt
import sys
import re
import os
import cPickle as pickle


INSTMAKE_VERSION = "INSTMAKE LOG VERSION 10"
def write_rec(rec, n, fd):
    empty_catcr = None

    data = (rec.ppid, rec.pid, rec.cwd, rec.retval,
        rec.times_start, rec.times_end,
        rec.cmdline_args, rec.make_target, rec.makefile_filename,
        rec.makefile_lineno, empty_catcr,
        rec.env_vars, rec.open_fds, rec.make_vars)

    data_text = pickle.dumps(data, 1) # 1 = dump as binary

    try:
        os.write(fd, data_text)
    except OSError, err:
        sys.exit(err)



def print_rec(rec, n, junk):
    print n
    rec.Print()

def print_bit_bucket(rec, n, junk):
    return

# This functions return a single field from an
# instmake record.
def return_cmdline(rec):
    return rec.cmdline

def return_tool(rec):
    return rec.tool

def return_target(rec):
    return rec.make_target

def return_cwd(rec):
    return rec.cwd

def return_retval(rec):
    return str(rec.retval)

def return_input(rec):
    return rec.input_files

def return_execed(rec):
    return rec.execed_files

def return_output(rec):
    return rec.output_files

def return_pid(rec):
    return rec.pid

def return_audit_ok(rec):
    return rec.audit_ok

# Used to search through a scalar field
def scalar_field_search(log, re_user, printer, printer_arg, helper_func, opposite):
    found = 0
    # Read through the records
    while 1:
        try:
            rec = log.read_record()
        except EOFError:
            log.close()
            break

        field = helper_func(rec)
        if field != None:
            m = re_user.search(field)
            if opposite:
                if not m:
                    found += 1
                    printer(rec, found, printer_arg)
            else:
                if m:
                    found += 1
                    printer(rec, found, printer_arg)

    return found

# Used to search through an array field.
def array_field_search(log, re_user, printer, printer_arg, helper_func, opposite):
    found = 0
    # Read through the records
    while 1:
        try:
            rec = log.read_record()
        except EOFError:
            log.close()
            break

        fields = helper_func(rec)
        if fields:
            for field in fields:
                m = re_user.search(field)
                if opposite:
                    if not m:
                        found += 1
                        printer(rec, found, printer_arg)
                        break
                else:
                    if m:
                        found += 1
                        printer(rec, found, printer_arg)
                        break

    return found

# Used to search for a boolean value
def boolean_field_search(log, needle, printer, printer_arg, helper_func, opposite):
    if needle == '0' or needle[0] == "f" or needle[0] == "F":
        needle = False
    else:
        needle = True

    found = 0
    # Read through the records
    while 1:
        try:
            rec = log.read_record()
        except EOFError:
            log.close()
            break

        field = helper_func(rec)
        if field != None:
            if field == needle:
                if not opposite:
                    found += 1
                    printer(rec, found, printer_arg)
            else:
                if opposite:
                    found += 1
                    printer(rec, found, printer_arg)

    return found

SEARCH_SCALAR = 0
SEARCH_ARRAY = 1
SEARCH_BOOLEAN = 2

description = "Find records whose fields match a regex."

def usage():
    print "grep:", description
    print "\t[-o new_instmake_log] [-v] [FIELD] regex"
    print
    print "\t-c : Show count, but not records."
    print "\t-o : Write records to new instmake log."
    print "\t-v : Return records that DON'T match."
    print
    print "\tFIELD: --cmdline (default), --tool, --target, --cwd,"
    print "\t\t--retval, --auditok, --inputs, --outputs, --execed, --pid"

def report(log_file_names, args):

    # We only accept one log file
    if len(log_file_names) != 1:
        sys.exit("'grep' report uses one log file.")
    else:
        log_file_name = log_file_names[0]

    # Defaults
    search_helper = return_cmdline
    search_type = SEARCH_SCALAR
    new_log_name = None
    new_log_fd = None
    opposite = 0
    show_count_only = 0

    # Our options
    optstring = "co:v"
    longopts = ["tool", "target", "cwd", "retval", "inputs", "outputs",
        "cmdline", "pid", "auditok", "execed"]


    try:
        opts, args = getopt.getopt(args, optstring, longopts)
    except getopt.GetoptError:
        usage()
        sys.exit(1)

    for opt, arg in opts:
        if opt == "--tool":
            search_helper = return_tool
            search_type = SEARCH_SCALAR
        elif opt == "--cmdline":
            search_helper = return_cmdline
            search_type = SEARCH_SCALAR
        elif opt == "--target":
            search_helper = return_target
            search_type = SEARCH_SCALAR
        elif opt == "--cwd":
            search_helper = return_cwd
            search_type = SEARCH_SCALAR
        elif opt == "--retval":
            search_helper = return_retval
            search_type = SEARCH_SCALAR
        elif opt == "--outputs":
            search_helper = return_output
            search_type = SEARCH_ARRAY
        elif opt == "--inputs":
            search_helper = return_input
            search_type = SEARCH_ARRAY
        elif opt == "--execed":
            search_helper = return_execed
            search_type = SEARCH_ARRAY
        elif opt == "--pid":
            search_helper = return_pid
            search_type = SEARCH_SCALAR
        elif opt == "--auditok":
            search_helper = return_audit_ok
            search_type = SEARCH_BOOLEAN
        elif opt == "-c":
            show_count_only = 1
        elif opt == "-o":
            new_log_name = arg
        elif opt == "-v":
            opposite = 1           
        else:
            assert 0, "%s option not handled." % (opt,)

    # One regex pattern
    if len(args) != 1:
        usage()
        sys.exit(0)

    # If the user wants it, create a new instmake log
    if new_log_name:
        file_mode = 0664
        try:
            new_log_fd = os.open(new_log_name, os.O_CREAT|os.O_TRUNC|os.O_WRONLY,
                file_mode)
        except OSError, err:
            sys.exit("Failed to open %s: %s" % (new_log_name, err))

        header_text = pickle.dumps(INSTMAKE_VERSION, 0) # 0 = dump as ASCII
        try:
            os.write(new_log_fd, header_text)
        except OSError, err:
            sys.exit("Failed to write to %s: %s" % (new_log_name, err))

        printer = write_rec
    else:
        printer = print_rec

    if show_count_only:
        printer = print_bit_bucket

    try:
        re_user = re.compile(args[0])
    except re.error, err:
        sys.exit("Regular expression: %s\n%s" % (args[0], err))

    # Open the log file
    log = LOG.LogFile(log_file_name)

    if search_type == SEARCH_SCALAR:
        num_found = scalar_field_search(log, re_user, printer, new_log_fd,
            search_helper, opposite)
    elif search_type == SEARCH_ARRAY:
        num_found = array_field_search(log, re_user, printer, new_log_fd,
            search_helper, opposite)
    elif search_type == SEARCH_BOOLEAN:
        num_found = boolean_field_search(log, args[0], printer, new_log_fd,
            search_helper, opposite)
    else:
        assert 0

    if new_log_fd:
        try:
            os.close(new_log_fd)
        except OSError:
            pass

        print num_found, "found."

    if show_count_only:
        print num_found, "found."
